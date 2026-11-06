"""Exercise argument rejection, actionable errors and saved-report compatibility."""
from pathlib import Path
import argparse
import copy
import json
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def verify(js=None, native=None):
    commands = [("js", ["node", str(js.resolve())])] if js else []
    if native:
        commands.append(("native", [str(native.resolve())]))
    if not commands:
        raise ValueError("select a backend")
    folder = ROOT / "artifacts/cli-contract-inputs"
    folder.mkdir(parents=True, exist_ok=True)
    checks = 0

    def invoke(arguments, kind=None, message=None, text=False):
        nonlocal checks
        reports = []
        for backend, command in commands:
            result = subprocess.run(command + arguments, cwd=ROOT, capture_output=True, text=True, timeout=60)
            assert result.returncode == (3 if kind else 0), (backend, arguments, result.stdout, result.stderr)
            assert result.stderr == "", (backend, result.stderr)
            if text:
                assert result.stdout.startswith("usage:")
                reports.append(result.stdout)
            else:
                report = json.loads(result.stdout)
                if kind:
                    assert report["schema_version"] == 2 and report["status"] == "input_error"
                    assert report["error_kind"] == kind, report
                    assert message in report["message"], report
                reports.append(report)
            checks += 1
        assert all(report == reports[0] for report in reports), "backend contract mismatch"
        return reports[0]

    def path(file):
        return file.relative_to(ROOT).as_posix()

    def write(name, value):
        file = folder / name
        file.write_text(json.dumps(value), encoding="utf-8")
        return path(file)

    base = ["check", "--snapshot", "fixtures/generated/u1/x86_64/fixed/snapshot",
            "--entry", "/opt/relocated-demo/app", "--scope", "dependencies", "--format", "json"]
    for args in [[], ["invalid"], ["ignored", *base], [*base, "ignored"], base[:-1],
                 [*base, "--format", "json"], [*base[:-1], "xml"],
                 [*base[:6], "everything", *base[7:]]]:
        invoke(args, "arguments", "usage:")
    invoke(["--help"], text=True)
    missing = folder / "absent-report.json"
    assert not missing.exists()
    invoke(["explain", "--report", path(missing), "--finding", "any"], "io", path(missing))
    invoke([*base[:2], path(folder / "absent-snapshot"), *base[3:]], "io", "manifest.json")

    target = folder / "snapshot"
    (target / "blobs").mkdir(parents=True, exist_ok=True)
    manifest_file = target / "manifest.json"
    check_target = [*base[:2], path(target), *base[3:]]
    manifest_file.write_text("{", encoding="utf-8")
    invoke(check_target, "json", "end of JSON")
    manifest_file.write_text('{"schema_version":1}', encoding="utf-8")
    invoke(check_target, "json", "profile")
    source = json.loads((ROOT / base[2] / "manifest.json").read_text())
    for change, kind, expected in [
        (lambda m: m.update(schema_version=99), "snapshot", "unsupported snapshot schema"),
        (lambda m: m["profile"].update(lib_token_hex=""), "snapshot", "token"),
        (lambda m: m["entries"][0].update(path_hex="zz"), "snapshot", "hex strings"),
        (lambda m: None, "snapshot", "cannot read snapshot blob"),
    ]:
        manifest = copy.deepcopy(source)
        change(manifest)
        manifest_file.write_text(json.dumps(manifest), encoding="utf-8")
        invoke(check_target, kind, expected)

    saved = json.loads((ROOT / "fixtures/reports/schema-2.json").read_text())
    finding = saved["findings"][0]
    def explain(name, report, kind=None, message=None):
        return invoke(["explain", "--report", write(name, report), "--finding", finding["id"]], kind, message)
    assert explain("valid.json", saved) == finding
    assert explain("additive.json", {**saved, "future_optional_evidence": True}) == finding
    for version in [1, 3, 999]:
        explain(f"schema-{version}.json", {"schema_version": version}, "report", "unsupported report schema")
    for name, patch, expected in [
        ("duplicate", {"findings": [finding, finding]}, "duplicate finding id"),
        ("empty-id", {"findings": [{**finding, "id": ""}]}, "empty finding id"),
        ("bad-finding", {"findings": [{**finding, "status": "pass"}]}, "invalid finding status"),
        ("bad-status", {"status": "success"}, "invalid report status"),
        ("conflict", {"status": "pass_static"}, "report status conflicts"),
    ]:
        explain(name + ".json", {**saved, **patch}, "report", expected)
    invoke(["explain", "--report", "fixtures/reports/schema-2.json", "--finding", "absent"],
           "report", "finding id is not present")
    print(f"CLI contract: {checks} checks across {len(commands)} backend(s)")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--js", type=Path)
    parser.add_argument("--native", type=Path)
    args = parser.parse_args()
    verify(args.js, args.native)
