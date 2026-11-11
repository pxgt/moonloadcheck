"""Compile a standalone public-API consumer using a temporary Moon workspace.

This is a local source dependency check, not evidence of a Mooncakes release.
"""
from pathlib import Path
import json
import argparse
import subprocess
import tempfile
from verify_archive import metadata

ROOT = Path(__file__).resolve().parents[1]


def verify(backend="native"):
    target = Path(tempfile.mkdtemp(prefix="moonloadcheck-consumer-"))
    version = metadata((ROOT / "moon.mod").read_text())["version"]
    (target / "moon.mod").write_text('name = "validation/consumer"\nimport { "Xpeng/moonloadcheck@' + version + '", }\n')
    (target / "moon.pkg").write_text('import { "Xpeng/moonloadcheck", } for "test"\n')
    (target / "consumer_test.mbt").write_text('''///|
test "external facade never needs internal parser types" {
  let files = @moonloadcheck.FileSystem::new([
    (b"/app", @moonloadcheck.Entry::File("application")),
    (b"/alias", @moonloadcheck.Entry::Symlink(b"/app")),
  ])
  assert_eq(files.resolve(b"/alias").path, b"/app")
  try @moonloadcheck.read_linkage(b"bad ELF") catch {
    @moonloadcheck.ElfError::Malformed(_) => ()
    _ => fail("incorrect public error")
  } noraise { _ => fail("bad ELF accepted") }
  try @moonloadcheck.load_snapshot(" ".repeat(4194305), _ => b"") catch {
    @moonloadcheck.SnapshotError::SnapshotLimit(message) =>
      assert_true(message.contains("4194304"))
    _ => fail("snapshot limit error is not exposed by the facade")
  } noraise { _ => fail("oversized manifest accepted") }
}
''')
    # Workspace resolution uses the local member without publishing or editing it.
    (target / "moon.work").write_text("members = " + json.dumps([".", str(ROOT)]) + "\n")
    subprocess.run(["moon", "test", "--package", "validation/consumer", "--target", backend, "--deny-warn"], cwd=target, check=True)
    print("Standalone public consumer passed:", target)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=["native", "js", "js,native"], default="native")
    verify(parser.parse_args().target)
