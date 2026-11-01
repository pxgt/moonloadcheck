"""Check COPY matrix reports and compare independent backend/host executions."""
from pathlib import Path
import argparse
import json
import subprocess
from build_copy import ROOT


def verify(js=None, native=None, compare_dir=None):
    commands = [("js", ["node", str(js.resolve())])] if js else []
    if native:
        commands += [("native", [str(native.resolve())])]
    if not commands:
        raise ValueError("select a backend")
    cases = json.loads((ROOT / "fixtures/generated/copy/oracle.json").read_text())
    assert len(cases) == 40 and sum(c["has_copy"] for c in cases) == 38
    output = ROOT / "artifacts/copy"
    output.mkdir(parents=True, exist_ok=True)
    checks = 0
    for case in cases:
        label = "-".join(case[k] for k in ["architecture", "suite", "case"])
        folder = ROOT / "fixtures/generated/copy" / case["architecture"] / case["suite"] / case["case"] / "snapshot"
        code = 1 if case["case"] in ["missing", "wrong-version"] else 2 if case["case"] in ["smaller", "larger", "protected"] else 0
        reports = []
        for backend, command in commands:
            result = subprocess.run(command + ["check", "--snapshot", str(folder), "--entry", "/app", "--scope", "compatibility", "--format", "json"],
                capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            assert result.returncode == code, (label, backend, result.returncode, report)
            copies = [c for c in report["symbol_checks"] if c["lookup_policy"] == "copy-source-excluding-executable"]
            assert len(copies) == int(case["has_copy"]), label
            assert len({f["id"] for f in report["findings"]}) == len(report["findings"])
            reports.append(report)
            checks += 1
        assert all(r == reports[0] for r in reports), "backend mismatch: " + label
        if compare_dir:
            assert json.loads((compare_dir / (label + ".json")).read_text()) == reports[0], "cross-host mismatch: " + label
        (output / (label + ".json")).write_text(json.dumps(reports[0], sort_keys=True, indent=2) + "\n")
    print(f"COPY CLI: {checks} checks across {len(commands)} backend(s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--js", type=Path)
    parser.add_argument("--native", type=Path)
    parser.add_argument("--compare-dir", type=Path)
    args = parser.parse_args()
    verify(args.js, args.native, args.compare_dir)
