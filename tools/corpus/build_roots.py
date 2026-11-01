"""Build pinned Ubuntu runtime roots and independent real-program loader evidence.

All extraction and chroots are project-owned. No package installation, maintainer
script execution, host linker-cache update or binfmt registration takes place.
"""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.request
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from capture_snapshot import capture

ROOT = Path(__file__).resolve().parents[2]
LOCK = ROOT / "tools/corpus/ubuntu.lock.json"
GENERATED = ROOT / "fixtures/generated/corpus"
APPS = ["hello", "jq", "zstd"]


def download(package):
    path = ROOT / ".tools/corpus/debs" / (package["sha256"] + ".deb")
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        for attempt in range(3):
            try:
                with urllib.request.urlopen(package["url"], timeout=60) as response:
                    data = response.read(package["size"] + 1)
                if len(data) != package["size"] or hashlib.sha256(data).hexdigest() != package["sha256"]:
                    raise ValueError("download integrity mismatch: " + package["name"])
                path.write_bytes(data)
                break
            except (OSError, TimeoutError):
                if attempt == 2:
                    raise
    if hashlib.sha256(path.read_bytes()).hexdigest() != package["sha256"]:
        raise ValueError("cached package integrity mismatch")
    return path


def target_file(root, absolute):
    # Resolve links in the target namespace, including absolute targets.
    pending = absolute.split("/")
    parts, hops = [], 0
    while pending:
        part = pending.pop(0)
        if part in ["", "."]:
            continue
        if part == "..":
            if parts:
                parts.pop()
            continue
        path = root.joinpath(*parts, part)
        if path.is_symlink():
            hops += 1
            if hops > 40:
                raise ValueError("target link loop")
            link = os.readlink(path)
            if link.startswith("/"):
                parts = []
            pending = link.split("/") + pending
        else:
            parts.append(part)
    return root.joinpath(*parts)


def loader_command(root, arch, interpreter, paths):
    command = ([] if os.geteuid() == 0 else ["sudo"]) + ["chroot", str(root)]
    if arch == "arm64":
        command += ["/qemu"]
    return command + [interpreter, "--inhibit-cache", "--glibc-hwcaps-mask", "", "--library-path", ":".join(paths)]


def stage_runtime(source, root, multiarch):
    # Rebuild only our generated root. Resolve and check before recursive removal.
    if root.is_symlink() or root.resolve() == GENERATED.resolve() or not root.resolve().is_relative_to(GENERATED.resolve()):
        raise ValueError("refusing cleanup outside generated corpus")
    if root.exists():
        shutil.rmtree(root)
    def omit(directory, names):
        relative = Path(directory).relative_to(source).as_posix()
        if relative == ".":
            allowed = {"lib", "lib64", "usr"}
        elif relative == "usr":
            allowed = {"lib", "lib64", "bin"}
        elif relative == "usr/bin":
            allowed = set(APPS)
        else:
            allowed = {name for name in names if name == multiarch or not (Path(directory) / name).is_dir() or (Path(directory) / name).is_symlink()}
        return set(names) - allowed
    shutil.copytree(source, root, symlinks=True, ignore=omit)


def build():
    lock = json.loads(LOCK.read_text())
    packages = {p["sha256"]: p for c in lock["contexts"] for p in c["packages"]}
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(download, packages.values()))
    for context in lock["contexts"]:
        root = ROOT / ".tools/corpus/roots" / context["suite"] / context["architecture"]
        owned = (ROOT / ".tools/corpus/roots").resolve()
        if root.is_symlink() or root.resolve() == owned or not root.resolve().is_relative_to(owned):
            raise ValueError("refusing extraction cleanup outside owned roots")
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True, exist_ok=True)
        for package in context["packages"]:
            subprocess.run(["dpkg-deb", "-x", str(download(package)), str(root)], check=True)
        # Noble packages use the merged-/usr layout. Jammy can keep real dirs.
        for name in ["lib", "lib64", "bin", "sbin"]:
            if not os.path.lexists(root / name) and (root / "usr" / name).is_dir():
                (root / name).symlink_to("usr/" + name)
        print(context["suite"], context["architecture"], "verified packages extracted", flush=True)
    outcomes = []
    for arch, machine, multiarch in [("amd64", 62, "x86_64-linux-gnu"), ("arm64", 183, "aarch64-linux-gnu")]:
        interpreter = "/lib64/ld-linux-x86-64.so.2" if arch == "amd64" else "/lib/ld-linux-aarch64.so.1"
        paths = ["/lib/" + multiarch, "/usr/lib/" + multiarch, "/lib", "/usr/lib"]
        for source, target in [("jammy", "jammy"), ("noble", "noble"), ("jammy", "noble"), ("noble", "jammy")]:
            label = source + "-on-" + target
            folder = GENERATED / arch / label
            root = folder / "root"
            # Preserve package symlinks; never resolve them through the host.
            stage_runtime(ROOT / ".tools/corpus/roots" / target / arch, root, multiarch)
            for app in APPS:
                origin = ROOT / ".tools/corpus/roots" / source / arch
                shutil.copy2(target_file(origin, "/usr/bin/" + app), root / "usr/bin" / app)
            loader = target_file(root, interpreter)
            profile = dict(rule_revision="glibc-2.35-controlled-v2" if target == "jammy" else "ubuntu-noble-2.39-0ubuntu8-v1",
                loader_family="glibc", machine=machine, loader_path_hex=interpreter.encode().hex(),
                loader_sha256=hashlib.sha256(loader.read_bytes()).hexdigest(), cwd_hex=b"/".hex(),
                default_dirs_hex=[p.encode().hex() for p in paths], library_path_hex=[p.encode().hex() for p in paths],
                cache_mode="disabled", hwcaps_policy="none", secure_execution=False, preload=[], audit=[])
            helper = root / "qemu"
            if helper.is_file():
                helper.unlink()
            capture(root, profile, folder / "snapshot")
            if arch == "arm64":
                shutil.copy2(ROOT / ".tools/reference/qemu/usr/bin/qemu-aarch64-static", helper)
            command = loader_command(root, arch, interpreter, paths)
            environment = {"PATH": os.environ["PATH"], "LC_ALL": "C", "LD_BIND_NOW": "1"}
            try:
                for app in APPS:
                    args = {"hello": ["--greeting=MoonLoadCheck"], "jq": ["-n", "[1,2,3] | add"], "zstd": ["-q", "-c"]}[app]
                    payload = b"MoonLoadCheck corpus roundtrip\n" * 16
                    result = subprocess.run(command + ["/usr/bin/" + app] + args, input=payload,
                        capture_output=True, env=environment, timeout=30)
                    listing = subprocess.run(command + ["--list", "/usr/bin/" + app], capture_output=True, env=environment, timeout=30)
                    stderr = result.stderr.decode("utf-8", errors="replace")
                    if result.returncode == 0:
                        if app == "hello" and result.stdout != b"MoonLoadCheck\n":
                            raise AssertionError("hello output differs")
                        if app == "jq" and result.stdout != b"6\n":
                            raise AssertionError("jq output differs")
                        if app == "zstd":
                            decoded = subprocess.run(command + ["/usr/bin/zstd", "-q", "-d", "-c"], input=result.stdout,
                                capture_output=True, env=environment, timeout=30)
                            if decoded.returncode != 0 or decoded.stdout != payload:
                                raise AssertionError("zstd roundtrip failed")
                    elif "not found" not in stderr and "undefined symbol" not in stderr:
                        raise AssertionError((arch, label, app, result.returncode, stderr))
                    if source == target and result.returncode != 0:
                        raise AssertionError("native distribution application failed")
                    record = dict(architecture=arch, case=label, app=app, exit_code=result.returncode,
                        stderr=stderr, listing=listing.stdout.decode("utf-8", errors="replace"),
                        program_sha256=hashlib.sha256((root / "usr/bin" / app).read_bytes()).hexdigest(),
                        loader_sha256=profile["loader_sha256"], snapshot_sha256=hashlib.sha256((folder / "snapshot/manifest.json").read_bytes()).hexdigest(),
                        command=[p.replace(str(ROOT), "$PROJECT") for p in command] + ["/usr/bin/" + app] + args,
                        environment=environment | {"PATH": "$HOST_PATH"})
                    outcomes.append(record)
                    print(arch, label, app, "exit", result.returncode, flush=True)
            finally:
                if helper.is_file():
                    helper.unlink()
    (GENERATED / "oracle.json").write_text(json.dumps(dict(lock_sha256=hashlib.sha256(LOCK.read_bytes()).hexdigest(), cases=outcomes), indent=2) + "\n")
    print(f"Corpus: {len(outcomes)} real-program deployment outcomes recorded")


if __name__ == "__main__":
    build()
