///|
fn uint(
  data : BytesView,
  offset : Int32,
  width : Int32,
) -> UInt64 raise @model.ElfError {
  guard offset >= 0 &&
    width >= 0 &&
    offset <= data.length() &&
    width <= data.length() - offset else {
    raise @model.ElfError::Malformed("integer outside file")
  }
  let mut value : UInt64 = 0
  for i = 0; i < width; i = i + 1 {
    value = value | (data[offset + i].to_uint64() << (8 * i))
  }
  value
}

///|
fn bounded(value : UInt64, limit : Int32) -> Int32 raise @model.ElfError {
  guard value <= limit.to_uint64() else {
    raise @model.ElfError::Malformed("file range exceeds input")
  }
  value.reinterpret_as_int64().to_int()
}

///|
fn file_range(
  elf : @elf.ElfBytes,
  address : UInt64,
  length : Int32,
) -> Int32 raise {
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
            raise @model.ElfError::Malformed("segment outside file")
          }
          return start + displacement
        }
      }
    }
  }
  raise @model.ElfError::Malformed("dynamic string address is not file backed")
}

///|
fn string_tag(
  tags : Map[UInt64, UInt64],
  key : UInt64,
  strings : @elf.StringTable,
) -> Bytes? raise {
  match tags.get(key) {
    None => None
    Some(offset) =>
      Some(strings.get_raw(bounded(offset, strings.data.length())).to_owned())
  }
}

///|
fn read_runtime(data : Bytes) -> @model.ElfObject raise {
  guard data.length() <= 134217728 else {
    raise @model.ElfError::ResourceLimit("ELF exceeds 128 MiB")
  }
  let elf = @elf.ElfBytes::minimal_parse(data[:])
  guard elf.ehdr.class == @elf.ELF64 && elf.ehdr.endianness == @elf.Little else {
    raise @model.ElfError::Unsupported("only ELF64 little endian is modeled")
  }
  guard (elf.ehdr.osabi == 0 || elf.ehdr.osabi == 3) && elf.ehdr.abiversion == 0 else {
    raise @model.ElfError::Unsupported(
      "OS ABI or ABI revision is outside the verified Linux profile",
    )
  }
  let kind = elf.ehdr.e_type.to_int()
  guard kind == 2 || kind == 3 else {
    raise @model.ElfError::Unsupported("only ET_EXEC and ET_DYN are modeled")
  }
  let tags : Map[UInt64, UInt64] = Map([])
  let needed_offsets : Array[UInt64] = []
  let mut interpreter = None
  let mut dynamic = false
  let unsupported = []
  if elf.segments() is Some(segments) {
    guard segments.len() <= 4096 else {
      raise @model.ElfError::ResourceLimit("too many program headers")
    }
    for i = 0; i < segments.len(); i = i + 1 {
      let segment = segments.get(i)
      if segment.p_type == @elf.PT_LOAD {
        guard segment.p_filesz <= segment.p_memsz else {
          raise @model.ElfError::Malformed(
            "PT_LOAD file size exceeds memory size",
          )
        }
        ignore(elf.segment_data(segment))
      }
      if segment.p_type == @elf.PT_INTERP {
        guard interpreter is None else {
          raise @model.ElfError::Malformed("multiple interpreters")
        }
        let value = elf.segment_data(segment)
        guard value.length() >= 2 && value[value.length() - 1] == 0 else {
          raise @model.ElfError::Malformed("invalid interpreter string")
        }
        for j = 0; j < value.length() - 1; j = j + 1 {
          guard value[j] != 0 else {
            raise @model.ElfError::Malformed("embedded NUL in interpreter")
          }
        }
        interpreter = Some(value[:value.length() - 1].to_owned())
      }
      if segment.p_type == @elf.PT_DYNAMIC {
        guard !dynamic else {
          raise @model.ElfError::Malformed("multiple dynamic segments")
        }
        dynamic = true
        let bytes = elf.segment_data(segment)
        guard bytes.length() % 16 == 0 else {
          raise @model.ElfError::Malformed("partial dynamic entry")
        }
        guard bytes.length() / 16 <= 65536 else {
          raise @model.ElfError::ResourceLimit("too many dynamic entries")
        }
        let mut terminated = false
        for offset = 0; offset < bytes.length(); offset = offset + 16 {
          let key = uint(bytes, offset, 8)
          if key == 0 {
            terminated = true
            break
          }
          let value = uint(bytes, offset + 8, 8)
          if key == 1 {
            needed_offsets.push(value)
          } else {
            if key == 5 ||
              key == 10 ||
              key == 14 ||
              key == 15 ||
              key == 29 ||
              key == 0x6ffffffb {
              guard tags.get(key) is None else {
                raise @model.ElfError::Malformed(
                  "duplicate singleton dynamic tag",
                )
              }
            }
            tags[key] = value
          }
          if key == 0x7fffffff ||
            key == 0x7ffffffd ||
            key == 0x6ffffefb ||
            key == 0x6ffffefc {
            unsupported.push("dynamic filter, auxiliary or audit loading")
          }
        }
        guard terminated else {
          raise @model.ElfError::Malformed("unterminated dynamic segment")
        }
      }
    }
  }
  guard dynamic else {
    raise @model.ElfError::Unsupported("static objects are not modeled yet")
  }
  let strings = match (tags.get(5), tags.get(10)) {
    (Some(address), Some(size)) => {
      let size = bounded(size, data.length())
      let start = file_range(elf, address, size)
      @elf.StringTable::new(data[start:start + size])
    }
    _ => raise @model.ElfError::Malformed("dynamic string table missing")
  }
  let needed = []
  for offset in needed_offsets {
    let name = strings
      .get_raw(bounded(offset, strings.data.length()))
      .to_owned()
    guard !name.is_empty() else {
      raise @model.ElfError::Malformed("empty DT_NEEDED")
    }
    needed.push(name)
  }
  let flags = tags.get(0x6ffffffb).unwrap_or(0)
  // Dependencies affected by unmodeled DF_1 flags must not silently pass.
  if (flags & (0xffffffffffffffff ^ 0x08000881)) != 0 {
    unsupported.push("unmodeled DT_FLAGS_1 behavior")
  }
  {
    machine: elf.ehdr.e_machine.to_int(),
    object_type: kind,
    interpreter,
    needed,
    soname: string_tag(tags, 14, strings),
    rpath: string_tag(tags, 15, strings),
    runpath: string_tag(tags, 29, strings),
    no_default_lib: (flags & 0x800) != 0,
    pie: (flags & 0x08000000) != 0,
    unsupported,
  }
}

///|
/// Program headers and dynamic segments are authoritative, including on stripped
/// and sectionless objects. No executable code from the input is run.
pub fn read(data : Bytes) -> @model.ElfObject raise @model.ElfError {
  read_runtime(data) catch {
    @model.ElfError::Malformed(message) =>
      raise @model.ElfError::Malformed(message)
    @model.ElfError::Unsupported(message) =>
      raise @model.ElfError::Unsupported(message)
    @model.ElfError::ResourceLimit(message) =>
      raise @model.ElfError::ResourceLimit(message)
    error => raise @model.ElfError::Malformed("\{error}")
  }
}
