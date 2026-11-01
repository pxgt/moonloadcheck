"""A same-object exact version versus unversioned fallback, with forced hash order."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "oracle"))
from elf_mutations import tables
from build_roots import ROOT, target_file, loader_command, capture


def prepare(data, style):
    data = bytearray(data)
    tags, offset = tables(data)
    sym, versym, strings = offset(tags[6]), offset(tags[0x6ffffff0]), offset(tags[5])
    hashpos = offset(tags[4])
    nbucket, count = struct.unpack_from("<II", data, hashpos)
    found = {}
    for i in range(count):
        start = strings + struct.unpack_from("<I", data, sym + 24 * i)[0]
        if data[start:data.index(0, start)] == b"api":
            found[struct.unpack_from("<H", data, versym + 2 * i)[0] & 0x7fff] = i
    old, exact = found[2], found[3]
    # GNU chain order is dynsym order. SysV deliberately uses the opposite,
    # so an implementation scanning dynsym instead of buckets must fail.
    want_low = style == "gnu"
    if (old < exact) != want_low:
        a, b = sym + 24 * old, sym + 24 * exact
        data[a:a + 24], data[b:b + 24] = data[b:b + 24], data[a:a + 24]
        a, b = versym + 2 * old, versym + 2 * exact
        data[a:a + 2], data[b:b + 2] = data[b:b + 2], data[a:a + 2]
        old, exact = exact, old
    struct.pack_into("<H", data, versym + old * 2, 1)
    if style == "sysv":
        chainbase = hashpos + 8 + nbucket * 4
        for bucket in range(nbucket):
            chain = []
            index = struct.unpack_from("<I", data, hashpos + 8 + bucket * 4)[0]
            while index:
                chain.append(index)
                index = struct.unpack_from("<I", data, chainbase + index * 4)[0]
            if old in chain:
                assert exact in chain
                chain.remove(old)
                chain.insert(0, old)
                struct.pack_into("<I", data, hashpos + 8 + bucket * 4, chain[0])
                for left, right in zip(chain, chain[1:] + [0]):
                    struct.pack_into("<I", data, chainbase + left * 4, right)
        phoff = struct.unpack_from("<Q", data, 32)[0]
        width, count = struct.unpack_from("<HH", data, 54)
        for i in range(count):
            pos = phoff + width * i
            if struct.unpack_from("<I", data, pos)[0] == 2:
                start, size = struct.unpack_from("<Q", data, pos + 8)[0], struct.unpack_from("<Q", data, pos + 32)[0]
                for p in range(start, start + size, 16):
                    if struct.unpack_from("<Q", data, p)[0] == 0x6ffffef5:
                        struct.pack_into("<QQ", data, p, 21, 0)  # Ignore GNU hash; retain SysV.
    return bytes(data)


def build():
    outcomes = []
    for arch, machine in [("amd64", 62), ("arm64", 183)]:
        cc = "gcc" if arch == "amd64" else "aarch64-linux-gnu-gcc"
        interpreter = "/lib64/ld-linux-x86-64.so.2" if arch == "amd64" else "/lib/ld-linux-aarch64.so.1"
        multiarch = "x86_64-linux-gnu" if arch == "amd64" else "aarch64-linux-gnu"
        for suite, expected in [("jammy", 7), ("noble", 7)]:
            for style in ["gnu", "sysv"]:
                folder = ROOT / "fixtures/generated/fallback" / arch / suite / style
                root = folder / "root"
                for path in [root / "runtime", (root / interpreter.lstrip("/")).parent]:
                    path.mkdir(parents=True, exist_ok=True)
                script = folder / "versions.map"
                script.write_text("SELECT_1 {}; SELECT_2 {} SELECT_1;\n")
                library = root / "runtime/libversions.so.1"
                subprocess.run([cc, "-shared", "-fPIC", str(ROOT / "fixtures/src/versions.c"), "-Wl,--hash-style=both",
                    "-Wl,-soname,libversions.so.1", "-Wl,--version-script=" + str(script), "-o", str(library)], check=True)
                subprocess.run([cc, str(ROOT / "fixtures/src/version_choice.c"), "-L" + str(root / "runtime"),
                    "-Wl,-z,now", "-l:libversions.so.1", "-o", str(root / "app")], check=True)
                library.write_bytes(prepare(library.read_bytes(), style))
                source = ROOT / ".tools/corpus/roots" / suite / arch
                shutil.copy2(target_file(source, interpreter), root / interpreter.lstrip("/"))
                shutil.copy2(target_file(source, "/lib/" + multiarch + "/libc.so.6"), root / "runtime/libc.so.6")
                profile = dict(rule_revision="glibc-2.35-controlled-v2" if suite == "jammy" else "ubuntu-noble-2.39-0ubuntu8-v1",
                    loader_family="glibc", machine=machine, loader_path_hex=interpreter.encode().hex(),
                    loader_sha256=hashlib.sha256((root / interpreter.lstrip("/")).read_bytes()).hexdigest(), cwd_hex=b"/".hex(),
                    default_dirs_hex=[], library_path_hex=[b"/runtime".hex()], cache_mode="disabled", hwcaps_policy="none",
                    secure_execution=False, preload=[], audit=[])
                helper = root / "qemu"
                if helper.is_file():
                    helper.unlink()
                capture(root, profile, folder / "snapshot")
                if arch == "arm64":
                    shutil.copy2(ROOT / ".tools/reference/qemu/usr/bin/qemu-aarch64-static", helper)
                try:
                    result = subprocess.run(loader_command(root, arch, interpreter, ["/runtime"]) + ["/app"],
                        capture_output=True, text=True, timeout=30, env={"PATH": os.environ["PATH"], "LC_ALL": "C"})
                    if result.returncode != expected:
                        raise AssertionError((arch, suite, style, expected, result.returncode, result.stderr))
                    outcomes.append(dict(architecture=arch, suite=suite, hash_style=style, api_return_value=expected,
                        library_sha256=hashlib.sha256(library.read_bytes()).hexdigest(), loader_sha256=profile["loader_sha256"]))
                finally:
                    if helper.is_file():
                        helper.unlink()
    (ROOT / "fixtures/generated/fallback/oracle.json").write_text(json.dumps(outcomes, indent=2) + "\n")
    print(f"Fallback: {len(outcomes)} release-specific lookup outcomes matched")


if __name__ == "__main__":
    build()
