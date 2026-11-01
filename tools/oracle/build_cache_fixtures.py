"""Compare ordered cache selection inside a disposable project-owned chroot.

The small synthetic cache is independently consumed by ldconfig and glibc.
No host cache or global linker configuration is changed.
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from capture_snapshot import capture

ROOT = Path(__file__).resolve().parents[2]


def cache_bytes(paths, flags, hwcap=0):
    strings = bytearray()
    records = bytearray()
    start = 48 + 24 * len(paths)
    for path in paths:
        key = start + len(strings)
        strings += b"libchoice.so.1\0"
        value = start + len(strings)
        strings += path.encode() + b"\0"
        records += struct.pack("<IIIIQ", flags, key, value, 0, hwcap)
    header = bytearray(48)
    header[:20] = b"glibc-ld.so.cache1.1"
    struct.pack_into("<II", header, 20, len(paths), len(strings))
    header[28] = 2
    return bytes(header + records + strings)


def build():
    outcomes = []
    for arch, machine, flags in [("x86_64", 62, 0x303), ("aarch64", 183, 0xa03)]:
        cc = "gcc" if machine == 62 else "aarch64-linux-gnu-gcc"
        system = Path("/lib/x86_64-linux-gnu") if machine == 62 else Path("/usr/aarch64-linux-gnu/lib")
        interpreter = "/lib64/ld-linux-x86-64.so.2" if machine == 62 else "/lib/ld-linux-aarch64.so.1"
        loader = system / Path(interpreter).name
        cases = [("preferred", ["/preferred/libchoice.so.1"], False, False, 0, "/preferred/libchoice.so.1"),
                 ("disabled", ["/preferred/libchoice.so.1"], False, True, 1, "/lib/libchoice.so.1"),
                 ("stale-first", ["/gone/libchoice.so.1", "/preferred/libchoice.so.1"], False, False, 1, "/lib/libchoice.so.1"),
                 ("nodeflib-allowed", ["/preferred/libchoice.so.1"], True, False, 0, "/preferred/libchoice.so.1"),
                 ("nodeflib-filtered", ["/lib/libchoice.so.1", "/preferred/libchoice.so.1"], True, False, 127, None)]
        for case, paths, nodeflib, disabled, expected_exit, expected_path in cases:
            folder = ROOT / "fixtures/generated/cache" / arch / case
            root = folder / "root"
            if (root / "qemu").is_file():
                (root / "qemu").unlink()  # Only our previous chroot helper.
            for directory in ["etc", "preferred", "lib", "runtime", Path(interpreter).parent.as_posix().lstrip("/")]:
                (root / directory).mkdir(parents=True, exist_ok=True)
            for directory, value in [("preferred", 7), ("lib", 9)]:
                subprocess.run([cc, "-shared", "-fPIC", f"-DVALUE={value}", str(ROOT / "fixtures/src/choice.c"),
                    "-Wl,-soname,libchoice.so.1", "-o", str(root / directory / "libchoice.so.1")], check=True)
            subprocess.run([cc, str(ROOT / "fixtures/src/app.c"), "-L" + str(root / "preferred"), "-l:libchoice.so.1",
                *(["-Wl,-z,nodefaultlib"] if nodeflib else []), "-o", str(root / "app")], check=True)
            shutil.copy2(system / "libc.so.6", root / "runtime/libc.so.6")
            shutil.copy2(loader, root / interpreter.lstrip("/"))
            (root / "etc/ld.so.cache").write_bytes(cache_bytes(paths, flags))
            printed = subprocess.check_output(["/sbin/ldconfig", "-p", "-C", str(root / "etc/ld.so.cache")], text=True)
            if any(path not in printed for path in paths):
                raise AssertionError("ldconfig did not decode the generated records")
            profile = dict(rule_revision="glibc-2.35-controlled-v2", loader_family="glibc", machine=machine,
                loader_path_hex=interpreter.encode().hex(), loader_sha256=hashlib.sha256(loader.read_bytes()).hexdigest(),
                cwd_hex=b"/".hex(), default_dirs_hex=[p.encode().hex() for p in (
                    ["/lib/x86_64-linux-gnu", "/usr/lib/x86_64-linux-gnu", "/lib", "/usr/lib"] if machine == 62 else ["/lib/aarch64-linux-gnu", "/usr/lib/aarch64-linux-gnu", "/lib", "/usr/lib"])],
                library_path_hex=[b"/runtime".hex()], cache_mode="disabled" if disabled else "glibc-cache-v1",
                hwcaps_policy="none", secure_execution=False, preload=[], audit=[])
            capture(root, profile, folder / "snapshot")
            prefix = ([] if os.geteuid() == 0 else ["sudo"]) + ["chroot", str(root)]
            if machine == 183:
                shutil.copy2(ROOT / ".tools/reference/qemu/usr/bin/qemu-aarch64-static", root / "qemu")
                prefix += ["/qemu"]
            command = prefix + [interpreter, *(["--inhibit-cache"] if disabled else []),
                "--glibc-hwcaps-mask", "", "--library-path", "/runtime"]
            env = {key: value for key, value in os.environ.items() if not key.startswith("LD_")}
            result = subprocess.run(command + ["/app"], capture_output=True, text=True, env=env, timeout=20)
            listing = subprocess.run(command + ["--list", "/app"], capture_output=True, text=True, env=env, timeout=20)
            if result.returncode != expected_exit or (expected_path and "=> " + expected_path not in listing.stdout):
                raise AssertionError((arch, case, result.returncode, result.stderr, listing.stdout))
            outcomes.append(dict(architecture=arch, case=case, exit_code=result.returncode, selected=expected_path,
                stderr=result.stderr, listing=listing.stdout))
            if (root / "qemu").is_file():
                (root / "qemu").unlink()
    (ROOT / "fixtures/generated/cache/oracle.json").write_text(json.dumps(outcomes, indent=2) + "\n")
    print(f"Cache: {len(outcomes)} chroot loader outcomes matched")


if __name__ == "__main__":
    build()
