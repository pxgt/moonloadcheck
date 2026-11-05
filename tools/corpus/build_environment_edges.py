"""Independent pinned-loader evidence for token context, separators and cache facts."""
import hashlib
import itertools
import json
import os
import shutil
import struct
import subprocess
from build_roots import ROOT, target_file, loader_command, capture

GENERATED = ROOT / "fixtures/generated/environment-edges"
TOKEN_CASES = ["tokens-" + "".join(map(str, bits)) for bits in itertools.product(range(2), repeat=3)]
PATH_CASES = ["dso-origin", "ancestor-origin", "environment-origin", "empty-runpath", "colon-runpath",
              "rpath-semicolon", "runpath-semicolon", "rpath-semicolon-missing", "runpath-semicolon-missing"]
CACHE_CASES = ["cache-tls", "cache-os-old", "cache-os-future", "cache-foreign", "cache-plain-first"]


def cache_bytes(records):
    """Controlled glibc 1.1 records: (flags, OS version, hwcap, absolute path)."""
    offset = 48 + 24 * len(records)
    strings, encoded = bytearray(), bytearray()
    for flags, osversion, hwcap, path in records:
        key = offset + len(strings)
        strings += b"libapi.so.1\0"
        value = offset + len(strings)
        strings += path.encode() + b"\0"
        encoded += struct.pack("<IIIIQ", flags, key, value, osversion, hwcap)
    header = bytearray(48)
    header[:20] = b"glibc-ld.so.cache1.1"
    struct.pack_into("<II", header, 20, len(records), len(strings))
    header[28] = 2  # little endian
    return header + encoded + strings


def build():
    outcomes = []
    environment = {"PATH": os.environ["PATH"], "LC_ALL": "C"}
    for arch, machine, multiarch in [("amd64", 62, "x86_64-linux-gnu"), ("arm64", 183, "aarch64-linux-gnu")]:
        cc = "gcc" if machine == 62 else "aarch64-linux-gnu-gcc"
        interpreter = "/lib64/ld-linux-x86-64.so.2" if machine == 62 else "/lib/ld-linux-aarch64.so.1"
        for suite in ["jammy", "noble"]:
            source = ROOT / ".tools/corpus/roots" / suite / arch
            for case in TOKEN_CASES + PATH_CASES + (CACHE_CASES if suite == "jammy" else []):
                folder = GENERATED / arch / suite / case
                root = folder / "root"
                if root.is_symlink() or root.resolve() == GENERATED.resolve() or not root.resolve().is_relative_to(GENERATED.resolve()):
                    raise ValueError("refusing cleanup outside generated environment fixtures")
                if root.exists():
                    shutil.rmtree(root)
                for directory in ["runtime", "app/bin", "preferred", "fallback", "etc", interpreter.lstrip("/").rsplit("/", 1)[0]]:
                    (root / directory).mkdir(parents=True, exist_ok=True)
                shutil.copy2(target_file(source, interpreter), root / interpreter.lstrip("/"))
                shutil.copy2(target_file(source, "/lib/" + multiarch + "/libc.so.6"), root / "runtime/libc.so.6")
                helper = root / "qemu"
                if arch == "arm64":
                    shutil.copy2(ROOT / ".tools/reference/qemu/usr/bin/qemu-aarch64-static", helper)
                prefix = loader_command(root, arch, interpreter, ["/runtime"])
                diagnostics = subprocess.check_output(prefix + ["--list-diagnostics"], env=environment, text=True, timeout=30)
                facts = dict(line.split("=", 1) for line in diagnostics.splitlines() if line.startswith(("dl_dst_lib=", "dl_platform=")))
                lib, platform = json.loads(facts["dl_dst_lib"]), json.loads(facts["dl_platform"])
                for value in [lib, platform]:
                    if not value or any(part in ["", ".", ".."] for part in value.split("/")):
                        raise ValueError("unsupported diagnostic token")
                if helper.is_file():
                    helper.unlink()
                commands = []

                def run(command):
                    commands.append([str(p).replace(str(ROOT), "$PROJECT") for p in command])
                    subprocess.run(command, check=True)

                def library(path, function="api", value=7, soname=None, flags=()):
                    output = root / path.lstrip("/")
                    output.parent.mkdir(parents=True, exist_ok=True)
                    run([cc, "-shared", "-fPIC", str(ROOT / "fixtures/src/graph_library.c"),
                         "-DFUNCTION=" + function, "-DVALUE=" + str(value), "-Wl,-soname," + (soname or output.name),
                         *flags, "-o", str(output)])
                    return output

                paths, flags, selected, code, actual_code = ["/runtime"], [], {}, 0, 0
                if case in TOKEN_CASES:
                    tokens = ["${" + name + "}" if bit == "1" else "$" + name for name, bit in zip(["ORIGIN", "LIB", "PLATFORM"], case[-3:])]
                    path = "/app/bin/" + lib + "/" + platform + "/libapi.so.1"
                    link = library(path)
                    flags = ["-Wl,-rpath," + "/".join(tokens)]
                    selected["libapi.so.1"] = path
                elif case in ["dso-origin", "ancestor-origin", "environment-origin"]:
                    middle = "/other/libmiddle.so.1" if case == "environment-origin" else "/app/bin/providers/libmiddle.so.1"
                    leafdir = "/app/bin/providers/private" if case == "dso-origin" else "/app/bin/providers"
                    leaf = library(leafdir + "/libleaf.so.1", "leaf")
                    decoy = {"dso-origin": "/app/bin/private", "ancestor-origin": "/app/bin/providers/providers",
                             "environment-origin": "/other/providers"}[case]
                    library(decoy + "/libleaf.so.1", "leaf", 99)
                    middleflags = ["-DDEPENDENCY=leaf", str(leaf)]
                    if case == "dso-origin":
                        middleflags += ["-Wl,-rpath,${ORIGIN}/private"]
                    link = library(middle, value=0, soname=middle if case == "environment-origin" else None, flags=middleflags)
                    if case == "environment-origin":
                        paths = ["$ORIGIN/providers", "/runtime"]
                    else:
                        flags = ["-Wl,-rpath,$ORIGIN/providers"]
                        if case == "ancestor-origin":
                            flags += ["-Wl,--disable-new-dtags"]
                    flags += ["-Wl,-rpath-link," + str(leaf.parent)]
                    selected = {"libleaf.so.1": leafdir + "/libleaf.so.1"}
                elif case in ["empty-runpath", "colon-runpath"]:
                    link = library("/libapi.so.1")
                    flags = ["-Wl,-rpath," + (":" if case == "colon-runpath" else "")]
                    if case == "empty-runpath":
                        code, actual_code = 1, 127
                        selected["libapi.so.1"] = None
                    else:
                        selected["libapi.so.1"] = "/libapi.so.1"
                elif "semicolon" in case:
                    link = library("/good;/decoy/libapi.so.1")
                    library("/good/libapi.so.1", value=99)
                    flags = ["-Wl,-rpath,/good;/decoy"]
                    if case.startswith("rpath-"):
                        flags += ["-Wl,--disable-new-dtags"]
                    selected["libapi.so.1"] = "/good;/decoy/libapi.so.1"
                    if case.endswith("-missing"):
                        code, actual_code = 1, 127
                        selected["libapi.so.1"] = None
                else:
                    link = library("/preferred/libapi.so.1")
                    library("/fallback/libapi.so.1", value=9)
                    cacheflag = 0x303 if machine == 62 else 0xa03
                    conditional = (cacheflag, 0, 1 << 63, "/preferred/libapi.so.1")
                    if case in ["cache-os-old", "cache-os-future"]:
                        conditional = (cacheflag, 1 if case == "cache-os-old" else 0xffffffff, 0, "/preferred/libapi.so.1")
                    if case == "cache-foreign":
                        conditional = (0xa03 if machine == 62 else 0x303, 0, 1 << 63, "/preferred/libapi.so.1")
                    ordinary = (cacheflag, 0, 0, "/fallback/libapi.so.1")
                    records = [ordinary, conditional] if case == "cache-plain-first" else [conditional, ordinary]
                    (root / "etc/ld.so.cache").write_bytes(cache_bytes(records))
                    if case in ["cache-foreign", "cache-plain-first"]:
                        selected["libapi.so.1"], actual_code = "/fallback/libapi.so.1", 1
                    else:
                        selected["libapi.so.1"], code = None, 2
                        actual_code = 1 if case == "cache-os-future" else 0
                app = root / "app/bin/app"
                run([cc, str(ROOT / "fixtures/src/app.c"), "-Wl,-z,now", *flags, str(link), "-o", str(app)])
                if case.endswith("semicolon-missing"):
                    link.unlink()
                profile = dict(rule_revision="glibc-2.35-controlled-v2" if suite == "jammy" else "ubuntu-noble-2.39-0ubuntu8-v1",
                    loader_family="glibc", machine=machine, loader_path_hex=interpreter.encode().hex(),
                    loader_sha256=hashlib.sha256((root / interpreter.lstrip("/")).read_bytes()).hexdigest(), cwd_hex=b"/".hex(),
                    default_dirs_hex=[], library_path_hex=[p.encode().hex() for p in paths],
                    cache_mode="glibc-cache-v1" if case in CACHE_CASES else "disabled", hwcaps_policy="none",
                    secure_execution=False, preload=[], audit=[], lib_token_hex=lib.encode().hex(), platform_token_hex=platform.encode().hex())
                capture(root, profile, folder / "snapshot")
                if arch == "arm64":
                    shutil.copy2(ROOT / ".tools/reference/qemu/usr/bin/qemu-aarch64-static", helper)
                try:
                    command = loader_command(root, arch, interpreter, paths)
                    if case in CACHE_CASES:
                        command.remove("--inhibit-cache")
                    result = subprocess.run(command + ["/app/bin/app"], env=environment, capture_output=True, text=True, timeout=30)
                    assert result.returncode == actual_code, (arch, suite, case, result.returncode, result.stderr)
                    listing = subprocess.run(command + ["--list", "/app/bin/app"], env=environment, capture_output=True, text=True, timeout=30)
                    for path in selected.values():
                        if path is not None:
                            expected_line = "\tlibapi.so.1 (" if case == "colon-runpath" else "=> " + path + " ("
                            assert expected_line in listing.stdout, (case, path, listing.stdout)
                    if case in CACHE_CASES:
                        expected_path = "/fallback/libapi.so.1" if actual_code == 1 else "/preferred/libapi.so.1"
                        assert "=> " + expected_path + " (" in listing.stdout
                    (folder / "loader-list.txt").write_text(listing.stdout + listing.stderr)
                    outcomes.append(dict(architecture=arch, suite=suite, case=case, entry="/app/bin/app", expected_code=code,
                        selected=selected, exit_code=result.returncode, stderr=result.stderr, lib=lib, platform=platform,
                        command=[p.replace(str(ROOT), "$PROJECT") for p in command + ["/app/bin/app"]],
                        environment=environment | {"PATH": "$HOST_PATH"}, compile_commands=commands,
                        compiler=subprocess.check_output([cc, "-dumpfullversion"], text=True).strip(),
                        loader_sha256=profile["loader_sha256"], app_sha256=hashlib.sha256(app.read_bytes()).hexdigest()))
                    print(arch, suite, case, result.returncode, flush=True)
                finally:
                    if helper.is_file():
                        helper.unlink()
    (GENERATED / "oracle.json").write_text(json.dumps(outcomes, indent=2) + "\n")
    print(f"Environment edges: {len(outcomes)} actual loader outcomes and snapshots")


if __name__ == "__main__":
    build()
