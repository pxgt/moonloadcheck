"""Compare portable analyzer reports with independently recorded target executions."""
from pathlib import Path
import argparse
import collections
import json
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]


def verify(js=None, native=None, inspect=False, compare_dir=None):
    commands = [("js", ["node", str(js.resolve())])] if js else []
    if native:
        commands.append(("native", [str(native.resolve())]))
    if not commands:
        raise ValueError("select a backend")
    oracle = json.loads((ROOT / "fixtures/generated/corpus/oracle.json").read_text())["cases"]
    output = ROOT / "artifacts/corpus"
    output.mkdir(parents=True, exist_ok=True)
    metrics, identities, count = [], {}, 0
    for case in oracle:
        source, target = case["case"].split("-on-")
        label = case["architecture"] + "-" + case["case"] + "-" + case["app"]
        identity_key = (case["architecture"], source, case["app"])
        old = identities.setdefault(identity_key, case["program_sha256"])
        assert old == case["program_sha256"], "migration changed the executable"
        expected = 1 if source == "noble" and target == "jammy" and case["app"] in ["hello", "jq"] else 0
        assert (case["exit_code"] != 0) == (expected != 0), "unexpected target execution result"
        reports = []
        for backend, command in commands:
            started = time.perf_counter()
            result = subprocess.run(command + ["check", "--snapshot", str(ROOT / "fixtures/generated/corpus" / case["architecture"] / case["case"] / "snapshot"),
                "--entry", "/usr/bin/" + case["app"], "--scope", "compatibility", "--format", "json"],
                capture_output=True, text=True, timeout=90)
            elapsed = time.perf_counter() - started
            report = json.loads(result.stdout)
            summary = collections.Counter(f["code"] + ":" + f["status"] for f in report.get("findings", []))
            if inspect:
                print(label, backend, report["status"], dict(summary), flush=True)
                for f in report.get("findings", [])[:4]:
                    print(" ", f["subject"]["display"], f.get("requirement", {}).get("display"), f["explanation"], flush=True)
            elif result.returncode != expected:
                raise AssertionError((label, backend, expected, result.returncode, summary, report.get("message")))
            if not inspect and expected == 1:
                assert any(f["code"] == "MLC004" and f.get("version", {}).get("display") == "GLIBC_2.38" for f in report["findings"])
            reports.append(report)
            metrics.append(dict(case=label, backend=backend, seconds=round(elapsed, 4), report_bytes=len(result.stdout.encode()),
                                objects=len(report.get("objects", [])), references=len(report.get("symbol_checks", []))))
            count += 1
        if any(report != reports[0] for report in reports[1:]):
            raise AssertionError("backend mismatch: " + label)
        if compare_dir and json.loads((compare_dir / (label + ".json")).read_text()) != reports[0]:
            raise AssertionError("cross-host mismatch: " + label)
        (output / (label + ".json")).write_text(json.dumps(reports[0], sort_keys=True, indent=2) + "\n")
    (output / "metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    print(f"Corpus CLI: {count} checks across {len(commands)} backend(s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--js", type=Path)
    parser.add_argument("--native", type=Path)
    parser.add_argument("--inspect", action="store_true")
    parser.add_argument("--compare-dir", type=Path)
    args = parser.parse_args()
    verify(args.js, args.native, args.inspect, args.compare_dir)
