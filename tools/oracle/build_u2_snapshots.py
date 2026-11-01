"""Version and referenced-symbol scenarios in complete portable target views."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from capture_snapshot import capture
from elf_mutations import weaken_or_detach_version

ROOT = Path(__file__).resolve().parents[2]


def build():
    outcomes = []
    for arch, machine in [("x86_64", 62), ("aarch64", 183)]:
        source = ROOT / "fixtures/generated" / arch
        cc = "gcc" if machine == 62 else "aarch64-linux-gnu-gcc"
        system = Path("/lib/x86_64-linux-gnu") if machine == 62 else Path("/usr/aarch64-linux-gnu/lib")
        interpreter = "/lib64/ld-linux-x86-64.so.2" if machine == 62 else "/lib/ld-linux-aarch64.so.1"
        loader = system / Path(interpreter).name
        unversioned = source / "unversioned"
        unversioned.mkdir(exist_ok=True)
        subprocess.run([cc, "-shared", "-fPIC", str(ROOT / "fixtures/src/library.c"),
            "-Wl,-soname,libdemo.so.1", "-o", str(unversioned / "libdemo.so.1")], check=True)
        with_versions = source / "unversioned-with-versions"
        with_versions.mkdir(exist_ok=True)
        subprocess.run([cc, "-shared", "-fPIC", str(ROOT / "fixtures/src/unversioned.c"),
            "-Wl,-soname,libdemo.so.1", "-o", str(with_versions / "libdemo.so.1")], check=True)
        subprocess.run([cc, str(ROOT / "fixtures/src/weak.c"), "-o", str(source / "weak-app")], check=True)
        for name, weak, detach in [("node-only", False, True), ("weak-node", True, True), ("weak-node-strong-symbol", True, False)]:
            target = source / name
            target.write_bytes(weaken_or_detach_version((source / "version-app").read_bytes(), weak=weak, detach=detach))
            target.chmod(0o755)
        cases = [("baseline", "app", "old", True), ("new-environment", "version-app", "new-version", True),
                 ("old-environment", "version-app", "old", False),
                 ("used-export-removed", "app", "removed", False),
                 ("unused-export-removed", "stable-app", "removed", True),
                 ("unversioned-provider", "app", "unversioned", False),
                 ("unversioned-with-versions", "app", "unversioned-with-versions", True),
                 ("sectionless", "app.sectionless", "old", True),
                 ("weak-symbol", "weak-app", "old", True),
                 ("node-only", "node-only", "old", False),
                 ("weak-node", "weak-node", "old", True),
                 ("weak-node-strong-symbol", "weak-node-strong-symbol", "old", False)]
        for case, program, library, expected in cases:
            folder = ROOT / "fixtures/generated/u2" / arch / case
            root = folder / "root"
            for directory in ["opt/demo", "runtime", Path(interpreter).parent.as_posix().lstrip("/")]:
                (root / directory).mkdir(parents=True, exist_ok=True)
            shutil.copy2(source / program, root / "opt/demo/app")
            shutil.copy2(source / library / "libdemo.so.1", root / "runtime/libdemo.so.1")
            shutil.copy2(system / "libc.so.6", root / "runtime/libc.so.6")
            shutil.copy2(loader, root / interpreter.lstrip("/"))
            profile = dict(rule_revision="glibc-2.35-controlled-v2", loader_family="glibc", machine=machine,
                loader_path_hex=interpreter.encode().hex(), loader_sha256=hashlib.sha256(loader.read_bytes()).hexdigest(),
                cwd_hex=b"/".hex(), default_dirs_hex=[], library_path_hex=[b"/runtime".hex()],
                cache_mode="disabled", hwcaps_policy="none", secure_execution=False, preload=[], audit=[])
            capture(root, profile, folder / "snapshot")
            prefix = [] if machine == 62 else [str(ROOT / ".tools/reference/qemu/usr/bin/qemu-aarch64-static")]
            command = prefix + [str(root / interpreter.lstrip("/")), "--inhibit-cache", "--glibc-hwcaps-mask", "",
                "--library-path", str(root / "runtime"), str(root / "opt/demo/app")]
            result = subprocess.run(command, capture_output=True, text=True, timeout=15,
                env={key: value for key, value in os.environ.items() if not key.startswith("LD_")})
            if (result.returncode == 0) != expected:
                raise AssertionError((arch, case, result.returncode, result.stderr))
            outcomes.append(dict(architecture=arch, case=case, exit_code=result.returncode,
                expected_success=expected, stderr=result.stderr.replace(str(ROOT), "$PROJECT"),
                command=[part.replace(str(ROOT), "$PROJECT") for part in command]))
    (ROOT / "fixtures/generated/u2/oracle.json").write_text(json.dumps(outcomes, indent=2) + "\n")
    print(f"U2: {len(outcomes)} version/symbol loader outcomes matched")


if __name__ == "__main__":
    build()
