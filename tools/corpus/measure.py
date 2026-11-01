"""Linux process-level time/RSS baseline with generous regression ceilings."""
from pathlib import Path
import argparse
import json
import os
import platform
import signal
import statistics
import subprocess
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]


def measure(js=None, native=None):
    commands = [("js", ["node", str(js.resolve())])] if js else []
    if native:
        commands.append(("native", [str(native.resolve())]))
    if platform.system() != "Linux" or not commands:
        raise ValueError("requires Linux, /usr/bin/time and at least one backend")
    folder = Path(tempfile.mkdtemp(prefix="moonloadcheck-metrics-"))
    entries = folder / "entries.json"
    entries.write_text(json.dumps(["/usr/bin/hello", "/usr/bin/jq", "/usr/bin/zstd"]))
    views = ROOT / "fixtures/generated/corpus/amd64"
    checks = [
        ("jq-native-runtime", 0, ["check", "--snapshot", str(views / "noble-on-noble/snapshot"), "--entry", "/usr/bin/jq", "--scope", "compatibility", "--format", "json"]),
        ("jq-downgrade", 1, ["check", "--snapshot", str(views / "noble-on-jammy/snapshot"), "--entry", "/usr/bin/jq", "--scope", "compatibility", "--format", "json"]),
        ("three-consumer-diff", 1, ["diff", "--before", str(views / "noble-on-noble/snapshot"), "--after", str(views / "noble-on-jammy/snapshot"), "--entries", str(entries), "--format", "json"]),
        ("copy-size-gap", 2, ["check", "--snapshot", str(ROOT / "fixtures/generated/copy/amd64/jammy/larger/snapshot"), "--entry", "/app", "--scope", "compatibility", "--format", "json"]),
    ]
    rows = []
    for backend, command in commands:
        for label, code, args in checks:
            times, memory, reference = [], [], None
            for _ in range(3):
                rss = folder / "rss.txt"
                started = time.perf_counter()
                process = subprocess.Popen(["/usr/bin/time", "-f", "%M", "-o", str(rss)] + command + args,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=ROOT, start_new_session=True)
                try:
                    stdout, stderr = process.communicate(timeout=60)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.communicate()
                    raise
                elapsed = time.perf_counter() - started
                report = json.loads(stdout)
                assert process.returncode == code, (label, process.returncode, stderr)
                if reference is not None:
                    assert report == reference, "unstable repeated report"
                reference = report
                peak = int(rss.read_text().strip().splitlines()[-1])
                assert peak <= 512 * 1024, (label, "RSS exceeds 512 MiB", peak)
                times.append(elapsed)
                memory.append(peak)
            row = dict(backend=backend, case=label, runs=3, seconds_median=round(statistics.median(times), 4),
                seconds_max=round(max(times), 4), peak_rss_kib=max(memory), report_bytes=len(stdout.encode()))
            rows.append(row)
            print(backend, label, row["seconds_median"], "seconds;", row["peak_rss_kib"], "KiB peak RSS", flush=True)
    output = ROOT / "artifacts/performance.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(dict(schema_version=1, revision=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        kernel=platform.release(), architecture=platform.machine(), cpu_count=os.cpu_count(),
        ceilings=dict(seconds_per_process=60, peak_rss_mib=512), measurements=rows), indent=2) + "\n")
    print(f"Resource baseline: {len(rows) * 3} measured processes; stable reports within time/RSS ceilings")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--js", type=Path)
    parser.add_argument("--native", type=Path)
    args = parser.parse_args()
    measure(args.js, args.native)
