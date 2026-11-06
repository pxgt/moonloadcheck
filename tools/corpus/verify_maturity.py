"""Binding/GLIBCXX/range evidence, exact backend reports and measured stress bounds."""
from pathlib import Path
import argparse
import json
import os
import platform
import signal
import subprocess
import tempfile
import time
from build_roots import ROOT


def verify(js=None, native=None, compare_dir=None, measure=False):
    commands = [("js", ["node", str(js.resolve())])] if js else []
    if native:
        commands.append(("native", [str(native.resolve())]))
    if not commands or (measure and platform.system() != "Linux"):
        raise ValueError("select a backend; process measurements require Linux")
    bindings = json.loads((ROOT / "fixtures/generated/bindings/oracle.json").read_text())
    glibcxx = json.loads((ROOT / "fixtures/generated/glibcxx/oracle.json").read_text())
    stress = json.loads((ROOT / "fixtures/generated/stress/oracle.json").read_text())
    assert (len(bindings), len(glibcxx), len(stress)) == (32, 12, 68)
    cases = []
    for row in bindings:
        parts = [row[k] for k in ["architecture", "suite", "case"]]
        code = 0 if row["case"] in ["interposition", "tls"] else 1 if row["case"] == "tls-missing" else 2
        cases.append(("bindings-" + "-".join(parts), ROOT / "fixtures/generated/bindings" / Path(*parts) / "snapshot", "/app", code, row, "bindings"))
    for row in glibcxx:
        parts = [row[k] for k in ["architecture", "case", "app"]]
        code = 1 if row["app"] == "modern" and row["case"] != "baseline" else 2
        cases.append(("glibcxx-" + "-".join(parts), ROOT / "fixtures/generated/glibcxx" / parts[0] / parts[1] / "snapshot",
                      "/app/" + row["app"], code, row, "glibcxx"))
    for row in stress:
        cases.append(("stress-" + row["architecture"] + "-" + row["case"], ROOT / "fixtures/generated/stress" / row["architecture"] / row["case"] / "snapshot",
                      "/app", row["expected_code"], row, "stress"))
    output = ROOT / "artifacts/maturity"
    output.mkdir(parents=True, exist_ok=True)
    measurements, checks = [], 0
    measured_cases = ["relocations-500000", "relocations-500001", "program-headers-4097", "virtual-memory-wrap"]
    with tempfile.TemporaryDirectory(prefix="moonloadcheck-stress-metrics-") as temporary:
        for label, folder, entry, code, row, group in cases:
            reports = []
            for backend, command in commands:
                arguments = command + ["check", "--snapshot", str(folder), "--entry", entry, "--scope", "compatibility", "--format", "json"]
                measured = measure and group == "stress" and row["case"] in measured_cases
                rss = Path(temporary) / "rss.txt"
                if measured:
                    arguments = ["/usr/bin/time", "-f", "%M", "-o", str(rss)] + arguments
                started = time.perf_counter()
                process = subprocess.Popen(arguments, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, start_new_session=measured)
                try:
                    stdout, stderr = process.communicate(timeout=60)
                except subprocess.TimeoutExpired:
                    if measured:
                        os.killpg(process.pid, signal.SIGKILL)
                    else:
                        process.kill()
                    process.communicate()
                    raise
                report = json.loads(stdout)
                assert process.returncode == code, (label, backend, process.returncode, report.get("findings", report), stderr)
                assert report["status"] == ["pass_static", "fail", "inconclusive", "input_error"][code]
                if group == "bindings":
                    slot = [c for c in report["symbol_checks"] if c["consumer"]["display"] == "/runtime/libclient.so.1" and c["symbol"]["display"] == "slot"]
                    if row["case"] in ["tls-type-first", "ordinary-to-tls"]:
                        assert len(slot) == 1 and slot[0]["status"] == "unknown"
                        selected = "/runtime/" + ("libfirst.so.1" if row["case"] == "tls-type-first" else "libprovider.so.1")
                        assert slot[0]["provider"]["display"] == selected
                        assert any("to " + selected in line for line in row["binding_lines"])
                    elif row["case"] in ["interposition", "tls", "tls-missing", "unique", "protected"]:
                        assert len(slot) == 1 and slot[0]["status"] == ({0: "pass", 1: "fail", 2: "unknown"}[code])
                elif group == "glibcxx":
                    required = [v for v in report["version_checks"] if v["consumer"]["display"] == entry and v["version"]["display"] == "GLIBCXX_3.4.32"]
                    if row["app"] == "modern":
                        assert len(required) == 1 and required[0]["status"] == ("fail" if code == 1 else "pass")
                        assert required[0]["provider"]["display"] == "/runtime/libstdc++.so.6"
                    else:
                        assert required == []
                    assert any(f["code"] == "MLC008" for f in report["findings"]), "unvalidated C++ runtime bindings must remain unknown"
                elif code:
                    assert any(f["code"] == ("MLC006" if code == 3 else "MLC009") for f in report["findings"])
                if measured:
                    peak = int(rss.read_text().strip().splitlines()[-1])
                    assert peak <= 512 * 1024, (label, backend, "RSS exceeds 512 MiB", peak)
                    measurements.append(dict(case=label, backend=backend, peak_rss_kib=peak,
                        seconds=round(time.perf_counter() - started, 4), input_bytes=row["byte_length"], expected_code=code))
                reports.append(report)
                checks += 1
            assert all(r == reports[0] for r in reports), "backend report mismatch: " + label
            if compare_dir:
                assert json.loads((compare_dir / (label + ".json")).read_text()) == reports[0], "cross-host mismatch: " + label
            (output / (label + ".json")).write_text(json.dumps(reports[0], sort_keys=True, indent=2) + "\n")
    if measure:
        (ROOT / "artifacts/stress-performance.json").write_text(json.dumps(dict(ceilings=dict(seconds=60, peak_rss_mib=512), measurements=measurements), indent=2) + "\n")
        print(f"Stress measurements: {len(measurements)} processes within 60 seconds / 512 MiB; peak {max(m['peak_rss_kib'] for m in measurements)} KiB")
    print(f"Maturity CLI: {checks} checks across {len(commands)} backend(s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--js", type=Path)
    parser.add_argument("--native", type=Path)
    parser.add_argument("--compare-dir", type=Path)
    parser.add_argument("--measure", action="store_true")
    args = parser.parse_args()
    verify(args.js, args.native, args.compare_dir, args.measure)
