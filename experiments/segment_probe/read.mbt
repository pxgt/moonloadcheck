///|
/// Original M0 adapter experiment. Reuses upstream ELF headers/segments/strings.
pub(all) suberror ReadError {
  Malformed(String)
  Unsupported(String)
}

///|
fn uint(
  data : BytesView,
  offset : Int32,
  width : Int32,
) -> UInt64 raise ReadError {
  guard offset >= 0 &&
    offset <= data.length() &&
    width <= data.length() - offset else {
    raise Malformed("integer outside file")
  }
  let mut value : UInt64 = 0
  for i = 0; i < width; i = i + 1 {
    value = value | (data[offset + i].to_uint64() << (8 * i))
  }
  value
}

///|
fn bounded(value : UInt64, limit : Int32) -> Int32 raise ReadError {
  guard value <= limit.to_uint64() else {
    raise Malformed("value exceeds its bounded range")
  }
  value.reinterpret_as_int64().to_int()
}

///|
fn file_range(
  elf : @elf.ElfBytes,
  address : UInt64,
  length : Int32,
) -> Int32 raise {
  guard length >= 0 else { raise Malformed("negative range") }
  if elf.segments() is Some(segments) {
    for i = 0; i < segments.len(); i = i + 1 {
      let segment = segments.get(i)
      if segment.p_type == @elf.PT_LOAD && address >= segment.p_vaddr {
        let delta = address - segment.p_vaddr
        if delta <= segment.p_filesz &&
          length.to_uint64() <= segment.p_filesz - delta {
          let start = bounded(segment.p_offset, elf.data.length())
          let displacement = bounded(delta, elf.data.length() - start)
          guard length <= elf.data.length() - start - displacement else {
            raise Malformed("segment range outside file")
          }
          return start + displacement
        }
      }
    }
  }
  raise Malformed("virtual address is not file backed")
}

///|
fn required(tags : Map[Int32, UInt64], key : Int32) -> UInt64 raise ReadError {
  match tags.get(key) {
    Some(value) => value
    None => raise Malformed("required dynamic tag missing: \{key}")
  }
}

///|
pub(all) struct SegmentFacts {
  machine : Int32
  needed : Array[Bytes]
  symbol_names : Array[Bytes]
  symbol_extent_exact : Bool
  required_versions : Array[Bytes]
} derive(Eq)

///|
pub extend SegmentFacts with Eq::{equal, not_equal}

///|
/// A bounded ELF64-LE experiment, not the production compatibility engine.
pub fn read(data : Bytes) -> SegmentFacts raise {
  guard data.length() <= 134217728 else {
    raise Unsupported("M0 input limit is 128 MiB")
  }
  let elf = @elf.ElfBytes::minimal_parse(data[:])
  guard elf.ehdr.class == @elf.ELF64 && elf.ehdr.endianness == @elf.Little else {
    raise Unsupported("M0 adapter supports ELF64 little endian")
  }
  let tags : Map[Int32, UInt64] = Map([])
  let needed_offsets = []
  let mut found_dynamic = false
  if elf.segments() is Some(segments) {
    for i = 0; i < segments.len(); i = i + 1 {
      let segment = segments.get(i)
      if segment.p_type == @elf.PT_DYNAMIC {
        guard !found_dynamic else {
          raise Malformed("multiple dynamic segments")
        }
        found_dynamic = true
        let bytes = elf.segment_data(segment)
        guard bytes.length() % 16 == 0 else {
          raise Malformed("partial dynamic entry")
        }
        let mut terminated = false
        for offset = 0; offset < bytes.length(); offset = offset + 16 {
          let key = bounded(uint(bytes, offset, 8), 2147483647)
          if key == 0 {
            terminated = true
            break
          }
          let value = uint(bytes, offset + 8, 8)
          if key == 1 {
            needed_offsets.push(value)
          } else {
            tags[key] = value
          }
        }
        guard terminated else {
          raise Malformed("unterminated dynamic segment")
        }
      }
    }
  }
  guard found_dynamic else { raise Unsupported("no dynamic segment") }
  let string_size = bounded(required(tags, 10), data.length())
  let string_start = file_range(elf, required(tags, 5), string_size)
  let strings = @elf.StringTable::new(
    data[string_start:string_start + string_size],
  )
  let needed = []
  for offset in needed_offsets {
    needed.push(strings.get_raw(bounded(offset, string_size)).to_owned())
  }
  let mut symbol_extent_exact = tags.get(4) is Some(_)
  let mut symbol_count = match tags.get(4) {
    Some(address) => {
      let offset = file_range(elf, address, 8)
      bounded(uint(data[:], offset + 4, 4), 1000000)
    }
    None => {
      let address = required(tags, 0x6ffffef5)
      let base = file_range(elf, address, 16)
      let buckets = bounded(uint(data[:], base, 4), 1000000)
      let first = bounded(uint(data[:], base + 4, 4), 1000000)
      let bloom = bounded(uint(data[:], base + 8, 4), 1000000)
      let head_size = 16 + bloom * 8 + buckets * 4
      ignore(file_range(elf, address, head_size))
      let mut maximum = 0
      for i = 0; i < buckets; i = i + 1 {
        let bucket = bounded(
          uint(data[:], base + 16 + bloom * 8 + i * 4, 4),
          1000000,
        )
        guard bucket == 0 || bucket >= first else {
          raise Malformed("bad GNU hash bucket")
        }
        maximum = if bucket > maximum { bucket } else { maximum }
      }
      if maximum == 0 {
        first
      } else {
        symbol_extent_exact = true
        let mut index = maximum
        while true {
          guard index < 1000000 else {
            raise Malformed("GNU hash symbol limit")
          }
          let end = head_size + (index - first + 1) * 4
          ignore(file_range(elf, address, end))
          let hash = uint(data[:], base + end - 4, 4)
          index += 1
          if (hash & 1) == 1 {
            break
          }
        }
        index
      }
    }
  }
  // An empty GNU hash does not bound trailing undefined symbols (observed on
  // AArch64). Include the actual symbol indices from dynamic relocations.
  for
    (address_tag, size_tag, entry_size, entry_tag) in [
      (7, 8, 24, 9),
      (17, 18, 16, 19),
      (23, 2, 0, 20),
    ] {
    if tags.get(address_tag) is Some(address) {
      let entry = if address_tag == 23 {
        match required(tags, entry_tag) {
          7 => 24
          17 => 16
          _ => raise Unsupported("unknown PLT relocation format")
        }
      } else {
        guard required(tags, entry_tag) == entry_size.to_uint64() else {
          raise Malformed("relocation entry size")
        }
        entry_size
      }
      let size = bounded(required(tags, size_tag), data.length())
      guard size % entry == 0 else {
        raise Malformed("partial relocation entry")
      }
      let base = file_range(elf, address, size)
      for offset = 0; offset < size; offset = offset + entry {
        let symbol = bounded(uint(data[:], base + offset + 8, 8) >> 32, 999999)
        if symbol + 1 > symbol_count {
          guard !symbol_extent_exact else {
            raise Malformed("relocation exceeds symbol table")
          }
          symbol_count = symbol + 1
        }
      }
    }
  }
  guard required(tags, 11) == 24 else {
    raise Malformed("invalid ELF64 symbol size")
  }
  let symbols = file_range(elf, required(tags, 6), symbol_count * 24)
  let symbol_names = []
  for i = 0; i < symbol_count; i = i + 1 {
    let offset = bounded(uint(data[:], symbols + i * 24, 4), string_size)
    symbol_names.push(strings.get_raw(offset).to_owned())
  }
  let required_versions = []
  if tags.get(0x6ffffffe) is Some(address) {
    let count = bounded(required(tags, 0x6fffffff), 65536)
    let mut relative = 0
    for i = 0; i < count; i = i + 1 {
      let end = relative + 16
      let start = file_range(elf, address, end) + relative
      guard uint(data[:], start, 2) == 1 else {
        raise Malformed("version need revision")
      }
      let auxiliary_count = bounded(uint(data[:], start + 2, 2), 65536)
      let auxiliary = bounded(uint(data[:], start + 8, 4), data.length())
      let next = bounded(uint(data[:], start + 12, 4), data.length())
      guard auxiliary_count == 0 || auxiliary >= 16 else {
        raise Malformed("invalid version auxiliary offset")
      }
      let mut auxiliary_relative = relative + auxiliary
      for j = 0; j < auxiliary_count; j = j + 1 {
        let pos = file_range(elf, address, auxiliary_relative + 16) +
          auxiliary_relative
        let name = bounded(uint(data[:], pos + 8, 4), string_size)
        required_versions.push(strings.get_raw(name).to_owned())
        let advance = bounded(uint(data[:], pos + 12, 4), data.length())
        if j + 1 < auxiliary_count {
          guard advance >= 16 else {
            raise Malformed("version auxiliary chain ended early")
          }
          guard advance <= data.length() - auxiliary_relative else {
            raise Malformed("version auxiliary overflow")
          }
          auxiliary_relative += advance
        } else {
          guard advance == 0 else {
            raise Malformed("version auxiliary chain exceeds count")
          }
        }
      }
      if i + 1 < count {
        guard next >= 16 && next <= data.length() - relative else {
          raise Malformed("version need chain ended early")
        }
        relative += next
      } else {
        guard next == 0 else {
          raise Malformed("version need chain exceeds count")
        }
      }
    }
  }
  {
    machine: elf.ehdr.e_machine.to_int(),
    needed,
    symbol_names,
    symbol_extent_exact,
    required_versions,
  }
}
