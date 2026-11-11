"""Exercise preflight, isolated targets, verdict aggregation and hostile matrix evidence."""
from pathlib import Path
import argparse
import copy
import hashlib
import json
import subprocess
import tempfile
import shutil
from check_deployment import write_json
from check_matrix import matrix
from preflight_deployment import preflight
from verify_reports import Page, HOSTILE

ROOT = Path(__file__).resolve().parents[1]


def verify(native, js):
    source = Path(json.loads((ROOT / "artifacts/deployment/result.json").read_text())["work"])
    work = Path(tempfile.mkdtemp(prefix="matrix-", dir=ROOT / "artifacts"))
    commands = [[str(native.resolve())], ["node", str(js.resolve())]]
    checks = 0
    for backend, command in zip(["native", "js"], commands):
        cfgs = []
        for index, label in enumerate(["good", "missing-library", "old-library", "fixed"]):
            original = source / "amd64/jammy" / label / "deployment.json"
            config = json.loads(original.read_text())
            config["root"] = str((original.parent / config["root"]).resolve())
            path = work / f"{backend}-{label}.json"
            write_json(path, config)
            expected = [0, 1, 0, 0][index]  # dependency preflight cannot establish symbol compatibility
            result = preflight(path, command)
            assert result["exit_code"] == expected, result
            assert result["scope"] == "dependencies"
            checks += 1
            cfgs.append(dict(id=label, config=str(path)))
        original = json.loads(Path(cfgs[0]["config"]).read_text())
        missing = copy.deepcopy(original)
        del missing["target"]["preload"]
        del missing["target"]["audit"]
        path = work / f"{backend}-missing-facts.json"
        write_json(path, missing)
        result = preflight(path, command)
        assert result["exit_code"] == 3 and len(result["missing_facts"]) == 2
        checks += 1
        cfgs.append(dict(id=HOSTILE, config=str(path)))
        multi = copy.deepcopy(original)
        stage = work / (backend + "-multi-root")
        shutil.copytree(original["root"], stage, symlinks=True)
        (stage / "opt/alternate-app").symlink_to(multi["entries"][0])
        multi["root"] = str(stage)
        multi["entries"].append("/opt/alternate-app")
        multi_path = work / (backend + "-multi.json")
        write_json(multi_path, multi)
        cfgs.append(dict(id="multiple-applications", config=str(multi_path)))
        cfg = work / f"{backend}-matrix.json"
        write_json(cfg, dict(schema_version=1, targets=cfgs))
        result = matrix(cfg, work / backend, command)
        assert result["exit_code"] == 3 and result["check_count"] == 6
        assert [c["status"] for c in result["cells"]] == ["pass_static", "fail", "fail", "pass_static", "input_error", "pass_static", "pass_static"]
        assert result["different_program_groups"] == 0
        Page((work / backend / "index.html").read_text())
        checks += 1
    saved = json.loads((work / "native/matrix.json").read_text())
    # Every aggregate outcome, absent/duplicate/misbound evidence and unknown analysis.
    cases = []
    for indexes, code in [([0], 0), ([1], 1), ([0, 4], 3)]:
        cases.append((dict(schema_version=1, kind="deployment_matrix", targets=[saved["targets"][i] for i in indexes]), code))
    unknown = copy.deepcopy(saved["targets"][0])
    original = json.loads(Path(cfgs[0]["config"]).read_text())
    from check_deployment import expand_target, run
    original["profile"] = expand_target(original.pop("target"))
    original["profile"]["rule_revision"] = "unverified"
    cfg = work / "unknown.json"
    write_json(cfg, original)
    assert preflight(cfg, commands[0])["exit_code"] == 2
    run(cfg, work / "unknown", commands[0])
    unknown["reports"] = [json.loads((work / "unknown/report-000.json").read_text())]
    cases.append((dict(schema_version=1, kind="deployment_matrix", targets=[unknown]), 2))
    for change in [lambda d: d["targets"].append(copy.deepcopy(d["targets"][0])),
                   lambda d: d["targets"][0].update(reports=[]),
                   lambda d: d["targets"][0].update(entries=["/wrong"]),
                   lambda d: d.update(schema_version=True),
                   lambda d: d["targets"][0]["reports"][0].update(status="fail")]:
        value = copy.deepcopy(cases[0][0]); change(value); cases.append((value, 3))
    for i, (value, code) in enumerate(cases):
        path = work / f"case-{i}.json"; write_json(path, value)
        outputs = []
        for command in commands:
            result = subprocess.run(command + ["matrix-report", "--input", str(path), "--format", "summary"], capture_output=True, text=True)
            assert result.returncode == code and not result.stderr, result
            outputs.append(json.loads(result.stdout)); checks += 1
        assert outputs[0] == outputs[1]
    # Same application name and architecture with genuinely different program bytes.
    varied = copy.deepcopy(cases[0][0]); other = copy.deepcopy(varied["targets"][0]); other["id"] = "other"
    other["reports"][0]["objects"][0]["sha256"] = "a" * 64
    varied["targets"].append(other)
    path = work / "different.json"; write_json(path, varied)
    r = subprocess.run(commands[0] + ["matrix-report", "--input", str(path), "--format", "summary"], capture_output=True, text=True)
    assert r.returncode == 0 and json.loads(r.stdout)["different_program_groups"] == 1
    checks += 1
    # Output overlap/reuse must not mutate an existing root or completed result.
    before = hashlib.sha256((work / "native/summary.json").read_bytes()).hexdigest()
    for out in [work / "native", Path(original["root"]) / "nested"]:
        try: matrix(work / "native-matrix.json", out, commands[0])
        except (OSError, ValueError): pass
        else: raise AssertionError("unsafe output accepted")
        checks += 1
    assert hashlib.sha256((work / "native/summary.json").read_bytes()).hexdigest() == before
    write_json(ROOT / "artifacts/matrix/result.json", dict(checks=checks, work=str(work), backends=["native", "js"]))
    print(f"Preflight/matrix: {checks} checks passed; {work}")


if __name__ == "__main__":
    p = argparse.ArgumentParser(); p.add_argument("--native", type=Path, required=True); p.add_argument("--js", type=Path, required=True)
    a = p.parse_args(); (ROOT / "artifacts/matrix").mkdir(parents=True, exist_ok=True); verify(a.native, a.js)
