"""Analyze and execute this project's own MoonBit native/FFI CLI in both roots."""
from pathlib import Path
import argparse
import hashlib
import json
import os
import shutil
import subprocess
from build_roots import ROOT, target_file, loader_command, capture


def verify(native, js=None):
    relocations = subprocess.run(["readelf", "-rW", str(native)], check=True, capture_output=True, text=True).stdout
    copy_symbols = {line.split()[4].split("@")[0] for line in relocations.splitlines() if "R_X86_64_COPY" in line}
    assert copy_symbols == {"stdout", "stderr", "__environ"}, copy_symbols
    commands = [[str(native.resolve())]]
    if js:
        commands.insert(0, ["node", str(js.resolve())])
    outcomes = []
    interpreter = "/lib64/ld-linux-x86-64.so.2"
    for suite in ["jammy", "noble"]:
        folder = ROOT / "fixtures/generated/self-host" / suite
        root = folder / "root"
        source = ROOT / ".tools/corpus/roots" / suite / "amd64"
        for path in [root / "runtime", root / "lib64", root / "opt"]:
            path.mkdir(parents=True, exist_ok=True)
        shutil.copy2(native, root / "opt/moonloadcheck")
        shutil.copy2(target_file(source, interpreter), root / interpreter.lstrip("/"))
        for library in ["libc.so.6", "libm.so.6", "libgcc_s.so.1"]:
            shutil.copy2(target_file(source, "/lib/x86_64-linux-gnu/" + library), root / "runtime" / library)
        profile = dict(rule_revision="glibc-2.35-controlled-v2" if suite == "jammy" else "ubuntu-noble-2.39-0ubuntu8-v1",
            loader_family="glibc", machine=62, loader_path_hex=interpreter.encode().hex(),
            loader_sha256=hashlib.sha256((root / interpreter.lstrip("/")).read_bytes()).hexdigest(), cwd_hex=b"/".hex(),
            default_dirs_hex=[], library_path_hex=[b"/runtime".hex()], cache_mode="disabled", hwcaps_policy="none",
            secure_execution=False, preload=[], audit=[])
        capture(root, profile, folder / "snapshot")
        actual = subprocess.run(loader_command(root, "amd64", interpreter, ["/runtime"]) + ["/opt/moonloadcheck", "invalid-command"],
            capture_output=True, text=True, timeout=30, env={"PATH": os.environ["PATH"], "LC_ALL": "C", "LD_BIND_NOW": "1"})
        assert actual.returncode == 3 and json.loads(actual.stdout)["status"] == "input_error", actual.stderr
        reports = []
        for command in commands:
            result = subprocess.run(command + ["check", "--snapshot", str(folder / "snapshot"), "--entry", "/opt/moonloadcheck",
                "--scope", "compatibility", "--format", "json"], capture_output=True, text=True, timeout=60)
            report = json.loads(result.stdout)
            if result.returncode != 0 or report["status"] != "pass_static":
                raise AssertionError((suite, report.get("findings", report)))
            copies = [c for c in report["symbol_checks"] if c["lookup_policy"] == "copy-source-excluding-executable"]
            assert {c["symbol"]["display"] for c in copies} == copy_symbols
            assert all(c["provider"]["display"] == "/runtime/libc.so.6" and c["copy_source_size"] == c["copy_destination_size"] == "8" for c in copies)
            # stdout/stderr also have ordinary references in the same executable.
            # They bind to the executable's copy, not the COPY initialization source.
            for symbol in ["stdout", "stderr"]:
                assert any(c["symbol"]["display"] == symbol and c["consumer"]["display"] == "/opt/moonloadcheck"
                    and c["provider"]["display"] == "/opt/moonloadcheck" and c["lookup_policy"] == "startup-global-scope"
                    for c in report["symbol_checks"])
            reports.append(report)
        assert all(report == reports[0] for report in reports)
        outcomes.append(dict(suite=suite, architecture="amd64", loader_exit=actual.returncode, analysis_status=reports[0]["status"],
            copy_symbols=sorted(copy_symbols), program_sha256=hashlib.sha256(native.read_bytes()).hexdigest(), loader_sha256=profile["loader_sha256"]))
    (ROOT / "fixtures/generated/self-host/oracle.json").write_text(json.dumps(outcomes, indent=2) + "\n")
    print(f"Self-host: {len(outcomes)} normal CLI executions and static passes with separate COPY/ordinary bindings")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--native", type=Path, required=True)
    parser.add_argument("--js", type=Path)
    args = parser.parse_args()
    verify(args.native, args.js)
