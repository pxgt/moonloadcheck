"""Reproduce an external zstd source build against three locked runtime identities.

Only this original recipe and metadata are distributed. Downloaded source,
licenses, binaries and roots remain in ignored directories. No host package install.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from check_deployment import write_json, run
from check_matrix import matrix
from corpus.build_roots import target_file, loader_command

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "tools/external.lock.json"
INTERP = "/lib64/ld-linux-x86-64.so.2"


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fetch(name, suffix):
    lock = json.loads(LOCK.read_text())[name]
    cache = ROOT / ".tools/expansion" / (name + suffix)
    cache.parent.mkdir(exist_ok=True, parents=True)
    if not cache.exists():
        for attempt in range(3):
            try:
                with urllib.request.urlopen(lock["url"], timeout=45) as response:
                    data = response.read(lock["size"] + 1)
                assert len(data) == lock["size"] and hashlib.sha256(data).hexdigest() == lock["sha256"]
                cache.write_bytes(data)
                break
            except OSError:
                if attempt == 2: raise
    assert cache.stat().st_size == lock["size"] and digest(cache) == lock["sha256"]
    return cache


def prepare_runtime():
    archive = fetch("libc6", ".deb")
    root = ROOT / ".tools/expansion/libc6-root"
    root.mkdir(exist_ok=True)
    # Re-extract the pinned package, retaining all its shipped documentation.
    subprocess.run(["dpkg-deb", "-x", str(archive), str(root)], check=True)
    return root


def verify(native, js):
    if not __debug__: raise RuntimeError("do not disable assertions")
    runtime = prepare_runtime()
    archive = fetch("zstd", ".tar.gz")
    base = ROOT / "fixtures/generated/external"
    base.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="zstd-", dir=base))
    with tarfile.open(archive) as tar:
        members = tar.getmembers()
        assert len(members) < 5000 and sum(m.size for m in members) < 100 * 1024 * 1024
        for member in members:
            assert not Path(member.name).is_absolute() and ".." not in Path(member.name).parts
            assert member.isfile() or member.isdir() or (
                member.issym() and member.name in ["zstd-1.5.7/tests/cli-tests/bin/unzstd", "zstd-1.5.7/tests/cli-tests/bin/zstdcat"]
                and member.linkname == "zstd"), member.name
        tar.extractall(work)
    source = work / "zstd-1.5.7"
    assert (source / "LICENSE").is_file() and (source / "COPYING").is_file()
    log = work / "build.log"
    with log.open("w") as stream:
        subprocess.run(["make", "-C", str(source / "lib"), "-j2", "libzstd"], stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=600)
        subprocess.run(["make", "-C", str(source / "programs"), "-j2", "zstd-dll", "HAVE_ZLIB=0", "HAVE_LZMA=0", "HAVE_LZ4=0"], stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=600)
        with tarfile.open(fetch("zstd_legacy", ".tar.gz")) as tar:
            for member in tar.getmembers():
                assert not Path(member.name).is_absolute() and ".." not in Path(member.name).parts
                assert member.isfile() or member.isdir(), member.name
            tar.extractall(work)
        subprocess.run(["make", "-C", str(work / "zstd-1.4.8/lib"), "-j2", "libzstd"], stdout=stream, stderr=subprocess.STDOUT, check=True, timeout=600)
    program = source / "programs/zstd"
    library = (source / "lib/libzstd.so.1").resolve(strict=True)
    assert library.is_relative_to(source)
    cases, targets = [], []
    for suite, runtime_root, revision in [
        ("jammy", ROOT / ".tools/corpus/roots/jammy/amd64", "glibc-2.35-controlled-v2"),
        ("noble", ROOT / ".tools/corpus/roots/noble/amd64", "ubuntu-noble-2.39-0ubuntu8-v1"),
        ("jammy-updated", runtime, "glibc-2.35-controlled-v2")]:
        for case in ["good", "missing", "old", "fixed"]:
            directory = work / suite / case
            stage = directory / "root"
            (stage / "lib64").mkdir(parents=True)
            (stage / "runtime").mkdir()
            (stage / "app").mkdir()
            shutil.copyfile(program, stage / "app/zstd")
            shutil.copyfile(target_file(runtime_root, INTERP), stage / INTERP.lstrip("/"))
            for name in ["libc.so.6", "libm.so.6", "libpthread.so.0"]:
                shutil.copyfile(target_file(runtime_root, "/lib/x86_64-linux-gnu/" + name), stage / "runtime" / name)
            if case != "missing":
                lib = (work / "zstd-1.4.8/lib/libzstd.so.1").resolve(strict=True) if case == "old" else library
                shutil.copyfile(lib, stage / "runtime/libzstd.so.1")
            # copyfile intentionally does not preserve mode; execution is a separate oracle.
            (stage / "app/zstd").chmod(0o755)
            (stage / INTERP.lstrip("/")).chmod(0o755)
            profile = dict(rule_revision=revision, loader_family="glibc", machine=62,
                loader_path=INTERP, loader_sha256=digest(stage / INTERP.lstrip("/")), cwd="/",
                default_dirs=[], library_path=["/runtime"], cache_mode="disabled", hwcaps_policy="none",
                secure_execution=False, preload=[], audit=[])
            cfg = directory / "deployment.json"
            config = dict(schema_version=1, root=str(stage), entries=["/app/zstd"], scope="compatibility", profile=profile)
            if suite == "jammy-updated":
                config.pop("profile")
                config["target"] = dict(id="ubuntu-jammy-2.35-0ubuntu3.15-amd64",
                    **{k:v for k,v in profile.items() if k not in ["rule_revision", "loader_family", "machine", "loader_path", "loader_sha256"]})
            write_json(cfg, config)
            expected = 0 if case in ["good", "old", "fixed"] else 1
            for label, command in [("native", [str(native.resolve())]), ("js", ["node", str(js.resolve())])]:
                observed = run(cfg, directory / label, command)
                assert observed["exit_code"] == expected, (suite, case, label, observed)
            loader = loader_command(stage, "amd64", INTERP, ["/runtime"])
            command = loader + ["/app/zstd"]
            env = {"PATH": os.environ["PATH"], "LC_ALL": "C", "LD_BIND_NOW": "1"}
            listing = subprocess.run(loader + ["--list", "/app/zstd"], capture_output=True, env=env, timeout=30)
            assert (listing.returncode == 0) == (expected == 0), (suite, case, listing.stderr)
            probe = subprocess.run(command + ["--version"], capture_output=True, env=env, timeout=30)
            assert (probe.returncode == 0) == (case in ["good", "fixed"]), (suite, case, probe.stderr)
            if case == "old":
                assert b"incorrect library version" in probe.stderr and b"actual : 1.4.8" in probe.stderr
            if case in ["good", "fixed"]:
                data = b"MoonLoadCheck external deployment roundtrip\n" * 1000
                packed = subprocess.run(command + ["-q", "-c"], input=data, capture_output=True, env=env, timeout=30)
                restored = subprocess.run(command + ["-q", "-d", "-c"], input=packed.stdout, capture_output=True, env=env, timeout=30)
                assert packed.returncode == restored.returncode == 0 and restored.stdout == data
            cases.append(dict(target=suite, case=case, analyzer_exit=expected, loader_exit=listing.returncode,
                application_exit=probe.returncode, application_error=probe.stderr.decode(errors="replace"),
                loader_sha256=profile["loader_sha256"], program_sha256=digest(program),
                loader_error=listing.stderr.decode(errors="replace")))
            targets.append(dict(id=suite + "/" + case, config=str(cfg)))
    cfg = work / "matrix-config.json"
    write_json(cfg, dict(schema_version=1, targets=targets))
    result = matrix(cfg, work / "matrix", [str(native.resolve())])
    assert result["exit_code"] == 1 and result["check_count"] == 12 and result["different_program_groups"] == 0
    output = ROOT / "artifacts/external"; output.mkdir(parents=True, exist_ok=True)
    write_json(output / "result.json", dict(project="facebook/zstd", version="1.5.7", external_adopter=False,
        work=str(work), source_sha256=digest(archive), program_sha256=digest(program), cases=cases,
        business_roundtrips=6, analyzer_checks=24, matrix=result,
        compiler=subprocess.check_output(["gcc", "--version"], text=True).splitlines()[0]))
    print("External zstd: 24 analyzer checks, 12 loader lists, 12 application probes, 6 compression roundtrips, 12-cell matrix passed;", work)


if __name__ == "__main__":
    p=argparse.ArgumentParser(); p.add_argument("--native", type=Path, required=True); p.add_argument("--js", type=Path, required=True)
    a=p.parse_args(); verify(a.native, a.js)
