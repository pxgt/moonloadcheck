"""Create a bounded, non-executed metadata stress input for the real graph cap."""
from pathlib import Path
import hashlib
import json
import shutil
import struct
import subprocess
from build_roots import ROOT


def build():
    source = ROOT / "fixtures/generated/paths/amd64/jammy/direct-missing"
    destination = ROOT / "fixtures/generated/limits/dependency-steps/snapshot"
    shutil.copytree(source / "snapshot", destination, dirs_exist_ok=True)
    data = bytearray((source / "root/app").read_bytes())
    phoff = struct.unpack_from("<Q", data, 32)[0]
    width, count = struct.unpack_from("<HH", data, 54)
    load_end, dynamic, reusable = 0, None, None
    for i in range(count):
        pos = phoff + i * width
        kind, _, offset, address, _, size, memsize, _ = struct.unpack_from("<IIQQQQQQ", data, pos)
        if kind == 1:
            load_end = max(load_end, address + memsize)
        elif kind == 2:
            dynamic = (pos, offset, size)
        elif kind == 4:
            reusable = pos
    assert dynamic is not None and reusable is not None
    pos, offset, size = dynamic
    entries = []
    for p in range(offset, offset + size, 16):
        pair = struct.unpack_from("<QQ", data, p)
        if pair[0] == 0:
            break
        entries.append(pair)
    needed = [p for p in entries if p[0] == 1]
    assert len(needed) == 2
    # Keep the first missing dependency, then repeatedly reuse already loaded libc.
    # This reaches the production 16,384-step cap without huge files or a lowered cap.
    table = b"".join(struct.pack("<QQ", *p) for p in [needed[0]] + [needed[1]] * 17000 + [p for p in entries if p[0] != 1] + [(0, 0)])
    fileoff = (len(data) + 4095) & ~4095
    address = (load_end + 4095) & ~4095
    data += b"\0" * (fileoff - len(data)) + table
    struct.pack_into("<IIQQQQQQ", data, reusable, 1, 4, fileoff, address, address, len(table), len(table), 4096)
    struct.pack_into("<IIQQQQQQ", data, pos, 2, 4, fileoff, address, address, len(table), len(table), 8)
    # Section headers describe the original table. Strip them so readelf, like
    # the production reader, must use the relocated PT_DYNAMIC metadata.
    struct.pack_into("<Q", data, 40, 0)
    struct.pack_into("<HHH", data, 58, 0, 0, 0)
    digest = hashlib.sha256(data).hexdigest()
    (destination / "blobs" / digest).write_bytes(data)
    manifest = json.loads((destination / "manifest.json").read_text())
    app = next(e for e in manifest["entries"] if e["path_hex"] == b"/app".hex())
    app["sha256"] = digest
    (destination / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    readelf = subprocess.run(["readelf", "-dW", str(destination / "blobs" / digest)], check=True, capture_output=True, text=True)
    assert readelf.stdout.count("(NEEDED)") == 17001
    (destination.parent / "oracle.json").write_text(json.dumps(dict(executed=False, needed_count=17001,
        first_needed="libapi.so.1", repeated_needed="libc.so.6", program_sha256=digest, byte_length=len(data)), indent=2) + "\n")
    print("Graph cap input: 17,001 DT_NEEDED records; verified by readelf, never executed")


if __name__ == "__main__":
    build()
