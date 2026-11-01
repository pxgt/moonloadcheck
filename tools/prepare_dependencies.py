"""M0-only manifest bridge for the published ELF 0.0.1 package.

The registry artifact still contains moon.mod.json. This only translates its
manifest in this checkout's dependency cache; no upstream source is patched.
It is not a solution for installing the eventual Mooncakes release.
"""
from pathlib import Path
import argparse
import json
import subprocess

def prepare(root):
    result = subprocess.run(["moon", "update"], cwd=root, capture_output=True, text=True)
    if result.returncode == 0:
        print("Dependencies available")
        return
    legacy = root / ".mooncakes/moonbit-community/elf/moon.mod.json"
    if "moon.mod.json" not in result.stdout + result.stderr or not legacy.is_file():
        raise RuntimeError(result.stdout + result.stderr)
    if not legacy.resolve().is_relative_to(root.resolve()):
        raise RuntimeError("dependency manifest escaped project root")
    module = json.loads(legacy.read_text())
    if (module.get("name"), module.get("version")) != ("moonbit-community/elf", "0.0.1"):
        raise RuntimeError("unexpected dependency version")
    modern = legacy.with_name("moon.mod")
    if modern.exists():
        raise RuntimeError("both manifest formats exist; inspect before changing")
    lines = [f'{key} = {json.dumps(module[key])}' for key in ["name", "version", "readme", "repository", "license", "description"] if key in module]
    lines += ["import {"]
    lines += ["  " + json.dumps(name + "@" + version) + "," for name, version in module.get("deps", {}).items()]
    lines += ["}"]
    modern.write_text("\n\n".join(lines) + "\n")
    legacy.unlink()
    subprocess.run(["moon", "update"], cwd=root, check=True)
    print("M0 bridge applied to ELF 0.0.1 manifest only")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    prepare(args.project.resolve())
