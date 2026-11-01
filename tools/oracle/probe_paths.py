"""Check the non-lexical path cases against Linux filesystem operations."""
from pathlib import Path
import errno
import json
import os
import tempfile

ROOT = Path(__file__).resolve().parents[2]

def main():
    parent = ROOT / "fixtures/generated"
    parent.mkdir(parents=True, exist_ok=True)
    # WSL's /mnt/d inherits NTFS case behavior; the reference must run on the
    # Linux filesystem, not the Windows-mounted checkout.
    root = Path(tempfile.mkdtemp(prefix="moonloadcheck-paths-"))
    (root / "usr/lib").mkdir(parents=True)
    (root / "usr/marker").write_bytes(b"usr-marker")
    (root / "marker").write_bytes(b"root-marker")
    os.symlink("usr/lib", root / "lib")
    os.symlink("missing", root / "broken")
    os.symlink("cycle-b", root / "cycle-a")
    os.symlink("cycle-a", root / "cycle-b")
    (root / "UPPER").write_bytes(b"upper")
    (root / "upper").write_bytes(b"lower")
    raw_name = os.fsencode(root) + b"/\xff"
    with open(raw_name, "wb") as stream: stream.write(b"raw-name")
    results = {}
    assert (root / "lib/../marker").read_bytes() == b"usr-marker"
    results["symlink-before-dotdot"] = True
    for name, error in [("marker/..", errno.ENOTDIR), ("marker/", errno.ENOTDIR), ("broken", errno.ENOENT), ("cycle-a", errno.ELOOP)]:
        try:
            os.stat(str(root) + "/" + name)
        except OSError as exc:
            assert exc.errno == error, (name, exc.errno)
        else:
            raise AssertionError("expected error: " + name)
        results[name] = error
    assert (root / "UPPER").read_bytes() != (root / "upper").read_bytes()
    with open(raw_name, "rb") as stream: assert stream.read() == b"raw-name"
    results["case-sensitive"] = True
    results["non-utf8"] = True
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(exist_ok=True)
    (artifacts / "path-oracle.json").write_text(json.dumps(results, indent=2) + "\n")
    print(str(len(results)) + " Linux path outcomes matched")

if __name__ == "__main__":
    main()
