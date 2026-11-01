"""Build our own ELF fixtures and record independent loader outcomes (Linux)."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "fixtures" / "src"

def run(args, **kwargs):
    return subprocess.run([str(x) for x in args], check=True, **kwargs)

def build(arch):
    cc = "gcc" if arch == "x86_64" else "aarch64-linux-gnu-gcc"
    strip = "strip" if arch == "x86_64" else "aarch64-linux-gnu-strip"
    out = ROOT / "fixtures" / "generated" / arch
    out.mkdir(parents=True, exist_ok=True)
    v1, v2 = out / "v1.map", out / "v2.map"
    v1.write_text("DEMO_1 { global: api; stable; local: *; };\n")
    v2.write_text("DEMO_2 { global: api; stable; local: *; };\n")
    for name, script, omit in [("old", v1, False), ("new-version", v2, False), ("removed", v1, True)]:
        folder = out / name
        folder.mkdir(exist_ok=True)
        run([cc, "-shared", "-fPIC", "-Wl,--hash-style=both", "-Wl,-soname,libdemo.so.1", "-Wl,--version-script=" + str(script), *(["-DOMIT_API"] if omit else []), SRC / "library.c", "-o", folder / "libdemo.so.1"])
    for name, folder, entry in [("app", "old", "api"), ("stable-app", "old", "stable"), ("version-app", "new-version", "api")]:
        run([cc, SRC / "app.c", "-DENTRY=" + entry, "-DEXPECTED=" + ("7" if entry == "api" else "9"), "-L" + str(out / folder), "-Wl,-rpath,$ORIGIN/" + folder, "-Wl,-z,now", "-l:libdemo.so.1", "-o", out / name])
    stripped = out / "app.stripped"
    shutil.copyfile(out / "app", stripped)
    run([strip, "--strip-all", stripped])
    sectionless = bytearray((out / "app").read_bytes())
    struct.pack_into("<Q", sectionless, 40, 0)
    struct.pack_into("<HHH", sectionless, 58, 0, 0, 0)
    (out / "app.sectionless").write_bytes(sectionless)
    (out / "app.sectionless").chmod(0o755)
    (out / "app.truncated").write_bytes(sectionless[:48])
    for kind in ["runpath", "rpath", "fixed"]:
        folder = out / kind
        lib = folder / "lib"
        lib.mkdir(parents=True, exist_ok=True)
        run([cc, "-shared", "-fPIC", SRC / "leaf.c", "-Wl,-soname,libleaf.so.1", "-o", lib / "libleaf.so.1"])
        run([cc, "-shared", "-fPIC", SRC / "middle.c", "-L" + str(lib), "-l:libleaf.so.1", "-Wl,-soname,libmiddle.so.1", *(["-Wl,-rpath,$ORIGIN"] if kind == "fixed" else []), "-o", lib / "libmiddle.so.1"])
        run([cc, SRC / "app.c", "-L" + str(lib), "-l:libmiddle.so.1", "-Wl,-rpath-link," + str(lib), "-Wl,-rpath,$ORIGIN/lib", *(["-Wl,--disable-new-dtags"] if kind == "rpath" else []), "-o", folder / "app"])
    loader = Path("/lib64/ld-linux-x86-64.so.2") if arch == "x86_64" else Path("/usr/aarch64-linux-gnu/lib/ld-linux-aarch64.so.1")
    qemu = ROOT / ".tools/reference/qemu/usr/bin/qemu-aarch64-static"
    if arch == "aarch64" and not qemu.exists():
        raise RuntimeError("AArch64 runtime unavailable; run bootstrap_reference.py first")
    prefix = [] if arch == "x86_64" else [str(qemu)]
    system_dirs = "/lib/x86_64-linux-gnu:/usr/lib/x86_64-linux-gnu" if arch == "x86_64" else "/usr/aarch64-linux-gnu/lib"
    env = {k: v for k, v in os.environ.items() if not k.startswith("LD_")}
    cases = [
        ("baseline", out / "app", out / "old", True),
        ("stripped", stripped, out / "old", True),
        ("sectionless", out / "app.sectionless", out / "old", True),
        ("version-missing", out / "version-app", out / "old", False),
        ("used-export-removed", out / "app", out / "removed", False),
        ("unused-export-removed", out / "stable-app", out / "removed", True),
        ("runpath-not-transitive", out / "runpath/app", None, False),
        ("rpath-transitive", out / "rpath/app", None, True),
        ("runpath-fixed", out / "fixed/app", None, True),
    ]
    records = []
    for name, program, override, expected in cases:
        path = ((str(override) + ":") if override else "") + system_dirs
        command = prefix + [str(loader), "--inhibit-cache", "--library-path", path, str(program)]
        result = subprocess.run(command, env=env, capture_output=True, text=True, timeout=15)
        record = {"case": name, "expected_success": expected, "exit_code": result.returncode, "stderr": result.stderr.replace(str(ROOT), "$PROJECT"), "command": [x.replace(str(ROOT), "$PROJECT") for x in command]}
        records.append(record)
        if (result.returncode == 0) != expected:
            raise AssertionError(record)
    metadata = {
        "architecture": arch,
        "compiler": subprocess.check_output([cc, "--version"], text=True).splitlines()[0],
        "loader_sha256": hashlib.sha256(loader.read_bytes()).hexdigest(),
        "qemu": subprocess.check_output([str(qemu), "--version"], text=True).splitlines()[0] if prefix else None,
        "cases": records,
        "files": {str(p.relative_to(out)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.rglob("*")) if p.is_file() and p.name != "oracle.json"},
    }
    (out / "oracle.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(arch + ": " + str(len(records)) + " loader outcomes matched", flush=True)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--arch", choices=["x86_64", "aarch64", "all"], default="all")
    args = parser.parse_args()
    for architecture in (["x86_64", "aarch64"] if args.arch == "all" else [args.arch]):
        build(architecture)
