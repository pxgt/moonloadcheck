"""Byte edits for our own ELF64-LE regression fixtures, not an analysis backend."""
import struct


def tables(data):
    offset = struct.unpack_from("<Q", data, 32)[0]
    width, count = struct.unpack_from("<HH", data, 54)
    segments, tags = [], {}
    for i in range(count):
        p = offset + width * i
        kind, _, fileoff, address, _, size = struct.unpack_from("<IIQQQQ", data, p)
        if kind == 1:
            segments.append((address, size, fileoff))
        if kind == 2:
            for q in range(fileoff, fileoff + size, 16):
                key, value = struct.unpack_from("<QQ", data, q)
                if key == 0:
                    break
                tags[key] = value
    def file_offset(address):
        for base, size, offset in segments:
            if base <= address < base + size:
                return offset + address - base
        raise ValueError("address is not file backed")
    return tags, file_offset


def weaken_or_detach_version(source, weak=False, detach=False):
    data = bytearray(source)
    tags, file_offset = tables(data)
    strings = file_offset(tags[5])
    def name(offset):
        start = strings + offset
        return bytes(data[start:data.index(0, start)])
    need = file_offset(tags[0x6ffffffe])
    chosen = None
    for _ in range(tags[0x6fffffff]):
        _, count, filename, aux, next_node = struct.unpack_from("<HHIII", data, need)
        pos = need + aux
        for _ in range(count):
            _, flags, other, version, advance = struct.unpack_from("<IHHII", data, pos)
            if name(filename) == b"libdemo.so.1" and name(version) == b"DEMO_2":
                chosen = other & 0x7fff
                if weak:
                    struct.pack_into("<H", data, pos + 4, flags | 2)
            pos += advance
        need += next_node
    if chosen is None:
        raise ValueError("expected version requirement not found")
    if detach:
        # The existing GNU-hash first-export index bounds undefined imports for
        # these fixtures. Relocation indices also cover the AArch64 empty hash.
        count = struct.unpack_from("<I", data, file_offset(tags[0x6ffffef5]) + 4)[0]
        for address_tag, size_tag, width in [(7, 8, 24), (23, 2, 24)]:
            if address_tag in tags:
                start = file_offset(tags[address_tag])
                for pos in range(start, start + tags[size_tag], width):
                    symbol = struct.unpack_from("<Q", data, pos + 8)[0] >> 32
                    count = max(count, symbol + 1)
        versym = file_offset(tags[0x6ffffff0])
        for i in range(count):
            if struct.unpack_from("<H", data, versym + i * 2)[0] & 0x7fff == chosen:
                struct.pack_into("<H", data, versym + i * 2, 1)
    return bytes(data)
