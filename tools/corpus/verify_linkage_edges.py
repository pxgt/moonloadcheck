"""CLI validation of linkage boundaries, including non-predictive static results."""
from pathlib import Path
import argparse
import json
import subprocess
from build_linkage_edges import ROOT, NOT_EXECUTED


def verify(js=None, native=None, compare_dir=None):
    commands = [("js", ["node", str(js.resolve())])] if js else []
    if native:
        commands.append(("native", [str(native.resolve())]))
    if not commands:
        raise ValueError("select a backend")
    cases = json.loads((ROOT / "fixtures/generated/linkage-edges/oracle.json").read_text())
    assert len(cases) == 60 and sum(len(c["executions"]) for c in cases) == 56
    output = ROOT / "artifacts/linkage-edges"
    output.mkdir(parents=True, exist_ok=True)
    checks = 0
    for case in cases:
        label = "-".join(case[k] for k in ["architecture", "suite", "case"])
        folder = ROOT / "fixtures/generated/linkage-edges" / case["architecture"] / case["suite"] / case["case"] / "snapshot"
        code = 1 if case["case"] in ["lazy-missing", "raw-mismatch"] else 2 if case["case"].startswith("unknown-") else 0
        executions = case["executions"]
        if case["case"] in NOT_EXECUTED:
            assert executions == []
        elif case["case"] == "lazy-missing":
            assert [r["exit_code"] for r in executions] == [0, 127, 127]
        elif case["case"] == "ifunc-wrong-value":
            assert executions[0]["exit_code"] == 41 and code == 0
        else:
            assert executions[0]["exit_code"] == (127 if case["case"] == "raw-mismatch" else 0)
        reports = []
        for backend, command in commands:
            result = subprocess.run(command + ["check", "--snapshot", str(folder), "--entry", "/app", "--scope", "compatibility", "--format", "json"],
                capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            assert result.returncode == code, (label, backend, result.returncode, report.get("findings"))
            if case["case"] == "lazy-missing":
                assert any(c["symbol"]["display"] == "api" and c["phase"] == "startup-or-first-call" and c["status"] == "fail" for c in report["symbol_checks"])
            if case["case"].startswith("ifunc-"):
                assert "IFUNC resolver results" in report["not_checked"]
            if case["case"] in ["raw-name", "raw-mismatch"]:
                assert any(c["symbol"]["hex"] == "61ff69" and c["status"] == ("fail" if code else "pass") for c in report["symbol_checks"])
            reports.append(report)
            checks += 1
        assert all(r == reports[0] for r in reports), "backend mismatch: " + label
        if compare_dir:
            assert json.loads((compare_dir / (label + ".json")).read_text()) == reports[0], "cross-host mismatch: " + label
        (output / (label + ".json")).write_text(json.dumps(reports[0], sort_keys=True, indent=2) + "\n")
    print(f"Linkage edge CLI: {checks} checks across {len(commands)} backend(s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--js", type=Path)
    parser.add_argument("--native", type=Path)
    parser.add_argument("--compare-dir", type=Path)
    args = parser.parse_args()
    verify(args.js, args.native, args.compare_dir)
