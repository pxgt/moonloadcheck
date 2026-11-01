"""CLI checks for path/graph oracles and the production resource limit."""
from pathlib import Path
import argparse
import json
import subprocess
from build_roots import ROOT


def verify(js=None, native=None, compare_dir=None):
    commands = [("js", ["node", str(js.resolve())])] if js else []
    if native:
        commands.append(("native", [str(native.resolve())]))
    if not commands:
        raise ValueError("select a backend")
    cases = json.loads((ROOT / "fixtures/generated/paths/oracle.json").read_text())
    assert len(cases) == 56
    output = ROOT / "artifacts/paths"
    output.mkdir(parents=True, exist_ok=True)
    checks = 0
    requests = []
    for case in cases:
        folder = ROOT / "fixtures/generated/paths" / case["architecture"] / case["suite"] / case["case"] / "snapshot"
        code = 3 if case["case"] == "corrupt-first" else 1 if case["exit_code"] != 0 else 0
        label = "-".join(case[k] for k in ["architecture", "suite", "case"])
        requests.append((label, folder, code, "compatibility"))
    requests.append(("dependency-step-limit", ROOT / "fixtures/generated/limits/dependency-steps/snapshot", 1, "dependencies"))
    for label, folder, code, scope in requests:
        reports = []
        for backend, command in commands:
            result = subprocess.run(command + ["check", "--snapshot", str(folder), "--entry", "/app", "--scope", scope, "--format", "json"],
                capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            assert result.returncode == code, (label, backend, result.returncode, report.get("findings"))
            if label == "dependency-step-limit":
                assert report["status"] == "fail"
                assert any(f["code"] == "MLC002" and f["status"] == "fail" for f in report["findings"])
                assert any(f["code"] == "MLC009" and f["status"] == "unknown" for f in report["findings"])
                assert 16000 < len(report["edges"]) <= 16384
            reports.append(report)
            checks += 1
        assert all(r == reports[0] for r in reports), "backend mismatch: " + label
        if compare_dir:
            assert json.loads((compare_dir / (label + ".json")).read_text()) == reports[0], "cross-host mismatch: " + label
        (output / (label + ".json")).write_text(json.dumps(reports[0], sort_keys=True, indent=2) + "\n")
    print(f"Path/limit CLI: {checks} checks across {len(commands)} backend(s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--js", type=Path)
    parser.add_argument("--native", type=Path)
    parser.add_argument("--compare-dir", type=Path)
    args = parser.parse_args()
    verify(args.js, args.native, args.compare_dir)
