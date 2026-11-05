"""Check independent loader observations and declared-fact variants on either backend."""
from pathlib import Path
import argparse
import json
import subprocess
from build_environment_edges import ROOT, GENERATED


def verify(js=None, native=None, compare_dir=None):
    commands = [("js", ["node", str(js.resolve())])] if js else []
    if native:
        commands.append(("native", [str(native.resolve())]))
    if not commands:
        raise ValueError("select a backend")
    actual = json.loads((GENERATED / "oracle.json").read_text())
    facts = json.loads((GENERATED / "facts.json").read_text())
    assert len(actual) == 78 and len(facts) == 50
    output = ROOT / "artifacts/environment-edges"
    output.mkdir(parents=True, exist_ok=True)
    checks = 0
    for case in actual + facts:
        parts = [case[k] for k in ["architecture", "suite", "case"]] if "architecture" in case else ["facts", case["case"]]
        label = "-".join(parts)
        folder = GENERATED.joinpath(*parts) / "snapshot"
        reports = []
        for backend, command in commands:
            result = subprocess.run(command + ["check", "--snapshot", str(folder), "--entry", case["entry"],
                "--scope", "compatibility", "--format", "json"], capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            code = case["expected_code"]
            assert result.returncode == code, (label, backend, result.returncode, report.get("findings", report))
            assert report["status"] == ["pass_static", "fail", "inconclusive", "input_error"][code]
            for needed, selected in case["selected"].items():
                edges = [e for e in report["edges"] if e["needed"]["display"] == needed]
                assert len(edges) == 1, (label, needed, edges)
                assert edges[0].get("selected", {}).get("display") == selected, (label, edges[0])
            if case["case"] in ["cache-tls", "cache-os-old", "cache-os-future"]:
                assert any(t["source"] == "cache_unknown" for e in report["edges"] for t in e["trace"])
                assert any(f["code"] == "MLC007" for f in report["findings"])
            reports.append(report)
            checks += 1
        assert all(r == reports[0] for r in reports), "backend mismatch: " + label
        if compare_dir:
            assert json.loads((compare_dir / (label + ".json")).read_text()) == reports[0], "cross-host mismatch: " + label
        (output / (label + ".json")).write_text(json.dumps(reports[0], sort_keys=True, indent=2) + "\n")
    print(f"Environment CLI: {checks} checks across {len(commands)} backend(s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--js", type=Path)
    parser.add_argument("--native", type=Path)
    parser.add_argument("--compare-dir", type=Path)
    args = parser.parse_args()
    verify(args.js, args.native, args.compare_dir)
