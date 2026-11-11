"""Verify a standalone MoonBit/FFI application's complete deployment workflow.

Only this explicit reference verifier executes our original application. The
general check_deployment.py command never executes analyzed programs.
"""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

from check_deployment import STATUSES, write_json
from corpus.build_roots import target_file, loader_command

ROOT = Path(__file__).resolve().parents[1]
ENTRY = "/opt/sensor-report/bin/sensor-report"
LOADER = "/lib64/ld-linux-x86-64.so.2"
EXPECTED = dict(samples=3, min_milli_c=19750, max_milli_c=24750, mean_milli_c=22250)


def invoke(command, expected, cwd=None):
    result = subprocess.run(list(map(str, command)), cwd=cwd, capture_output=True, text=True, timeout=180)
    if result.returncode != expected:
        raise AssertionError((command, expected, result.returncode, result.stdout[-3000:], result.stderr[-3000:]))
    return result


def verify(native, js):
    if not __debug__:
        raise RuntimeError("verification requires Python assertions")
    if sys.platform != "linux":
        raise RuntimeError("capture and the independent loader oracle require Linux")
    parent = ROOT / "fixtures/generated/deployment"
    parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="sensor-report-", dir=parent))
    backend_commands = {"native": [str(native.resolve())], "js": ["node", str(js.resolve())]}
    cases, reports, gate_checks = [], {}, 0

    # Build outside the main module and without any workspace/source override.
    with tempfile.TemporaryDirectory(prefix="mlc independent app ") as separate:
        app = Path(separate) / "sensor_report"
        shutil.copytree(ROOT / "examples/sensor_report", app,
                        ignore=shutil.ignore_patterns("_build", ".mooncakes", ".moonagent", "__pycache__"))
        assert "moonloadcheck" not in (app / "moon.mod").read_text().lower()
        assert not (app / "moon.work").exists()
        invoke([sys.executable, app / "build.py"], 0, app)
        invoke(["moon", "check", "--target", "native", "--deny-warn"], 0, app)
        interface = (app / "pkg.generated.mbti").read_text()
        invoke(["moon", "info", "--target", "native"], 0, app)
        assert (app / "pkg.generated.mbti").read_text() == interface
        invoke(["moon", "fmt", "--check"], 0, app)
        environment = dict(os.environ, LD_LIBRARY_PATH=str(app / "_build/ffi"))
        subprocess.run(["moon", "test", "--target", "native", "--deny-warn"], cwd=app,
                       env=environment, timeout=120, check=True)
        executable = app / "_build/native/debug/build/sensor_report.exe"
        dynamic = invoke(["readelf", "-dW", executable], 0).stdout
        versions = invoke(["readelf", "-VW", executable], 0).stdout
        assert "libsensorcal.so.1" in dynamic and "$ORIGIN/../lib" in dynamic and "SENSOR_2.0" in versions
        program_digest = hashlib.sha256(executable.read_bytes()).hexdigest()

        for label, suite, variant, expected in [
            ("good", "jammy", "current", 0),
            ("missing-library", "jammy", "missing", 1),
            ("old-library", "jammy", "legacy", 1),
            ("fixed", "jammy", "current", 0),
            ("noble", "noble", "current", 0),
        ]:
            folder = work / label
            stage = folder / "root"
            for path in [stage / "runtime", stage / "lib64", stage / "opt/sensor-report/bin", stage / "opt/sensor-report/lib"]:
                path.mkdir(parents=True, exist_ok=True)
            shutil.copy2(executable, stage / ENTRY.lstrip("/"))
            source = ROOT / ".tools/corpus/roots" / suite / "amd64"
            shutil.copy2(target_file(source, LOADER), stage / LOADER.lstrip("/"))
            for name in ["libc.so.6", "libm.so.6", "libgcc_s.so.1"]:
                shutil.copy2(target_file(source, "/lib/x86_64-linux-gnu/" + name), stage / "runtime" / name)
            if variant != "missing":
                shutil.copy2(app / "_build/ffi" / (variant + ".so"), stage / "opt/sensor-report/lib/libsensorcal.so.1")
            profile = dict(rule_revision="glibc-2.35-controlled-v2" if suite == "jammy" else "ubuntu-noble-2.39-0ubuntu8-v1",
                loader_family="glibc", machine=62, loader_path=LOADER,
                loader_sha256=hashlib.sha256((stage / LOADER.lstrip("/")).read_bytes()).hexdigest(),
                cwd="/", default_dirs=[], library_path=["/runtime"], cache_mode="disabled", hwcaps_policy="none",
                secure_execution=False, preload=[], audit=[])
            config = dict(schema_version=1, root="root", entries=[ENTRY], scope="compatibility", profile=profile)
            config_path = folder / "deployment.json"
            write_json(config_path, config)
            case_reports = []
            for backend, binary in [("native", native), ("js", js)]:
                out = folder / backend
                result = invoke([sys.executable, ROOT / "tools/check_deployment.py", "--config", config_path,
                    "--out", out, "--" + backend, binary.resolve()], expected, app)
                summary = json.loads(result.stdout)
                assert summary == json.loads((out / "summary.json").read_text())
                assert summary["status"] == STATUSES[expected] and len(summary["reports"]) == 1
                report = json.loads((out / "report-000.json").read_text())
                obj = next(item for item in report["objects"] if item["path"]["display"] == ENTRY)
                assert obj["sha256"] == program_digest
                if expected == 0:
                    edge = next(e for e in report["edges"] if e["needed"]["display"] == "libsensorcal.so.1")
                    assert edge["selected"]["display"] == "/opt/sensor-report/lib/libsensorcal.so.1"
                    assert edge["trace"], "dependency selection must retain evidence"
                if label == "missing-library":
                    assert any(f["code"] == "MLC002" for f in report["findings"])
                if label == "old-library":
                    assert any(f["code"] == "MLC004" and f.get("version", {}).get("display") == "SENSOR_2.0" for f in report["findings"])
                case_reports.append(report)
                gate_checks += 1
            assert case_reports[0] == case_reports[1], label + " backend mismatch"
            reports[label] = case_reports[0]

            command = loader_command(stage, "amd64", LOADER, ["/runtime"])
            environment = {"PATH": os.environ["PATH"], "LC_ALL": "C", "LD_BIND_NOW": "1"}
            actual = subprocess.run(command + [ENTRY, "19500,22000,24500"], env=environment,
                                    capture_output=True, text=True, timeout=30, check=False)
            if expected == 0:
                assert actual.returncode == 0 and json.loads(actual.stdout) == EXPECTED, actual.stderr
            else:
                assert actual.returncode != 0 and "libsensorcal.so.1" in actual.stderr, actual.stderr
                if label == "old-library":
                    assert "SENSOR_2.0" in actual.stderr
            cases.append(dict(case=label, suite=suite, architecture="amd64", analyzer_exit=expected,
                loader_exit=actual.returncode, application_output=actual.stdout.strip(),
                loader_error=actual.stderr.strip(), program_sha256=program_digest, loader_sha256=profile["loader_sha256"]))
            print(label, "static", expected, "loader", actual.returncode, flush=True)

        # Exercise both 2 and 3 as actual CLI outcomes; neither may pass a CI gate.
        base = json.loads((work / "good/deployment.json").read_text())
        base["root"] = str(work / "good/root")
        for label, mutate, expected in [
            ("unverified-profile", lambda c: c["profile"].update(rule_revision="unverified-target"), 2),
            ("wrong-loader", lambda c: c["profile"].update(loader_sha256="0" * 64), 3),
            ("mixed-input-error", lambda c: c.update(entries=[ENTRY, "/not-a-program"]), 3),
        ]:
            config = copy.deepcopy(base)
            mutate(config)
            config_path = work / (label + ".json")
            write_json(config_path, config)
            for backend, binary in [("native", native), ("js", js)]:
                result = invoke([sys.executable, ROOT / "tools/check_deployment.py", "--config", config_path,
                    "--out", work / (label + "-" + backend), "--" + backend, binary.resolve()], expected, app)
                summary = json.loads(result.stdout)
                assert summary["status"] == STATUSES[expected], summary
                if label == "mixed-input-error":
                    assert [r["exit_code"] for r in summary["reports"]] == [0, 3]
                gate_checks += 1

        # Configuration errors fail before capturing anything; typos must not
        # silently fall back to this machine's environment or a default profile.
        for label, mutate in [
            ("missing-fact", lambda c: c["profile"].pop("library_path")),
            ("unknown-field", lambda c: c["profile"].update(library_paths=["/runtime"])),
            ("null-token", lambda c: c["profile"].update(lib_token=None)),
            ("boolean-machine", lambda c: c["profile"].update(machine=True)),
            ("relative-entry", lambda c: c.update(entries=["app"])),
            ("duplicate-entry", lambda c: c.update(entries=[ENTRY, ENTRY])),
        ]:
            config = copy.deepcopy(base)
            mutate(config)
            config_path, out = work / (label + ".json"), work / label
            write_json(config_path, config)
            result = invoke([sys.executable, ROOT / "tools/check_deployment.py", "--config", config_path,
                "--out", out, "--native", native.resolve()], 3, app)
            assert json.loads(result.stdout)["status"] == "input_error" and not out.exists()
            gate_checks += 1
        duplicate = work / "duplicate-key.json"
        duplicate.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
        for config_path, out in [(duplicate, work / "duplicate-key"),
                                 (work / "good/deployment.json", work / "good/native"),
                                 (work / "good/deployment.json", work / "good/root/nested-output")]:
            result = invoke([sys.executable, ROOT / "tools/check_deployment.py", "--config", config_path,
                "--out", out, "--native", native.resolve()], 3, app)
            assert json.loads(result.stdout)["status"] == "input_error"
            gate_checks += 1
        assert json.loads((work / "good/native/summary.json").read_text())["status"] == "pass_static"
        result = invoke([sys.executable, ROOT / "tools/check_deployment.py", "--not-an-option"], 3, app)
        assert json.loads(result.stdout)["status"] == "input_error"
        gate_checks += 1

        # Explain the real version finding, and compare failed/fixed views.
        entries = work / "entries.json"
        write_json(entries, [ENTRY])
        comparisons = []
        for backend, command in backend_commands.items():
            for before, after, expected, classification in [("good", "old-library", 1, "introduced"), ("old-library", "fixed", 0, "resolved")]:
                result = invoke(command + ["diff", "--before", work / before / backend / "snapshot", "--after",
                    work / after / backend / "snapshot", "--entries", entries, "--format", "json"], expected, app)
                diff = json.loads(result.stdout)
                assert not diff["entries"][0]["application_changed"]
                assert any(c["classification"] == classification for c in diff["entries"][0]["changes"])
                write_json(work / f"diff-{before}-{after}-{backend}.json", diff)
                comparisons.append(diff)
            finding = next(f for f in reports["old-library"]["findings"] if f["code"] == "MLC004")
            result = invoke(command + ["explain", "--report", work / "old-library" / backend / "report-000.json",
                                      "--finding", finding["id"]], 0, app)
            assert json.loads(result.stdout) == finding
        assert comparisons[0] == comparisons[2] and comparisons[1] == comparisons[3]

        # A linked/loaded application can still reject business input: this is
        # outside the static deployment result and must not be advertised away.
        result = subprocess.run(loader_command(work / "good/root", "amd64", LOADER, ["/runtime"]) + [ENTRY, "bad-input"],
                                env=environment, capture_output=True, text=True, timeout=30)
        assert result.returncode == 2

    record = dict(application="sensor_report", application_dependency_on_analyzer=False,
        program_sha256=program_digest, work=str(work), cases=cases, gate_checks=gate_checks,
        diff_checks=4, explain_checks=2, business_error_exit=2)
    output = ROOT / "artifacts/deployment"
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "result.json", record)
    print(f"Deployment integration: {gate_checks} gates, 5 loader cases, 4 diffs, 2 explanations; {work}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", required=True, type=Path)
    parser.add_argument("--js", required=True, type=Path)
    args = parser.parse_args()
    verify(args.native, args.js)
