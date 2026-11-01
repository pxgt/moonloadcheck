"""Independent COPY lookup/size probes using own sources and locked runtimes."""
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

CASES = ["equal", "pie", "missing", "weak-missing", "smaller", "larger", "weak-first", "strong-first", "wrong-version", "protected"]


def symbol_position(data, name):
    tags, offset = tables(data)
    count = struct.unpack_from("<I", data, offset(tags[4]) + 4)[0]
    strings, symbols = offset(tags[5]), offset(tags[6])
    for index in range(count):
        pos = symbols + index * 24
        start = strings + struct.unpack_from("<I", data, pos)[0]
        if data[start:data.index(0, start)] == name:
            return pos
    raise ValueError("symbol missing: " + repr(name))


def build():
    outcomes = []
    for arch, machine, multiarch in [("amd64", 62, "x86_64-linux-gnu"), ("arm64", 183, "aarch64-linux-gnu")]:
        cc = "gcc" if machine == 62 else "aarch64-linux-gnu-gcc"
        interpreter = "/lib64/ld-linux-x86-64.so.2" if machine == 62 else "/lib/ld-linux-aarch64.so.1"
        for suite in ["jammy", "noble"]:
            for case in CASES:
                folder = ROOT / "fixtures/generated/copy" / arch / suite / case
                root = folder / "root"
                for path in [root / "runtime", (root / interpreter.lstrip("/")).parent]:
                    path.mkdir(parents=True, exist_ok=True)
                version_script = folder / "copy.map"
                version_script.write_text("COPY_1 {}; COPY_2 { global: data; read_data; };\n")

                def shared(name, *options):
                    subprocess.run([cc, "-shared", "-fPIC", str(ROOT / "fixtures/src/copy_data.c"),
                        "-Wl,--hash-style=both", "-Wl,-soname," + name,
                        "-Wl,--version-script=" + str(version_script), *options, "-o", str(root / "runtime" / name)], check=True)

                shared("libcopy.so.1", *(["-DWEAK"] if case in ["weak-first", "strong-first"] else []))
                libraries = ["-l:libcopy.so.1"]
                if case in ["weak-first", "strong-first"]:
                    shared("libsecond.so.1", "-DVALUE=9")
                    libraries += ["-l:libsecond.so.1"]
                    if case == "strong-first":
                        libraries.reverse()
                expected = 0 if case == "weak-missing" else 9 if case == "strong-first" else 7
                subprocess.run([cc, str(ROOT / "fixtures/src/copy_app.c"), "-fPIE" if case == "pie" else "-fno-pic",
                    "-pie" if case == "pie" else "-no-pie", "-Wl,-z,now", "-Wl,--hash-style=both",
                    "-Wl,--no-as-needed", "-DEXPECTED=" + str(expected), "-L" + str(root / "runtime"),
                    *libraries, "-o", str(root / "app")], check=True)
                if case in ["missing", "weak-missing"]:
                    shared("libcopy.so.1", "-DOMIT_DATA")
                elif case in ["smaller", "larger"]:
                    shared("libcopy.so.1", "-DCOUNT=" + ("2" if case == "smaller" else "8"))
                elif case == "wrong-version":
                    version_script.write_text("COPY_1 { global: data; }; COPY_2 { global: read_data; };\n")
                    shared("libcopy.so.1")
                if case in ["weak-missing", "protected"]:
                    path = root / "app" if case == "weak-missing" else root / "runtime/libcopy.so.1"
                    data = bytearray(path.read_bytes())
                    pos = symbol_position(data, b"data")
                    if case == "weak-missing":
                        data[pos + 4] = (2 << 4) | (data[pos + 4] & 15)
                    else:
                        data[pos + 5] = 3
                    path.write_bytes(data)
                readelf = subprocess.run(["readelf", "-rW", str(root / "app")], check=True, capture_output=True, text=True).stdout
                has_copy = not (arch == "arm64" and case == "pie")
                assert ("_COPY" in readelf) == has_copy and "data@COPY_2" in readelf, (arch, case, readelf)
                (folder / "readelf.txt").write_text(readelf)
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
                    command = loader_command(root, arch, interpreter, ["/runtime"]) + ["/app"]
                    result = subprocess.run(command, capture_output=True, text=True, timeout=30,
                        env={"PATH": os.environ["PATH"], "LC_ALL": "C", "LD_BIND_NOW": "1"})
                    failure = case in ["missing", "wrong-version"]
                    if failure:
                        assert result.returncode != 0 and ("undefined symbol: data" in result.stderr or "copy relocation against non-copyable protected symbol" in result.stderr), (arch, suite, case, result.returncode, result.stderr)
                    else:
                        assert result.returncode == 0, (arch, suite, case, result.returncode, result.stderr)
                    if case == "larger":
                        assert "different size" in result.stderr
                    outcomes.append(dict(architecture=arch, suite=suite, case=case, exit_code=result.returncode,
                        stderr=result.stderr, has_copy=has_copy, expected_data_value=expected, loader_sha256=profile["loader_sha256"],
                        app_sha256=hashlib.sha256((root / "app").read_bytes()).hexdigest(),
                        library_sha256=hashlib.sha256((root / "runtime/libcopy.so.1").read_bytes()).hexdigest(),
                        compiler=subprocess.check_output([cc, "-dumpfullversion"], text=True).strip(),
                        command=[part.replace(str(ROOT), "$PROJECT") for part in command]))
                    print(arch, suite, case, result.returncode, flush=True)
                finally:
                    if helper.is_file():
                        helper.unlink()
    (ROOT / "fixtures/generated/copy/oracle.json").write_text(json.dumps(outcomes, indent=2) + "\n")
    print(f"COPY: {len(outcomes)} independent loader outcomes matched")


if __name__ == "__main__":
    build()
