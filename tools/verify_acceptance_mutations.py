"""Five planned fault classes, each killed by its dedicated native assertion."""
from pathlib import Path
import json
import shutil
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]

HOST_FALLBACK = '''self.filesystem.resolve(path, cwd~) catch {
    error => {
      let bytes = @host_fs.read_file_to_bytes(@utf8.decode_lossy(path[:])) catch { _ => raise error }
      let id = "host-fallback:" + @hex.encode(path[:])
      self.contents[id] = bytes
      self.digests[id] = sha256(bytes)
      { path, entry: File(id), symlinks: 0 }
    }
  }'''

EXPORT_HELPER = '''
///|
fn mutation_exports(snapshot : @snapshot.Snapshot, report : Report) -> Array[Bytes] raise {
  let names = []
  for object in report.objects {
    let linkage = @elf.read_linkage(snapshot.content(object.file_id).unwrap())
    for symbol in linkage.symbols {
      if exported(symbol) && !names.contains(symbol.name) { names.push(symbol.name) }
    }
  }
  names
}
'''

EXPORT_RULE = '''let later = check_compatibility(after, entry)
    let previous_exports = mutation_exports(before, earlier)
    let current_exports = mutation_exports(after, later)
    let removed = previous_exports.filter(name => !current_exports.contains(name))
    if !removed.is_empty() && later.findings.is_empty() {
      issue(later, "MLC005", "fail", entry, Some(removed[0]), [], "Removed export assumed to break every consumer", "Restore export")
    }
    let later = finish(later)'''


def verify():
    target = Path(tempfile.mkdtemp(prefix="moonloadcheck-acceptance-mutations-"))
    paths = subprocess.check_output(["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"], cwd=ROOT).decode().split("\0")
    for relative in paths:
        if relative:
            path = target / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, path)
    (target / "fixtures/generated").symlink_to(ROOT / "fixtures/generated", target_is_directory=True)
    decoy = json.loads((ROOT / "fixtures/generated/paths/amd64/jammy/host-decoy/snapshot/manifest.json").read_text())
    host_directory = Path(bytes.fromhex(decoy["profile"]["library_path_hex"][0]).decode())
    assert (host_directory / "libapi.so.1").is_file(), "host-side decoy must actually exist"
    mutations = [
        ("inherit RUNPATH", "0", [("analysis/dependencies.mbt",
            "if ancestor.object.runpath is None && ancestor.object.rpath is Some(rpath) {",
            "if ancestor.object.runpath is Some(rpath) {")]),
        ("ignore GNU versions", "1", [("analysis/linkage.mbt", "    for need in linkage.version_needs {", "    for need in linkage.version_needs.filter(_ => false) {"),
            ("analysis/linkage.mbt", "let desired = versions[consumer].get(symbol.version_index)", "let desired : Version? = None")]),
        ("read missing target library from host", "2", [("snapshot/manifest.mbt", "self.filesystem.resolve(path, cwd~)", HOST_FALLBACK),
            ("snapshot/moon.pkg", "import {", 'import {\n  "moonbitlang/x/fs" @host_fs,')]),
        ("convert unknown to pass", "3", [("analysis/report.mbt", '1 => "inconclusive"', '1 => "pass_static"')]),
        ("compare only removed exports", "4", [("analysis/impact.mbt", "let later = check_compatibility(after, entry)", EXPORT_RULE),
            ("analysis/impact.mbt", None, EXPORT_HELPER)]),
    ]
    original = {relative: (target / relative).read_text() for _, _, edits in mutations for relative, _, _ in edits}
    command = ["moon", "test", "analysis/acceptance_test.mbt", "--target", "native"]
    control = subprocess.run(command, cwd=target, capture_output=True, text=True, timeout=180)
    assert control.returncode == 0 and "passed: 7" in control.stdout + control.stderr, control.stdout + control.stderr
    evidence = []
    for label, index, edits in mutations:
        try:
            for relative, before, after in edits:
                path = target / relative
                text = path.read_text()
                if before is not None:
                    assert text.count(before) == 1, (label, "mutation anchor changed")
                    text = text.replace(before, after)
                else:
                    text += after
                path.write_text(text)
            result = subprocess.run(command + ["--index", index], cwd=target, capture_output=True, text=True, timeout=180)
            output = result.stdout + result.stderr
            assert result.returncode != 0 and "failed: 1" in output, (label, output)
            evidence.append(dict(fault=label, detected_by_assertion=True, exit_code=result.returncode))
            print("Detected acceptance mutation:", label, flush=True)
        finally:
            for relative, text in original.items():
                (target / relative).write_text(text)
    (ROOT / "artifacts").mkdir(exist_ok=True)
    (ROOT / "artifacts/acceptance-mutations.json").write_text(json.dumps(evidence, indent=2) + "\n")


if __name__ == "__main__":
    verify()
