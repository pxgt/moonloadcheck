"""Probe symbol scope, weak binding, visibility and default/nondefault versions."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from capture_snapshot import capture

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "fixtures/src"


def build():
    outcomes = []
    for arch, machine in [("x86_64", 62), ("aarch64", 183)]:
        cc = "gcc" if machine == 62 else "aarch64-linux-gnu-gcc"
        system = Path("/lib/x86_64-linux-gnu") if machine == 62 else Path("/usr/aarch64-linux-gnu/lib")
        interpreter = "/lib64/ld-linux-x86-64.so.2" if machine == 62 else "/lib/ld-linux-aarch64.so.1"
        loader = system / Path(interpreter).name
        prefix = [] if machine == 62 else [str(ROOT / ".tools/reference/qemu/usr/bin/qemu-aarch64-static")]
        for case in ["weak-first", "strong-first", "hidden-first", "main-interposition", "unversioned-oldest", "default-version", "explicit-old-version", "sysv-only"]:
            folder = ROOT / "fixtures/generated/symbols" / arch / case
            root, runtime = folder / "root", folder / "root/runtime"
            for path in [runtime, root / "opt/demo", (root / interpreter.lstrip("/")).parent]:
                path.mkdir(parents=True, exist_ok=True)

            def shared(source, soname, *flags):
                subprocess.run([cc, "-shared", "-fPIC", str(SRC / source), "-Wl,-soname," + soname,
                    *flags, "-o", str(runtime / soname)], check=True)

            app_source, expected, links = "app.c", 7, []
            if case in ["weak-first", "strong-first", "hidden-first"]:
                shared("binding.c", "libfirst.so.1", "-DHIDDEN" if case == "hidden-first" else "-DWEAK")
                shared("binding.c", "libsecond.so.1", "-DVALUE=9")
                links = ["-l:libfirst.so.1", "-l:libsecond.so.1"]
                if case == "strong-first":
                    links.reverse()
                expected = 7 if case == "weak-first" else 9
            elif case == "main-interposition":
                shared("interposed.c", "libinterposed.so.1")
                app_source, links = "interposer.c", ["-rdynamic", "-l:libinterposed.so.1"]
            elif case == "sysv-only":
                shared("binding.c", "libversions.so.1", "-Wl,--hash-style=sysv")
                links = ["-Wl,--hash-style=sysv", "-l:libversions.so.1"]
            else:
                shared("binding.c", "libversions.so.1")
                script = folder / "versions.map"
                script.write_text("SELECT_1 {}; SELECT_2 {} SELECT_1;\n")
                if case != "unversioned-oldest":
                    shared("versions.c", "libversions.so.1", "-Wl,--version-script=" + str(script))
                if case == "default-version":
                    expected = 9
                elif case == "explicit-old-version":
                    app_source = "version_ref.c"
                links = ["-l:libversions.so.1"]
            subprocess.run([cc, str(SRC / app_source), f"-DEXPECTED={expected}", "-Wl,-z,now", "-Wl,--no-as-needed",
                "-L" + str(runtime), *links, "-o", str(root / "opt/demo/app")], check=True)
            if case == "unversioned-oldest":
                shared("versions.c", "libversions.so.1", "-Wl,--version-script=" + str(script))
            shutil.copy2(system / "libc.so.6", runtime / "libc.so.6")
            shutil.copy2(loader, root / interpreter.lstrip("/"))
            profile = dict(rule_revision="glibc-2.35-controlled-v2", loader_family="glibc", machine=machine,
                loader_path_hex=interpreter.encode().hex(), loader_sha256=hashlib.sha256(loader.read_bytes()).hexdigest(),
                cwd_hex=b"/".hex(), default_dirs_hex=[], library_path_hex=[b"/runtime".hex()],
                cache_mode="disabled", hwcaps_policy="none", secure_execution=False, preload=[], audit=[])
            capture(root, profile, folder / "snapshot")
            result = subprocess.run(prefix + [str(loader), "--inhibit-cache", "--glibc-hwcaps-mask", "",
                "--library-path", str(runtime), str(root / "opt/demo/app")], capture_output=True, text=True, timeout=15,
                env={k: v for k, v in os.environ.items() if not k.startswith("LD_")})
            if result.returncode != 0:
                raise AssertionError((arch, case, result.returncode, result.stderr))
            outcomes.append(dict(architecture=arch, case=case, exit_code=result.returncode, expected_api_value=expected))
    (ROOT / "fixtures/generated/symbols/oracle.json").write_text(json.dumps(outcomes, indent=2) + "\n")
    print(f"Symbols: {len(outcomes)} binding/version loader outcomes matched")


if __name__ == "__main__":
    build()
