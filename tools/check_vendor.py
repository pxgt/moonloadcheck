"""Verify that no local edit or formatter changed the preserved upstream source."""
from pathlib import Path
import hashlib
import json

root = Path(__file__).resolve().parents[1] / "internal/elf_vendor"
lock = json.loads((root / "UPSTREAM.json").read_text())
for name, digest in lock["files"].items():
    if hashlib.sha256((root / name).read_bytes()).hexdigest() != digest:
        raise SystemExit("upstream source changed: " + name)
print("all preserved upstream source hashes match")
