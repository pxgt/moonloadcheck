"""Reproduce the relocation failure/fix against the loader and portable analyzer."""
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


def build():
    records = []
    for arch, machine in [("x86_64", 62), ("aarch64", 183)]:
        source = ROOT / "fixtures/generated" / arch
        system = Path("/lib/x86_64-linux-gnu") if machine == 62 else Path("/usr/aarch64-linux-gnu/lib")
        interpreter = "/lib64/ld-linux-x86-64.so.2" if machine == 62 else "/lib/ld-linux-aarch64.so.1"
        loader = system / Path(interpreter).name
        qemu = ROOT / ".tools/reference/qemu/usr/bin/qemu-aarch64-static"
        prefix = [] if machine == 62 else [str(qemu)]
        for case, expected in [("runpath", False), ("rpath", True), ("fixed", True),
                               ("wrong-machine-first", True), ("directory-first", False), ("pie-first", False),
                               ("symlink-origin", True)]:
            folder = ROOT / "fixtures/generated/u1" / arch / case
            root = folder / "root"
            app = root / "opt/relocated-demo"
            (app / "lib").mkdir(parents=True, exist_ok=True)
            (root / "lib").mkdir(parents=True, exist_ok=True)
            (root / interpreter.lstrip("/")).parent.mkdir(parents=True, exist_ok=True)
            source_case = case if case in ("runpath", "rpath", "fixed") else "fixed"
            for relative in ["app", "lib/libmiddle.so.1", "lib/libleaf.so.1"]:
                if case == "symlink-origin" and relative == "lib/libmiddle.so.1":
                    continue
                shutil.copy2(source / source_case / relative, app / relative)
            if case == "symlink-origin":
                (root / "store").mkdir(exist_ok=True)
                shutil.copy2(source / "fixed/lib/libmiddle.so.1", root / "store/libmiddle.so.1")
                link = app / "lib/libmiddle.so.1"
                if not link.is_symlink():
                    link.symlink_to("../../../store/libmiddle.so.1")
            shutil.copy2(system / "libc.so.6", root / "lib/libc.so.6")
            shutil.copy2(loader, root / interpreter.lstrip("/"))
            search = [b"/lib"]
            if case in ("wrong-machine-first", "directory-first", "pie-first"):
                (root / "bad").mkdir(exist_ok=True)
                search.insert(0, b"/bad")
                if case == "wrong-machine-first":
                    other_arch = "aarch64" if machine == 62 else "x86_64"
                    shutil.copy2(ROOT / "fixtures/generated" / other_arch / "fixed/lib/libmiddle.so.1",
                                 root / "bad/libmiddle.so.1")
                elif case == "directory-first":
                    (root / "bad/libmiddle.so.1").mkdir(exist_ok=True)
                else:
                    shutil.copy2(source / "fixed/app", root / "bad/libmiddle.so.1")
            # libc names the already-loaded interpreter by SONAME.
            profile = dict(
                rule_revision="glibc-2.35-controlled-v1", loader_family="glibc", machine=machine,
                loader_path_hex=interpreter.encode().hex(), loader_sha256=hashlib.sha256(loader.read_bytes()).hexdigest(),
                cwd_hex=b"/".hex(), default_dirs_hex=[], library_path_hex=[path.hex() for path in search],
                cache_mode="disabled", hwcaps_policy="none", secure_execution=False, preload=[], audit=[])
            capture(root, profile, folder / "snapshot")
            command = prefix + [str(root / interpreter.lstrip("/")), "--inhibit-cache", "--glibc-hwcaps-mask", "",
                                "--library-path", ":".join(str(root / path.decode().lstrip("/")) for path in search), str(app / "app")]
            result = subprocess.run(command, capture_output=True, text=True, timeout=15,
                env={key: value for key, value in os.environ.items() if not key.startswith("LD_")})
            if (result.returncode == 0) != expected:
                raise AssertionError((arch, case, result.stderr))
            records.append(dict(architecture=arch, case=case, expected_success=expected,
                exit_code=result.returncode, stderr=result.stderr.replace(str(ROOT), "$PROJECT"),
                command=[part.replace(str(ROOT), "$PROJECT") for part in command]))
    (ROOT / "fixtures/generated/u1/oracle.json").write_text(json.dumps(records, indent=2) + "\n")
    print(f"U1: {len(records)} relocated loader outcomes and snapshots generated")


if __name__ == "__main__":
    build()
