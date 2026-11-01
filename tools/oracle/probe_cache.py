"""M0 cache-layout validation against read-only ldconfig output.

Format reference: glibc release/2.35/master, sysdeps/generic/dl-cache.h.
This is a reference experiment; production candidate selection belongs in MoonBit.
"""
from pathlib import Path
import hashlib
import json
import re
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[2]

def probe(path):
    data = path.read_bytes()
    base = 0
    if data[:11] == b"ld.so-1.7.0" and len(data) >= 16:
        old_count = struct.unpack_from("<I", data, 12)[0]
        base = (16 + old_count * 12 + 7) & ~7
    magic = b"glibc-ld.so.cache1.1"
    if base + 48 > len(data) or data[base:base + len(magic)] != magic:
        raise ValueError("M0 needs a new-format cache, optionally inside a compat cache")
    if data[base + 28] & 3 not in (0, 2):
        raise ValueError("cache endian flags are not supported")
    count, string_bytes = struct.unpack_from("<II", data, base + 20)
    strings_start = base + 48 + count * 24
    strings_end = strings_start + string_bytes
    if count > 1000000 or strings_end > len(data):
        raise ValueError("invalid cache table bounds")
    def string_at(offset):
        offset += base
        if not strings_start <= offset < strings_end:
            raise ValueError("string offset outside cache string table")
        end = data.find(b"\0", offset, strings_end)
        if end < 0:
            raise ValueError("unterminated cache string")
        return data[offset:end].decode("utf-8")
    entries = []
    for index in range(count):
        flags, key, value, osversion, hwcap = struct.unpack_from("<iIIIQ", data, base + 48 + index * 24)
        entries.append({"name": string_at(key), "path": string_at(value), "flags": flags, "osversion": osversion, "hwcap": hwcap, "order": index})
    reference = subprocess.check_output(["/sbin/ldconfig", "-p", "-C", str(path)], text=True)
    printed = re.findall(r"^\s*(\S+)\s+\([^)]*\)\s+=>\s+(.+)$", reference, re.M)
    observed = [(entry["name"], entry["path"]) for entry in entries]
    if sorted(printed) != sorted(observed):
        raise AssertionError("cache records differ from ldconfig")
    extension_offset = struct.unpack_from("<I", data, base + 32)[0]
    if extension_offset and (extension_offset % 4 or extension_offset + 8 > len(data)):
        raise ValueError("invalid extension directory offset")
    summary = {
        "cache_sha256": hashlib.sha256(data).hexdigest(),
        "format": "glibc-ld.so.cache1.1",
        "compat_header": base != 0,
        "entries": count,
        "ldconfig_records_match": True,
        "entry_flags": sorted({entry["flags"] for entry in entries}),
        "hwcap_entries": sum(entry["hwcap"] != 0 for entry in entries),
        "extension_directory_present": extension_offset != 0,
        "scope": "metadata decoding only; hwcaps ranking and loader choice are not verified",
    }
    artifacts = ROOT / "artifacts"
    artifacts.mkdir(exist_ok=True)
    (artifacts / "m0-cache-summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps(summary, indent=2))

if __name__ == "__main__":
    probe(Path("/etc/ld.so.cache"))
