"""Reproduce the internal, unmodified Apache-2.0 ELF parser dependency."""
from pathlib import Path
import hashlib
import io
import json
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
URL = "https://download.mooncakes.io/user/moonbit-community/elf/0.0.1.zip"
SHA256 = "82a9ff515aeb10bd38043c0951790a280b49334781ef7c266f18f9a6655f8fb1"
SOURCES = ["parse.mbt", "string_table.mbt", "gnu_symver.mbt", "segment.mbt", "endian.mbt", "compression.mbt", "section.mbt", "note.mbt", "dynamic.mbt", "file.mbt", "abi.mbt", "symbol.mbt", "relocation.mbt", "to_str.mbt", "hash.mbt", "elf_bytes.mbt", "error.mbt", "LICENSE"]

def main():
    with urllib.request.urlopen(URL, timeout=45) as response:
        content = response.read()
    if hashlib.sha256(content).hexdigest() != SHA256:
        raise ValueError("upstream archive hash mismatch")
    archive = zipfile.ZipFile(io.BytesIO(content))
    destination = ROOT / "internal" / "elf_vendor"
    destination.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for name in SOURCES:
        data = archive.read(name)
        path = destination / name
        if path.exists() and path.read_bytes() != data:
            raise ValueError("refusing to overwrite modified upstream source: " + name)
        path.write_bytes(data)
        hashes[name] = hashlib.sha256(data).hexdigest()
    lock = {"module": "moonbit-community/elf", "version": "0.0.1", "archive": URL, "sha256": SHA256, "license": "Apache-2.0", "source_changes": "none", "configuration_changes": "package renamed to internal/elf_vendor; test-only dependency omitted; upstream deprecation warnings scoped to this package", "files": hashes}
    (destination / "UPSTREAM.json").write_text(json.dumps(lock, indent=2) + "\n")
    print("Verified and preserved", len(SOURCES) - 1, "upstream source files; license retained")

if __name__ == "__main__":
    main()
