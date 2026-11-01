"""Prove COPY regression tests detect wrong rules in a disposable source copy."""
from pathlib import Path
import json
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def verify():
    target = Path(tempfile.mkdtemp(prefix="moonloadcheck-copy-mutations-"))
    paths = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")
    for relative in paths:
        if relative:
            destination = target / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, destination)
    (target / "fixtures/generated").symlink_to(ROOT / "fixtures/generated", target_is_directory=True)
    source = target / "analysis/linkage.mbt"
    original = source.read_text()
    mutations = [
        ("COPY wrongly binds executable", "if copy && provider == 0 {", "if false {", "0"),
        ("COPY ignores size mismatch", "size_mismatch = source.size != symbol.size", "size_mismatch = false", "1"),
    ]
    evidence = []
    command = ["moon", "test", "analysis/copy_test.mbt", "--target", "native"]
    control = subprocess.run(command, cwd=target, capture_output=True, text=True, timeout=180)
    assert control.returncode == 0 and "passed: 3" in control.stdout + control.stderr, control.stdout + control.stderr
    for label, before, after, index in mutations:
        assert original.count(before) == 1, "mutation anchor changed"
        source.write_text(original.replace(before, after))
        try:
            result = subprocess.run(command + ["--index", index], cwd=target, capture_output=True, text=True, timeout=180)
            output = result.stdout + result.stderr
            # A compiler error or missing fixture is not a successful mutation kill.
            assert result.returncode != 0 and "failed: 1" in output, (label, output)
            evidence.append(dict(mutation=label, detected=True, exit_code=result.returncode))
            print("Detected mutation:", label, flush=True)
        finally:
            source.write_text(original)
    (ROOT / "artifacts").mkdir(exist_ok=True)
    (ROOT / "artifacts/copy-mutations.json").write_text(json.dumps(evidence, indent=2) + "\n")


if __name__ == "__main__":
    verify()
