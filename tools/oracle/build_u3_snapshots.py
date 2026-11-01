"""Two unchanged consumers, one removed export, two complete runtime views."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from capture_snapshot import capture

ROOT = Path(__file__).resolve().parents[2]


def build():
    outcomes = []
    for arch in ["x86_64", "aarch64"]:
        prefix = [] if arch == "x86_64" else [str(ROOT / ".tools/reference/qemu/usr/bin/qemu-aarch64-static")]
        for view, case in [("before", "baseline"), ("after", "used-export-removed")]:
            source = ROOT / "fixtures/generated/u2" / arch / case
            folder = ROOT / "fixtures/generated/u3" / arch / view
            root = folder / "root"
            shutil.copytree(source / "root", root, dirs_exist_ok=True)
            shutil.copy2(ROOT / "fixtures/generated" / arch / "stable-app", root / "opt/demo/stable-app")
            profile = json.loads((source / "snapshot/manifest.json").read_text())["profile"]
            capture(root, profile, folder / "snapshot")
            interpreter = bytes.fromhex(profile["loader_path_hex"]).decode()
            for program in ["app", "stable-app"]:
                expected = view == "before" or program == "stable-app"
                command = prefix + [str(root / interpreter.lstrip("/")), "--inhibit-cache", "--glibc-hwcaps-mask", "",
                    "--library-path", str(root / "runtime"), str(root / "opt/demo" / program)]
                result = subprocess.run(command, capture_output=True, text=True, timeout=15,
                    env={k: v for k, v in os.environ.items() if not k.startswith("LD_")})
                if (result.returncode == 0) != expected:
                    raise AssertionError((arch, view, program, result.returncode, result.stderr))
                outcomes.append(dict(architecture=arch, view=view, consumer=program, exit_code=result.returncode,
                    expected_success=expected, stderr=result.stderr.replace(str(ROOT), "$PROJECT")))
    folder = ROOT / "fixtures/generated/u3"
    (folder / "oracle.json").write_text(json.dumps(outcomes, indent=2) + "\n")
    (folder / "entries.json").write_text('["/opt/demo/app", "/opt/demo/stable-app"]\n')
    print(f"U3: {len(outcomes)} consumer/view loader outcomes matched")


if __name__ == "__main__":
    build()
