"""Verify an independent MoonBit/FFI app on locked x86-64 and AArch64 targets.

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
from verify_targets import ARCHES, CATALOG, catalog

ROOT = Path(__file__).resolve().parents[1]
ENTRY = "/opt/sensor-report/bin/sensor-report"
QEMU = ROOT / ".tools/reference/qemu/usr/bin/qemu-aarch64-static"
EXPECTED = dict(samples=3, min_milli_c=19750, max_milli_c=24750, mean_milli_c=22250)
FACTS = dict(cwd="/", default_dirs=[], library_path=["/runtime"], cache_mode="disabled",
             hwcaps_policy="none", secure_execution=False, preload=[], audit=[])


def invoke(command, expected, cwd=None, env=None):
    result = subprocess.run(list(map(str, command)), cwd=cwd, env=env,
                            capture_output=True, text=True, timeout=180)
    if result.returncode != expected:
        raise AssertionError((command, expected, result.returncode, result.stdout[-3000:], result.stderr[-3000:]))
    return result


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_app(parent, arch):
    # No main-module import, workspace override, or source-tree build cache.
    app = parent / arch
    shutil.copytree(ROOT / "examples/sensor_report", app,
                    ignore=shutil.ignore_patterns("_build", ".mooncakes", ".moonagent", "__pycache__"))
    assert "moonloadcheck" not in (app / "moon.mod").read_text().lower()
    assert not (app / "moon.work").exists()
    invoke([sys.executable, app / "build.py", "--arch", arch], 0, app)
    invoke(["moon", "check", "--target", "native", "--deny-warn"], 0, app)
    interface = (app / "pkg.generated.mbti").read_text()
    invoke(["moon", "info", "--target", "native"], 0, app)
    assert (app / "pkg.generated.mbti").read_text() == interface
    invoke(["moon", "fmt", "--check"], 0, app)
    if arch == "amd64":
        environment = dict(os.environ, MOON_CC=shutil.which("gcc"), LD_LIBRARY_PATH=str(app / "_build/ffi"))
        invoke(["moon", "test", "--target", "native", "--deny-warn"], 0, app, environment)
    executable = app / "_build/native/debug/build/sensor_report.exe"
    header = executable.read_bytes()[:20]
    assert header[:6] == b"\x7fELF\x02\x01" and int.from_bytes(header[18:20], "little") == ARCHES[arch][0]
    dynamic = invoke(["readelf", "-dW", executable], 0).stdout
    versions = invoke(["readelf", "-VW", executable], 0).stdout
    assert "libsensorcal.so.1" in dynamic and "$ORIGIN/../lib" in dynamic and "SENSOR_2.0" in versions
    return app, executable


def run_application(stage, arch, interpreter, arguments):
    # Install QEMU only during execution, after capture. Neither QEMU nor any
    # target runtime is distributed; cleanup also runs after an oracle failure.
    helper = stage / "qemu"
    assert not helper.exists()
    try:
        if arch == "arm64":
            shutil.copy2(QEMU, helper)
        environment = {"PATH": os.environ["PATH"], "LC_ALL": "C", "LD_BIND_NOW": "1"}
        return subprocess.run(loader_command(stage, arch, interpreter, ["/runtime"]) + [ENTRY, arguments],
                              env=environment, capture_output=True, text=True, timeout=30)
    finally:
        if arch == "arm64":
            helper.unlink(missing_ok=True)


def verify(native, js):
    if not __debug__:
        raise RuntimeError("verification requires Python assertions")
    if sys.platform != "linux":
        raise RuntimeError("capture and the independent loader oracle require Linux")
    assert json.loads(CATALOG.read_text()) == catalog(), "verify the checked-in target identities first"
    parent = ROOT / "fixtures/generated/deployment"
    parent.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="sensor-report-", dir=parent))
    binaries = {"native": native.resolve(), "js": js.resolve()}
    commands = {"native": [str(binaries["native"])], "js": ["node", str(binaries["js"])]}
    cases, builds, business, reports = [], {}, [], {}
    gate_checks, diff_checks, explain_checks, parity_checks = 0, 0, 0, 0

    def check(config_path, out, backend, expected, no_output=False):
        nonlocal gate_checks
        result = invoke([sys.executable, ROOT / "tools/check_deployment.py", "--config", config_path,
                         "--out", out, "--" + backend, binaries[backend]], expected)
        summary = json.loads(result.stdout)
        assert summary["status"] == STATUSES[expected]
        if no_output:
            assert not out.exists()
        elif (out / "summary.json").exists() and expected != 3:
            assert summary == json.loads((out / "summary.json").read_text())
        gate_checks += 1
        return summary

    with tempfile.TemporaryDirectory(prefix="mlc independent apps ") as separate:
        apps = {arch: build_app(Path(separate), arch) for arch in ARCHES}
        for arch, (app, executable) in apps.items():
            machine, interpreter = ARCHES[arch]
            program_digest = digest(executable)
            builds[arch] = dict(json.loads((app / "_build/build.json").read_text()),
                                program_sha256=program_digest, elf_machine=machine)
            for suite in ["jammy", "noble"]:
                group = work / arch / suite
                target_id = f"ubuntu-{suite}-{arch}"
                source = ROOT / ".tools/corpus/roots" / suite / arch
                multiarch = "x86_64-linux-gnu" if arch == "amd64" else "aarch64-linux-gnu"
                for label, variant, expected in [("good", "current", 0), ("missing-library", "missing", 1),
                        ("old-library", "legacy", 1), ("fixed", "current", 0), ("wrong-architecture", "wrong", 1)]:
                    folder, stage = group / label, group / label / "root"
                    for path in [stage / interpreter.lstrip("/"), stage / ENTRY.lstrip("/"),
                                 stage / "opt/sensor-report/lib/libsensorcal.so.1"]:
                        path.parent.mkdir(parents=True, exist_ok=True)
                    (stage / "runtime").mkdir(exist_ok=True)
                    shutil.copy2(executable, stage / ENTRY.lstrip("/"))
                    shutil.copy2(target_file(source, interpreter), stage / interpreter.lstrip("/"))
                    for name in ["libc.so.6", "libm.so.6", "libgcc_s.so.1"]:
                        shutil.copy2(target_file(source, f"/lib/{multiarch}/{name}"), stage / "runtime" / name)
                    if variant != "missing":
                        library = apps["arm64" if arch == "amd64" else "amd64"][0] if variant == "wrong" else app
                        shutil.copy2(library / "_build/ffi" / ("legacy.so" if variant == "legacy" else "current.so"),
                                     stage / "opt/sensor-report/lib/libsensorcal.so.1")
                    loader_digest = digest(stage / interpreter.lstrip("/"))
                    config = dict(schema_version=1, root="root", entries=[ENTRY], scope="compatibility",
                                  target=dict(id=target_id, **FACTS))
                    config_path = folder / "deployment.json"
                    write_json(config_path, config)
                    case_reports = []
                    for backend in binaries:
                        out = folder / backend
                        summary = check(config_path, out, backend, expected)
                        assert summary["target_id"] == target_id and len(summary["reports"]) == 1
                        report = json.loads((out / "report-000.json").read_text())
                        obj = next(item for item in report["objects"] if item["path"]["display"] == ENTRY)
                        assert obj["sha256"] == program_digest
                        if expected == 0:
                            edge = next(e for e in report["edges"] if e["needed"]["display"] == "libsensorcal.so.1")
                            assert edge["selected"]["display"] == "/opt/sensor-report/lib/libsensorcal.so.1" and edge["trace"]
                        if label in ["missing-library", "wrong-architecture"]:
                            assert any(f["code"] == "MLC002" for f in report["findings"])
                        if label == "old-library":
                            assert any(f["code"] == "MLC004" and f.get("version", {}).get("display") == "SENSOR_2.0"
                                       for f in report["findings"])
                        case_reports.append(report)
                    assert case_reports[0] == case_reports[1], f"{arch}/{suite}/{label} backend mismatch"
                    reports[arch, suite, label] = case_reports[0]
                    actual = run_application(stage, arch, interpreter, "19500,22000,24500")
                    if expected == 0:
                        assert actual.returncode == 0 and json.loads(actual.stdout) == EXPECTED, actual.stderr
                    else:
                        assert actual.returncode != 0 and "libsensorcal.so.1" in actual.stderr, actual.stderr
                        if label == "old-library":
                            assert "SENSOR_2.0" in actual.stderr
                    cases.append(dict(case=label, suite=suite, architecture=arch, target_id=target_id,
                        execution_mode="qemu-user" if arch == "arm64" else "native",
                        analyzer_exit=expected, loader_exit=actual.returncode, application_output=actual.stdout.strip(),
                        loader_error=actual.stderr.strip(), program_sha256=program_digest, loader_sha256=loader_digest))
                    print(f"{arch}/{suite}/{label}: static {expected}, loader {actual.returncode}", flush=True)

                # Independently assemble the previous raw-profile format; presets
                # must not alter reports, capture identity, or search semantics.
                raw = dict(schema_version=1, root=str(group / "good/root"), entries=[ENTRY], scope="compatibility",
                    profile=dict(rule_revision="glibc-2.35-controlled-v2" if suite == "jammy" else "ubuntu-noble-2.39-0ubuntu8-v1",
                        loader_family="glibc", machine=machine, loader_path=interpreter,
                        loader_sha256=loader_digest, **FACTS))
                raw_path = group / "raw.json"
                write_json(raw_path, raw)
                wrong = json.loads((group / "good/deployment.json").read_text())
                wrong["root"] = raw["root"]
                wrong["target"]["id"] = f"ubuntu-{'noble' if suite == 'jammy' else 'jammy'}-{arch}"
                wrong_path = group / "wrong-target.json"
                write_json(wrong_path, wrong)
                for backend in binaries:
                    out = group / ("raw-" + backend)
                    check(raw_path, out, backend, 0)
                    assert json.loads((out / "report-000.json").read_text()) == reports[arch, suite, "good"]
                    assert (out / "snapshot/manifest.json").read_bytes() == (group / "good" / backend / "snapshot/manifest.json").read_bytes()
                    parity_checks += 1
                    check(wrong_path, group / ("wrong-target-" + backend), backend, 3)

                entries = group / "entries.json"
                write_json(entries, [ENTRY])
                comparisons = []
                for backend, command in commands.items():
                    for before, after, expected, classification in [("good", "old-library", 1, "introduced"), ("old-library", "fixed", 0, "resolved")]:
                        result = invoke(command + ["diff", "--before", group / before / backend / "snapshot", "--after",
                            group / after / backend / "snapshot", "--entries", entries, "--format", "json"], expected)
                        diff = json.loads(result.stdout)
                        assert not diff["entries"][0]["application_changed"]
                        assert any(c["classification"] == classification for c in diff["entries"][0]["changes"])
                        write_json(group / f"diff-{before}-{after}-{backend}.json", diff)
                        comparisons.append(diff)
                        diff_checks += 1
                    finding = next(f for f in reports[arch, suite, "old-library"]["findings"] if f["code"] == "MLC004")
                    result = invoke(command + ["explain", "--report", group / "old-library" / backend / "report-000.json",
                                              "--finding", finding["id"]], 0)
                    assert json.loads(result.stdout) == finding
                    explain_checks += 1
                assert comparisons[0] == comparisons[2] and comparisons[1] == comparisons[3]

                # Execute business checks on both architectures. ARM execution
                # uses QEMU and is distinct from the host MoonBit unit tests.
                for argument, expected, output in [("bad-input", 2, None), ("100001", 2, None),
                        ("-50000,100000", 0, dict(samples=2, min_milli_c=-49750, max_milli_c=100250, mean_milli_c=25250)),
                        (",".join(["100000"] * 1000), 0, dict(samples=1000, min_milli_c=100250, max_milli_c=100250, mean_milli_c=100250))]:
                    actual = run_application(group / "good/root", arch, interpreter, argument)
                    assert actual.returncode == expected, actual.stderr
                    if output is not None:
                        assert json.loads(actual.stdout) == output
                    business.append(dict(architecture=arch, suite=suite, input_samples=len(argument.split(",")),
                                         exit_code=actual.returncode, output=output))

        base = json.loads((work / "amd64/jammy/raw.json").read_text())
        for label, mutate, expected in [
            ("unverified-profile", lambda c: c["profile"].update(rule_revision="unverified-target"), 2),
            ("wrong-loader", lambda c: c["profile"].update(loader_sha256="0" * 64), 3),
            ("mixed-input-error", lambda c: c.update(entries=[ENTRY, "/not-a-program"]), 3),
        ]:
            config = copy.deepcopy(base)
            mutate(config)
            config_path = work / (label + ".json")
            write_json(config_path, config)
            for backend in binaries:
                summary = check(config_path, work / (label + "-" + backend), backend, expected)
                if label == "mixed-input-error":
                    assert [r["exit_code"] for r in summary["reports"]] == [0, 3]

        preset = dict(base)
        preset.pop("profile")
        preset["target"] = dict(id="ubuntu-jammy-amd64", **FACTS)
        invalid = [
            ("missing-fact", base, lambda c: c["profile"].pop("library_path")),
            ("unknown-field", base, lambda c: c["profile"].update(library_paths=["/runtime"])),
            ("null-token", base, lambda c: c["profile"].update(lib_token=None)),
            ("boolean-machine", base, lambda c: c["profile"].update(machine=True)),
            ("relative-entry", base, lambda c: c.update(entries=["app"])),
            ("duplicate-entry", base, lambda c: c.update(entries=[ENTRY, ENTRY])),
            ("unknown-target", preset, lambda c: c["target"].update(id="ubuntu-latest-arm64")),
            ("preset-missing-fact", preset, lambda c: c["target"].pop("library_path")),
            ("preset-override", preset, lambda c: c["target"].update(machine=183)),
            ("ambiguous-profile", preset, lambda c: c.update(profile=base["profile"])),
            ("no-profile", preset, lambda c: c.pop("target")),
        ]
        for label, original, mutate in invalid:
            config = copy.deepcopy(original)
            mutate(config)
            config_path = work / (label + ".json")
            write_json(config_path, config)
            check(config_path, work / label, "native", 3, no_output=True)
        duplicate = work / "duplicate-key.json"
        duplicate.write_text('{"schema_version":1,"schema_version":1}', encoding="utf-8")
        good = work / "amd64/jammy/good"
        for config_path, out in [(duplicate, work / "duplicate-key"),
                                 (good / "deployment.json", good / "native"),
                                 (good / "deployment.json", good / "root/nested-output")]:
            check(config_path, out, "native", 3)
        assert json.loads((good / "native/summary.json").read_text())["status"] == "pass_static"
        result = invoke([sys.executable, ROOT / "tools/check_deployment.py", "--not-an-option"], 3)
        assert json.loads(result.stdout)["status"] == "input_error"
        gate_checks += 1

    record = dict(application="sensor_report", application_dependency_on_analyzer=False, builds=builds,
        qemu=dict(version=invoke([QEMU, "--version"], 0).stdout.splitlines()[0], sha256=digest(QEMU),
                  source_recipe="tools/oracle/bootstrap_reference.py", physical_arm_hardware=False),
        target_catalog_sha256=digest(CATALOG), work=str(work), cases=cases, gate_checks=gate_checks,
        diff_checks=diff_checks, explain_checks=explain_checks, preset_parity_checks=parity_checks,
        business_checks=business)
    output = ROOT / "artifacts/deployment"
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "result.json", record)
    print(f"Deployment integration: {gate_checks} gates, {len(cases)} loader cases, {diff_checks} diffs, "
          f"{explain_checks} explanations, {parity_checks} preset comparisons, {len(business)} business checks; {work}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", required=True, type=Path)
    parser.add_argument("--js", required=True, type=Path)
    args = parser.parse_args()
    verify(args.native, args.js)
