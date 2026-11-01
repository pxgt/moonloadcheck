"""Exercise public CLI exits and compare deterministic reports across backends."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def verify(js=None, native=None, compare_dir=None):
    commands = [["node", str(js.resolve())]] if js else []
    if native:
        commands.append([str(native.resolve())])
    if not commands:
        raise ValueError("supply at least one backend")
    artifacts = ROOT / "artifacts/cli"
    artifacts.mkdir(parents=True, exist_ok=True)
    count = 0

    def check(folder, expected, label, entry="/opt/relocated-demo/app"):
        nonlocal count
        reports = []
        for command in commands:
            result = subprocess.run(command + ["check", "--snapshot", str(folder), "--entry", entry,
                "--scope", "dependencies", "--format", "json"], capture_output=True, text=True, timeout=30)
            if result.returncode != expected:
                raise AssertionError((label, result.returncode, result.stdout, result.stderr))
            report = json.loads(result.stdout)
            if report["status"] != {0: "pass_static", 1: "fail", 2: "inconclusive", 3: "input_error"}[expected]:
                raise AssertionError((label, report))
            reports.append(report)
            count += 1
        if any(report != reports[0] for report in reports[1:]):
            raise AssertionError("backend report mismatch: " + label)
        if compare_dir and json.loads((compare_dir / (label + ".json")).read_text()) != reports[0]:
            raise AssertionError("cross-host report mismatch: " + label)
        (artifacts / (label + ".json")).write_text(json.dumps(reports[0], sort_keys=True, indent=2) + "\n")

    for arch in ["x86_64", "aarch64"]:
        for case, expected in [("runpath", 1), ("rpath", 0), ("fixed", 0), ("wrong-machine-first", 0),
                               ("directory-first", 1), ("pie-first", 1), ("symlink-origin", 0)]:
            folder = ROOT / "fixtures/generated/u1" / arch / case / "snapshot"
            check(folder, expected, arch + "-" + case)
    source = ROOT / "fixtures/generated/u1/x86_64/fixed/snapshot"
    check(source, 3, "missing-entry", "/absent")
    folder = Path(tempfile.mkdtemp(prefix="negative-", dir=artifacts))
    shutil.copytree(source, folder, dirs_exist_ok=True)
    manifest = json.loads((folder / "manifest.json").read_text())
    manifest["profile"]["cache_mode"] = "enabled"
    (folder / "manifest.json").write_text(json.dumps(manifest))
    check(folder, 2, "unknown-cache")
    blob = next((folder / "blobs").iterdir())
    blob.write_bytes(b"tampered")
    check(folder, 3, "tampered-blob")
    print(f"CLI: {count} exit/report checks passed on {len(commands)} backend(s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--js", type=Path)
    parser.add_argument("--native", type=Path)
    parser.add_argument("--compare-dir", type=Path)
    args = parser.parse_args()
    verify(args.js, args.native, args.compare_dir)
