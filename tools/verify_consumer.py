"""Compile a standalone public-API consumer using a temporary Moon workspace.

This is a local source dependency check, not evidence of a Mooncakes release.
"""
from pathlib import Path
import json
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def verify():
    target = Path(tempfile.mkdtemp(prefix="moonloadcheck-consumer-"))
    (target / "moon.mod").write_text('name = "validation/consumer"\nimport { "Xpeng/moonloadcheck@0.1.0", }\n')
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
}
''')
    # Workspace resolution uses the local member without publishing or editing it.
    (target / "moon.work").write_text("members = " + json.dumps([".", str(ROOT)]) + "\n")
    subprocess.run(["moon", "test", "--package", "validation/consumer", "--target", "native", "--deny-warn"], cwd=target, check=True)
    print("Standalone public consumer passed:", target)


if __name__ == "__main__":
    verify()
