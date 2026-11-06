"""Non-executed range/overflow mutations and actual production-count boundaries."""
import hashlib
import json
import os
import struct
from build_roots import ROOT
from build_linkage_edges import layout

GENERATED = ROOT / "fixtures/generated/stress"


def put(source, offset, value, width=8):
    data = bytearray(source)
    data[offset:offset + width] = value.to_bytes(width, "little")
    return data


def headers(data):
    start = struct.unpack_from("<Q", data, 32)[0]
    width, count = struct.unpack_from("<HH", data, 54)
    return [start + i * width for i in range(count)]


def dynamic(source, key, value):
    data = bytearray(source)
    pos = next(p for p in headers(data) if struct.unpack_from("<I", data, p)[0] == 2)
    start, size = struct.unpack_from("<Q", data, pos + 8)[0], struct.unpack_from("<Q", data, pos + 32)[0]
    for p in range(start, start + size, 16):
        if struct.unpack_from("<Q", data, p)[0] == key:
            return put(data, p + 8, value)
    raise ValueError("missing dynamic tag")


def append_load(source, payload):
    data = bytearray(source)
    positions = headers(data)
    note = next(p for p in positions if struct.unpack_from("<I", data, p)[0] == 4)
    end = max(struct.unpack_from("<Q", data, p + 16)[0] + struct.unpack_from("<Q", data, p + 40)[0]
              for p in positions if struct.unpack_from("<I", data, p)[0] == 1)
    fileoff, address = (len(data) + 4095) & ~4095, (end + 4095) & ~4095
    data += bytes(fileoff - len(data)) + payload
    struct.pack_into("<IIQQQQQQ", data, note, 1, 4, fileoff, address, address, len(payload), len(payload), 4096)
    return data, fileoff, address


def build():
    rows = []
    for arch in ["amd64", "arm64"]:
        base = ROOT / "fixtures/generated/linkage-edges" / arch / "jammy/baseline-pie"
        source = (base / "root/app").read_bytes()
        positions = headers(source)
        load = next(p for p in positions if struct.unpack_from("<I", source, p)[0] == 1)
        note = next(p for p in positions if struct.unpack_from("<I", source, p)[0] == 4)
        dyn = next(p for p in positions if struct.unpack_from("<I", source, p)[0] == 2)
        tags, offset, symbols, _, hashpos, _, _, _ = layout(source)
        variants = [("control", source, 0)]
        for value, suffix in [(0x80000000, "int32"), (0xfffffffffffffff8, "uint64")]:
            variants += [("phoff-" + suffix, put(source, 32, value), 3),
                         ("load-offset-" + suffix, put(source, load + 8, value), 3),
                         ("load-size-" + suffix, put(put(source, load + 32, value), load + 40, value), 3)]
            for key, label in [(5, "strings"), (6, "symbols"), (4, "hash"), (7, "rela"), (0x6ffffffe, "verneed")]:
                variants.append((label + "-address-" + suffix, dynamic(source, key, value), 3))
            for key, label in [(10, "strings"), (8, "rela")]:
                variants.append((label + "-size-" + suffix, dynamic(source, key, value), 3))
        for size, label, code in [(7, "high-range-control", 0), (16, "virtual-memory-wrap", 3)]:
            data = bytearray(source)
            struct.pack_into("<IIQQQQQQ", data, note, 1, 4, 0, 0xfffffffffffffff8, 0xfffffffffffffff8, 0, size, 1)
            variants.append((label, data, code))
        variants += [("symbol-string-outside", put(source, symbols + 24, 0xffffffff, 4), 3),
                     ("sysv-count-limit", put(source, hashpos + 4, 100001, 4), 2),
                     ("verneed-count-limit", dynamic(source, 0x6fffffff, 32769), 2),
                     ("verneed-aux-wrap", put(source, offset(tags[0x6ffffffe]) + 8, 0xfffffff0, 4), 3),
                     ("relocation-symbol-outside", put(source, offset(tags[7]) + 8, (99999 << 32) | 1), 3)]
        for count in [4096, 4097]:
            data = bytearray(source)
            fileoff = (len(data) + 15) & ~15
            table = source[positions[0]:positions[-1] + 56] + bytes((count - len(positions)) * 56)
            data += bytes(fileoff - len(data)) + table
            struct.pack_into("<Q", data, 32, fileoff)
            struct.pack_into("<H", data, 56, count)
            variants.append(("program-headers-" + str(count), data, 0 if count == 4096 else 2))
        start, size = struct.unpack_from("<Q", source, dyn + 8)[0], struct.unpack_from("<Q", source, dyn + 32)[0]
        for count in [65536, 65537]:
            payload = source[start:start + size] + bytes(count * 16 - size)
            data, fileoff, address = append_load(source, payload)
            struct.pack_into("<IIQQQQQQ", data, dyn, 2, 4, fileoff, address, address, len(payload), len(payload), 8)
            variants.append(("dynamic-entries-" + str(count), data, 0 if count == 65536 else 2))
        for count in [500000, 500001]:
            data, _, address = append_load(source, bytes(count * 24))
            data = dynamic(dynamic(dynamic(data, 7, address), 8, count * 24), 2, 0)
            variants.append(("relocations-" + str(count), data, 0 if count == 500000 else 2))
        manifest = json.loads((base / "snapshot/manifest.json").read_text())
        for case, data, code in variants:
            folder = GENERATED / arch / case
            snapshot = folder / "snapshot"
            (snapshot / "blobs").mkdir(parents=True, exist_ok=True)
            for blob in (base / "snapshot/blobs").iterdir():
                if not (snapshot / "blobs" / blob.name).exists():
                    os.link(blob, snapshot / "blobs" / blob.name)
            digest = hashlib.sha256(data).hexdigest()
            (snapshot / "blobs" / digest).write_bytes(data)
            view = json.loads(json.dumps(manifest))
            next(e for e in view["entries"] if e["path_hex"] == b"/app".hex())["sha256"] = digest
            (snapshot / "manifest.json").write_text(json.dumps(view, indent=2) + "\n")
            rows.append(dict(architecture=arch, case=case, expected_code=code, executed=False,
                sha256=digest, byte_length=len(data)))
    (GENERATED / "oracle.json").write_text(json.dumps(rows, indent=2) + "\n")
    print(f"Stress: {len(rows)} non-executed range/count fixtures; largest {max(r['byte_length'] for r in rows)} bytes")


if __name__ == "__main__":
    build()
