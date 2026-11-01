///|
fn tag(frame : Frame, key : UInt64) -> UInt64 raise @model.ElfError {
  match frame.tags.get(key) {
    Some(value) => value
    None =>
      raise @model.ElfError::Malformed("required dynamic tag missing: \{key}")
  }
}

///|
fn at(
  frame : Frame,
  address : UInt64,
  relative : Int32,
  size : Int32,
) -> Int32 raise {
  guard relative >= 0 && size >= 0 && relative <= frame.elf.data.length() - size else {
    raise @model.ElfError::Malformed("dynamic table range overflow")
  }
  file_range(frame.elf, address, relative + size) + relative
}

///|
fn string_at(frame : Frame, offset : UInt64) -> Bytes raise {
  frame.strings.get_raw(bounded(offset, frame.strings.data.length())).to_owned()
}

///|
fn version_needs(frame : Frame) -> Array[@model.VersionNeed] raise {
  let needs = []
  guard frame.tags.get(0x6ffffffe) is Some(address) else {
    guard frame.tags.get(0x6fffffff) is None else {
      raise @model.ElfError::Malformed("orphan VERNEEDNUM")
    }
    return needs
  }
  let data = frame.elf.data
  let count = bounded(tag(frame, 0x6fffffff), 32768)
  let mut relative = 0
  let indices : Map[Int32, Bool] = Map([])
  for i = 0; i < count; i = i + 1 {
    let start = at(frame, address, relative, 16)
    guard uint(data, start, 2) == 1 else {
      raise @model.ElfError::Malformed("unsupported VERNEED revision")
    }
    let provider = string_at(frame, uint(data, start + 4, 4))
    let auxiliaries = bounded(uint(data, start + 2, 2), 32768)
    let auxiliary = bounded(uint(data, start + 8, 4), data.length())
    guard auxiliary >= 16 && auxiliaries > 0 else {
      raise @model.ElfError::Malformed("invalid VERNEED auxiliary")
    }
    let mut offset = relative + auxiliary
    for j = 0; j < auxiliaries; j = j + 1 {
      let pos = at(frame, address, offset, 16)
      let hash = uint(data, pos, 4)
      let flags = uint(data, pos + 4, 2)
      let other = bounded(uint(data, pos + 6, 2), 65535)
      let index = other & 0x7fff
      let name = string_at(frame, uint(data, pos + 8, 4))
      guard hash == @elf.sysv_hash(name[:]).to_uint64() &&
        index >= 2 &&
        indices.get(index) is None else {
        raise @model.ElfError::Malformed(
          "invalid or duplicate version requirement",
        )
      }
      indices[index] = true
      needs.push({
        provider,
        name,
        hash,
        index,
        weak: (flags & 2) != 0,
        hidden: (other & 0x8000) != 0,
      })
      guard needs.length() <= 32768 else {
        raise @model.ElfError::ResourceLimit("too many version requirements")
      }
      let advance = bounded(uint(data, pos + 12, 4), data.length())
      if j + 1 < auxiliaries {
        guard advance >= 16 && advance <= data.length() - offset else {
          raise @model.ElfError::Malformed("VERNEED auxiliary chain")
        }
        offset += advance
      } else {
        guard advance == 0 else {
          raise @model.ElfError::Malformed("VERNEED auxiliary count mismatch")
        }
      }
    }
    let next = bounded(uint(data, start + 12, 4), data.length())
    if i + 1 < count {
      guard next >= 16 && next <= data.length() - relative else {
        raise @model.ElfError::Malformed("VERNEED chain")
      }
      relative += next
    } else {
      guard next == 0 else {
        raise @model.ElfError::Malformed("VERNEED count mismatch")
      }
    }
  }
  needs
}

///|
fn version_defs(frame : Frame) -> Array[@model.VersionDef] raise {
  let defs = []
  guard frame.tags.get(0x6ffffffc) is Some(address) else {
    guard frame.tags.get(0x6ffffffd) is None else {
      raise @model.ElfError::Malformed("orphan VERDEFNUM")
    }
    return defs
  }
  let data = frame.elf.data
  let count = bounded(tag(frame, 0x6ffffffd), 32768)
  let mut relative = 0
  let indices : Map[Int32, Bool] = Map([])
  for i = 0; i < count; i = i + 1 {
    let start = at(frame, address, relative, 20)
    guard uint(data, start, 2) == 1 else {
      raise @model.ElfError::Malformed("unsupported VERDEF revision")
    }
    let flags = bounded(uint(data, start + 2, 2), 65535)
    let index = bounded(uint(data, start + 4, 2), 32767)
    let auxiliaries = bounded(uint(data, start + 6, 2), 32768)
    let hash = uint(data, start + 8, 4)
    let auxiliary = bounded(uint(data, start + 12, 4), data.length())
    guard auxiliary >= 20 &&
      auxiliaries > 0 &&
      index > 0 &&
      indices.get(index) is None else {
      raise @model.ElfError::Malformed("invalid or duplicate VERDEF")
    }
    indices[index] = true
    let mut offset = relative + auxiliary
    for j = 0; j < auxiliaries; j = j + 1 {
      let pos = at(frame, address, offset, 8)
      let name = string_at(frame, uint(data, pos, 4))
      if j == 0 {
        guard hash == @elf.sysv_hash(name[:]).to_uint64() else {
          raise @model.ElfError::Malformed("VERDEF hash mismatch")
        }
        defs.push({ name, hash, index, flags, })
      }
      let advance = bounded(uint(data, pos + 4, 4), data.length())
      if j + 1 < auxiliaries {
        guard advance >= 8 && advance <= data.length() - offset else {
          raise @model.ElfError::Malformed("VERDEF auxiliary chain")
        }
        offset += advance
      } else {
        guard advance == 0 else {
          raise @model.ElfError::Malformed("VERDEF auxiliary count mismatch")
        }
      }
    }
    let next = bounded(uint(data, start + 16, 4), data.length())
    if i + 1 < count {
      guard next >= 20 && next <= data.length() - relative else {
        raise @model.ElfError::Malformed("VERDEF chain")
      }
      relative += next
    } else {
      guard next == 0 else {
        raise @model.ElfError::Malformed("VERDEF count mismatch")
      }
    }
  }
  defs
}

///|
fn references(frame : Frame) -> Array[@model.Reference] raise {
  let result : Array[@model.Reference] = []
  let data = frame.elf.data
  for
    (address_tag, size_tag, entry_tag, entry_size, table) in [
      (7UL, 8UL, 9UL, 24, "RELA"),
      (17UL, 18UL, 19UL, 16, "REL"),
      (23UL, 2UL, 20UL, 0, "JMPREL"),
    ] {
    if frame.tags.get(address_tag) is Some(address) {
      let entry = if address_tag == 23 {
        match tag(frame, entry_tag) {
          7 => 24
          17 => 16
          _ => raise @model.ElfError::Unsupported("PLT relocation encoding")
        }
      } else {
        guard tag(frame, entry_tag) == entry_size.to_uint64() else {
          raise @model.ElfError::Malformed("relocation entry size")
        }
        entry_size
      }
      let size = bounded(tag(frame, size_tag), data.length())
      guard size % entry == 0 else {
        raise @model.ElfError::Malformed("partial relocation entry")
      }
      let start = file_range(frame.elf, address, size)
      for pos = start; pos < start + size; pos = pos + entry {
        guard result.length() < 500000 else {
          raise @model.ElfError::ResourceLimit("too many relocations")
        }
        let info = uint(data, pos + 8, 8)
        result.push({
          symbol_index: bounded(info >> 32, 99999),
          offset: uint(data, pos, 8),
          relocation: bounded(info & 0xffffffff, 2147483647),
          table,
        })
      }
    } else {
      guard frame.tags.get(size_tag).unwrap_or(0) == 0 else {
        raise @model.ElfError::Malformed("relocation size without table")
      }
    }
  }
  result
}

///|
fn read_linkage_frame(frame : Frame) -> @model.Linkage raise {
  let data = frame.elf.data
  let references = references(frame)
  let version_needs = version_needs(frame)
  let version_defs = version_defs(frame)
  let version_indices : Map[Int32, Bool] = Map([])
  for need in version_needs {
    version_indices[need.index] = true
  }
  for def in version_defs {
    guard version_indices.get(def.index) is None else {
      raise @model.ElfError::Malformed("overlapping version indices")
    }
    version_indices[def.index] = true
  }
  let mut count = 0
  let mut exact = false
  let mut gnu_first = 0
  let mut gnu_end = 0
  let mut gnu_header = None
  if frame.tags.get(0x6ffffef5) is Some(address) {
    let start = at(frame, address, 0, 16)
    let buckets = bounded(uint(data, start, 4), 100000)
    let first = bounded(uint(data, start + 4, 4), 100000)
    let bloom = bounded(uint(data, start + 8, 4), 100000)
    let shift = bounded(uint(data, start + 12, 4), 31)
    guard buckets > 0 && bloom > 0 && (bloom & (bloom - 1)) == 0 else {
      raise @model.ElfError::Malformed("GNU hash dimensions")
    }
    let head = 16 + bloom * 8 + buckets * 4
    ignore(at(frame, address, 0, head))
    let mut maximum = 0
    for i = 0; i < buckets; i = i + 1 {
      let bucket = bounded(uint(data, start + 16 + bloom * 8 + i * 4, 4), 99999)
      guard bucket == 0 || bucket >= first else {
        raise @model.ElfError::Malformed("GNU hash bucket")
      }
      if bucket > maximum {
        maximum = bucket
      }
    }
    count = first
    if maximum != 0 {
      let mut index = maximum
      while true {
        guard index < 100000 else {
          raise @model.ElfError::ResourceLimit("GNU hash chain exceeds limit")
        }
        let pos = at(frame, address, head + (index - first) * 4, 4)
        index += 1
        if (uint(data, pos, 4) & 1) == 1 {
          break
        }
      }
      count = index
      exact = true
    }
    gnu_first = first
    gnu_end = count
    gnu_header = Some((address, start, buckets, bloom, shift, head))
  }
  if frame.tags.get(4) is Some(address) {
    let start = at(frame, address, 0, 8)
    let nchain = bounded(uint(data, start + 4, 4), 100000)
    guard nchain >= count else {
      raise @model.ElfError::Malformed("hash tables disagree on symbol extent")
    }
    count = nchain
    exact = true
  }
  guard frame.tags.get(4) is Some(_) || gnu_header is Some(_) else {
    raise @model.ElfError::Unsupported("no runtime hash table")
  }
  for reference in references {
    if reference.symbol_index >= count {
      guard !exact else {
        raise @model.ElfError::Malformed(
          "relocation symbol index outside table",
        )
      }
      count = reference.symbol_index + 1
    }
  }
  guard tag(frame, 11) == 24 else {
    raise @model.ElfError::Malformed("ELF64 dynamic symbol size")
  }
  let symbol_start = file_range(frame.elf, tag(frame, 6), count * 24)
  let versions = match frame.tags.get(0x6ffffff0) {
    Some(address) => Some(file_range(frame.elf, address, count * 2))
    None => None
  }
  let symbols : Array[@model.DynamicSymbol] = []
  for i = 0; i < count; i = i + 1 {
    let pos = symbol_start + i * 24
    let info = data[pos + 4].to_int()
    let version = match versions {
      None => 1
      Some(start) => bounded(uint(data, start + i * 2, 2), 65535)
    }
    let index = version & 0x7fff
    guard index < 2 || version_indices.get(index) is Some(_) else {
      raise @model.ElfError::Malformed("unresolved object-local version index")
    }
    symbols.push({
      name: string_at(frame, uint(data, pos, 4)),
      binding: info >> 4,
      kind: info & 15,
      visibility: data[pos + 5].to_int() & 3,
      section: bounded(uint(data, pos + 6, 2), 65535),
      value: uint(data, pos + 8, 8),
      size: uint(data, pos + 16, 8),
      version_index: index,
      version_hidden: (version & 0x8000) != 0,
      lookupable: false,
    })
  }
  if gnu_header is Some((address, start, buckets, bloom, shift, head)) {
    let visited : Map[Int32, Bool] = Map([])
    for bucket = 0; bucket < buckets; bucket = bucket + 1 {
      let mut index = bounded(
        uint(data, start + 16 + bloom * 8 + bucket * 4, 4),
        100000,
      )
      if index == 0 {
        continue
      }
      while true {
        guard index >= gnu_first &&
          index < gnu_end &&
          visited.get(index) is None else {
          raise @model.ElfError::Malformed(
            "overlapping or invalid GNU hash chains",
          )
        }
        visited[index] = true
        let hash = @elf.gnu_hash(symbols[index].name[:]).to_uint64()
        let stored = uint(
          data,
          at(frame, address, head + (index - gnu_first) * 4, 4),
          4,
        )
        let bloom_word = uint(
          data,
          start + 16 + bounded(hash / 64 % bloom.to_uint64(), bloom) * 8,
          8,
        )
        let mask = (1UL << bounded(hash % 64, 63)) |
          (1UL << bounded((hash >> shift) % 64, 63))
        guard (stored | 1) == (hash | 1) &&
          hash % buckets.to_uint64() == bucket.to_uint64() &&
          (bloom_word & mask) == mask else {
          raise @model.ElfError::Malformed(
            "GNU hash does not expose the named symbol",
          )
        }
        symbols[index] = { ..symbols[index], lookupable: true, }
        index += 1
        if (stored & 1) == 1 {
          break
        }
      }
    }
  } else {
    let address = tag(frame, 4)
    let start = at(frame, address, 0, 8)
    let buckets = bounded(uint(data, start, 4), 100000)
    guard buckets > 0 else {
      raise @model.ElfError::Malformed("empty SysV hash buckets")
    }
    ignore(at(frame, address, 0, 8 + (buckets + count) * 4))
    let visited : Map[Int32, Bool] = Map([])
    for bucket = 0; bucket < buckets; bucket = bucket + 1 {
      let mut index = bounded(uint(data, start + 8 + bucket * 4, 4), count)
      while index != 0 {
        guard index < count && visited.get(index) is None else {
          raise @model.ElfError::Malformed("SysV hash cycle or invalid index")
        }
        visited[index] = true
        guard @elf.sysv_hash(symbols[index].name[:]).to_uint64() %
          buckets.to_uint64() ==
          bucket.to_uint64() else {
          raise @model.ElfError::Malformed("SysV hash bucket mismatch")
        }
        symbols[index] = { ..symbols[index], lookupable: true, }
        index = bounded(uint(data, start + 8 + (buckets + index) * 4, 4), count)
      }
    }
  }
  {
    object: frame.object,
    symbols,
    references,
    version_needs,
    version_defs,
    has_versions: versions is Some(_),
    symbolic: frame.tags.get(16) is Some(_) ||
    (frame.tags.get(30).unwrap_or(0) & 2) != 0,
    bind_now: frame.tags.get(24) is Some(_) ||
    (frame.tags.get(30).unwrap_or(0) & 8) != 0 ||
    (frame.tags.get(0x6ffffffb).unwrap_or(0) & 1) != 0,
  }
}

///|
pub fn read_linkage(data : Bytes) -> @model.Linkage raise @model.ElfError {
  read_linkage_frame(read_frame(data)) catch {
    @model.ElfError::Malformed(message) =>
      raise @model.ElfError::Malformed(message)
    @model.ElfError::Unsupported(message) =>
      raise @model.ElfError::Unsupported(message)
    @model.ElfError::ResourceLimit(message) =>
      raise @model.ElfError::ResourceLimit(message)
    error => raise @model.ElfError::Malformed("\{error}")
  }
}
