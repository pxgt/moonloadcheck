"""Relocate intact runtime tables to an exact PT_LOAD boundary, then truncate them.

These own-source metadata fixtures are never executed. Valid controls distinguish
table range checks from unrelated header/parser failures.
"""
from pathlib import Path
import hashlib
import json
import struct
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "oracle"))
from elf_mutations import tables

ROOT = Path(__file__).resolve().parents[2]


def place(source, tag, payload, disable=None):
    data = bytearray(source)
    phoff = struct.unpack_from("<Q", data, 32)[0]
    width, count = struct.unpack_from("<HH", data, 54)
    maximum, note, dynamic = 0, None, None
    for i in range(count):
        pos = phoff + i * width
        kind, _, fileoff, address, _, size, memory, _ = struct.unpack_from("<IIQQQQQQ", data, pos)
        if kind == 1:
            maximum = max(maximum, address + memory)
        elif kind == 2:
            dynamic = (fileoff, size)
        elif kind == 4:
            note = pos
    assert note is not None and dynamic is not None
    fileoff, address = (len(data) + 4095) & ~4095, (maximum + 4095) & ~4095
    data += bytes(fileoff - len(data)) + payload
    struct.pack_into("<IIQQQQQQ", data, note, 1, 4, fileoff, address, address, len(payload), len(payload), 4096)
    found = False
    for pos in range(dynamic[0], sum(dynamic), 16):
        key = struct.unpack_from("<Q", data, pos)[0]
        if key == 0:
            break
        if key == tag:
            struct.pack_into("<Q", data, pos + 8, address)
            found = True
        elif key == disable:
            struct.pack_into("<QQ", data, pos, 21, 0)  # DT_DEBUG is irrelevant to lookup.
    assert found
    # Do not leave a competing stale section-table view for reference readers.
    struct.pack_into("<Q", data, 40, 0)
    struct.pack_into("<HHH", data, 58, 0, 0, 0)
    return bytes(data)


def version_extent(data, tags, offset, definitions):
    tag, count_tag, header, aux_width = (0x6ffffffc, 0x6ffffffd, 20, 8) if definitions else (0x6ffffffe, 0x6fffffff, 16, 16)
    base = offset(tags[tag])
    relative, end, first_aux = 0, 0, None
    for _ in range(tags[count_tag]):
        pos = base + relative
        count = struct.unpack_from("<H", data, pos + (6 if definitions else 2))[0]
        aux = relative + struct.unpack_from("<I", data, pos + (12 if definitions else 8))[0]
        first_aux = aux if first_aux is None else first_aux
        end = max(end, relative + header)
        for _ in range(count):
            end = max(end, aux + aux_width)
            aux += struct.unpack_from("<I", data, base + aux + (4 if definitions else 12))[0]
        relative += struct.unpack_from("<I", data, pos + (16 if definitions else 12))[0]
    return tag, bytes(data[base:base + end]), [header - 1, first_aux + aux_width - 1, end - 1]


def build():
    generated = ROOT / "fixtures/generated/parser-edges"
    records = []
    for arch in ["x86_64", "aarch64"]:
        folder = generated / arch
        folder.mkdir(parents=True, exist_ok=True)
        libpath = ROOT / "fixtures/generated" / arch / "old/libdemo.so.1"
        apppath = ROOT / "fixtures/generated" / arch / "app"
        lib = libpath.read_bytes()
        tags, offset = tables(lib)
        sysv = offset(tags[4])
        buckets, count = struct.unpack_from("<II", lib, sysv)
        gnu = offset(tags[0x6ffffef5])
        nbucket, first, bloom, _ = struct.unpack_from("<IIII", lib, gnu)
        head = 16 + bloom * 8 + nbucket * 4
        maximum = max(struct.unpack_from("<I", lib, gnu + 16 + bloom * 8 + i * 4)[0] for i in range(nbucket))
        assert maximum >= first
        last = maximum
        while struct.unpack_from("<I", lib, gnu + head + (last - first) * 4)[0] & 1 == 0:
            last += 1
        gnu_bytes = lib[gnu:gnu + head + (last - first + 1) * 4]
        specifications = [
            ("gnu", libpath, lib, 0x6ffffef5, gnu_bytes, 4, [len(gnu_bytes) - 1, len(gnu_bytes) - 3]),
            ("sysv", libpath, lib, 4, lib[sysv:sysv + 8 + (buckets + count) * 4], 0x6ffffef5, [8 + (buckets + count) * 4 - 1]),
            ("dynsym", libpath, lib, 6, lib[offset(tags[6]):offset(tags[6]) + count * 24], None, [count * 24 - 1]),
            ("versym", libpath, lib, 0x6ffffff0, lib[offset(tags[0x6ffffff0]):offset(tags[0x6ffffff0]) + count * 2], None, [count * 2 - 1]),
        ]
        for label, sourcepath, definitions in [("verneed", apppath, False), ("verdef", libpath, True)]:
            source = sourcepath.read_bytes()
            source_tags, source_offset = tables(source)
            tag, payload, cuts = version_extent(source, source_tags, source_offset, definitions)
            specifications.append((label, sourcepath, source, tag, payload, None, cuts))
        for label, sourcepath, source, tag, payload, disable, cuts in specifications:
            variants = [("complete", payload, True)] + [("cut-" + str(size), payload[:size], False) for size in cuts]
            if label == "gnu":
                no_end = bytearray(payload)
                value = struct.unpack_from("<I", no_end, len(no_end) - 4)[0]
                struct.pack_into("<I", no_end, len(no_end) - 4, value & ~1)
                variants.append(("missing-last-terminator", no_end, False))
            for suffix, content, valid in variants:
                path = folder / (label + "-" + suffix + ".elf")
                output = place(source, tag, content, disable)
                path.write_bytes(output)
                records.append(dict(path=path.relative_to(ROOT).as_posix(), original=sourcepath.relative_to(ROOT).as_posix(),
                    table=label, valid=valid, sha256=hashlib.sha256(output).hexdigest(), table_bytes=len(content),
                    table_address=str(tables(output)[0][tag]), executed=False))
    (generated / "cases.json").write_text(json.dumps(records, indent=2) + "\n")
    print(f"Parser boundaries: {len(records)} non-executed inputs, {sum(r['valid'] for r in records)} complete controls")


if __name__ == "__main__":
    build()
