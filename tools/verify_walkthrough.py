"""Execute README's marked Bash blocks verbatim, then check their user-visible results."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shlex
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def verify(require_clean=False):
    if require_clean:
        for path in [".tools", ".mooncakes", "_build", "fixtures/generated"]:
            if (ROOT / path).exists():
                raise ValueError("fresh walkthrough requires an absent " + path)
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    blocks = re.findall(r"<!-- walkthrough:([a-z0-9-]+) exit=([0-3]) -->\s+```sh\n(.*?)```", readme, re.S)
    names = [name for name, _, _ in blocks]
    assert names == ["setup", "u1-failure", "u1-fixed", "u2-new", "u2-old",
                     "u3-introduced", "u3-resolved", "save-report", "explain", "consumer"], names
    output = ROOT / "artifacts/walkthrough"
    output.mkdir(parents=True, exist_ok=True)
    script = ["set -eu", "unset LD_LIBRARY_PATH LD_PRELOAD LD_AUDIT LD_BIND_NOW"]
    for name, expected, command in blocks:
        script.append(f"printf '%s' '{name}' > " + shlex.quote(str(output / "current-step")))
        # Zero-exit setup/compound blocks use errexit. Expected-failure blocks
        # contain exactly one CLI command, whose status is checked explicitly.
        if expected != "0":
            assert len(command.strip().splitlines()) == 1
            script.append("set +e")
        script.extend(["{", command.rstrip(), "} > " + shlex.quote(str(output / (name + ".out")))
                       + " 2> " + shlex.quote(str(output / (name + ".err"))),
                       "observed=$?", "set -e", f'test "$observed" -eq {expected}',
                       f"printf '%s\\n' 'README {name}: exit {expected} verified'"])
    script_path = output / "commands.sh"
    script_path.write_bytes(("\n".join(script) + "\n").encode())
    result = subprocess.run(["bash", str(script_path)], cwd=ROOT, timeout=1200)
    if result.returncode:
        name = (output / "current-step").read_text()
        assert name in names
        for suffix in ["out", "err"]:
            log = output / (name + "." + suffix)
            if log.exists():
                print(name, suffix, log.read_text(errors="replace")[-4000:])
        raise RuntimeError("README command failed; inspect artifacts/walkthrough")

    def report(name):
        assert (output / (name + ".err")).read_text() == ""
        return json.loads((output / (name + ".out")).read_text())
    bad, fixed = report("u1-failure"), report("u1-fixed")
    assert bad["status"] == "fail" and any(f["code"] == "MLC002" for f in bad["findings"])
    assert any(e["trace"] for e in bad["edges"])
    assert fixed["status"] == "pass_static"
    new, old = report("u2-new"), report("u2-old")
    assert new["status"] == "pass_static" and old["status"] == "fail"
    assert any(v["version"]["display"] == "DEMO_2" and v["status"] == "fail" for v in old["version_checks"])
    hashes = [next(o["sha256"] for o in r["objects"] if o["path"]["display"] == "/opt/demo/app") for r in [new, old]]
    assert hashes[0] == hashes[1], "U2 must retain the exact executable"
    for name, status, classification in [("u3-introduced", "fail", "introduced"), ("u3-resolved", "pass_static", "resolved")]:
        diff = report(name)
        assert diff["status"] == status
        changed = next(e for e in diff["entries"] if e["entry"]["display"] == "/opt/demo/app")
        stable = next(e for e in diff["entries"] if e["entry"]["display"] == "/opt/demo/stable-app")
        assert len(changed["changes"]) == 1 and changed["changes"][0]["classification"] == classification
        assert not changed["application_changed"] and stable["after"]["status"] == "pass_static"
        assert stable["changes"] == []
    saved = json.loads((output / "report.json").read_text())
    assert saved["status"] == "fail" and report("explain") == saved["findings"][0]
    record = dict(readme_sha256=hashlib.sha256(readme.encode()).hexdigest(), required_clean=require_clean,
                  steps=[dict(name=n, exit_code=int(c)) for n, c, _ in blocks], cli_checks=8)
    (output / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print("README walkthrough: 10 command blocks, 8 CLI outcomes and standalone consumer passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--require-clean", action="store_true")
    verify(parser.parse_args().require_clean)
