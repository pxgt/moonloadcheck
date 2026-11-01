"""Exercise public CLI exits, offline explanations and cross-backend determinism."""
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

    def invoke(args, expected, label, check_status=True):
        nonlocal count
        reports = []
        for command in commands:
            result = subprocess.run(command + list(map(str, args)),
                capture_output=True, text=True, timeout=60)
            if result.returncode != expected:
                raise AssertionError((label, result.returncode, result.stdout[:8000], result.stderr))
            report = json.loads(result.stdout)
            if check_status and report["status"] != {0: "pass_static", 1: "fail", 2: "inconclusive", 3: "input_error"}[expected]:
                raise AssertionError((label, report["status"]))
            reports.append(report)
            count += 1
        if any(report != reports[0] for report in reports[1:]):
            raise AssertionError("backend report mismatch: " + label)
        if compare_dir and json.loads((compare_dir / (label + ".json")).read_text()) != reports[0]:
            raise AssertionError("cross-host report mismatch: " + label)
        (artifacts / (label + ".json")).write_text(json.dumps(reports[0], sort_keys=True, indent=2) + "\n")
        return reports[0]

    def check(folder, expected, label, entry="/opt/relocated-demo/app", scope="dependencies"):
        return invoke(["check", "--snapshot", folder, "--entry", entry,
            "--scope", scope, "--format", "json"], expected, label)

    for arch in ["x86_64", "aarch64"]:
        for case, expected in [("runpath", 1), ("rpath", 0), ("fixed", 0), ("wrong-machine-first", 0),
                               ("directory-first", 1), ("pie-first", 1), ("symlink-origin", 0)]:
            folder = ROOT / "fixtures/generated/u1" / arch / case / "snapshot"
            check(folder, expected, arch + "-" + case)
        for case, expected in [("baseline", 0), ("new-environment", 0), ("old-environment", 1),
                               ("used-export-removed", 1), ("unused-export-removed", 0),
                               ("unversioned-provider", 1), ("unversioned-with-versions", 0),
                               ("sectionless", 0), ("weak-symbol", 0), ("node-only", 1),
                               ("weak-node", 0), ("weak-node-strong-symbol", 1)]:
            folder = ROOT / "fixtures/generated/u2" / arch / case / "snapshot"
            report = check(folder, expected, arch + "-u2-" + case, "/opt/demo/app", "compatibility")
            if len({f["id"] for f in report["findings"]}) != len(report["findings"]):
                raise AssertionError("ambiguous finding identifiers")
        for case, expected in [("preferred", 0), ("disabled", 0), ("stale-first", 0),
                               ("nodeflib-allowed", 0), ("nodeflib-filtered", 1)]:
            check(ROOT / "fixtures/generated/cache" / arch / case / "snapshot",
                  expected, arch + "-cache-" + case, "/app")
        check(ROOT / "fixtures/generated/tokens" / arch / "snapshot", 0, arch + "-tokens",
              "/opt/demo/app", "compatibility")
        check(ROOT / "fixtures/generated/tokens" / arch / "unknown-snapshot", 2, arch + "-unknown-token",
              "/opt/demo/app", "compatibility")
        for case in ["weak-first", "strong-first", "hidden-first", "main-interposition",
                     "unversioned-oldest", "default-version", "explicit-old-version", "sysv-only"]:
            check(ROOT / "fixtures/generated/symbols" / arch / case / "snapshot",
                  0, arch + "-symbols-" + case, "/opt/demo/app", "compatibility")
        before = ROOT / "fixtures/generated/u3" / arch / "before/snapshot"
        after = ROOT / "fixtures/generated/u3" / arch / "after/snapshot"
        entries = ROOT / "fixtures/generated/u3/entries.json"
        for label, left, right, expected, classification in [
                ("introduced", before, after, 1, "introduced"),
                ("existing", after, after, 1, "existing"),
                ("resolved", after, before, 0, "resolved"),
                ("unchanged", before, before, 0, None)]:
            report = invoke(["diff", "--before", left, "--after", right, "--entries", entries, "--format", "json"],
                            expected, arch + "-diff-" + label)
            changes = report["entries"][0]["changes"]
            if classification is None:
                assert changes == []
            else:
                assert len(changes) == 1 and changes[0]["classification"] == classification
            assert report["entries"][1]["after"]["status"] == "pass_static"
            assert all(not item["application_changed"] for item in report["entries"])
        original = json.loads((artifacts / (arch + "-u2-used-export-removed.json")).read_text())
        finding = original["findings"][0]
        # This command receives only a saved report. It has no snapshot argument.
        explained = invoke(["explain", "--report", artifacts / (arch + "-u2-used-export-removed.json"),
            "--finding", finding["id"]], 0, arch + "-explain", check_status=False)
        assert explained == finding

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
    report_path = artifacts / "x86_64-u2-used-export-removed.json"
    invoke(["explain", "--report", report_path, "--finding", "absent"], 3, "absent-finding")
    (folder / "entries.json").write_text("[]")
    invoke(["diff", "--before", source, "--after", source, "--entries", folder / "entries.json",
            "--format", "json"], 3, "empty-consumers")
    future = json.loads(report_path.read_text())
    future["schema_version"] = 999
    (folder / "future.json").write_text(json.dumps(future))
    invoke(["explain", "--report", folder / "future.json", "--finding", "any"], 3, "future-report")
    invoke(["invalid-command"], 3, "invalid-command")
    print(f"CLI: {count} exit/report checks passed on {len(commands)} backend(s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--js", type=Path)
    parser.add_argument("--native", type=Path)
    parser.add_argument("--compare-dir", type=Path)
    args = parser.parse_args()
    verify(args.js, args.native, args.compare_dir)
