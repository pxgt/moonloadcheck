///|
pub(all) suberror CacheError {
  Invalid(String)
  Unsupported(String)
}

///|
pub(all) struct Record {
  name : Bytes
  path : Bytes
  flags : UInt64
  osversion : UInt64
  hwcap : UInt64
}

///|
fn word(data : Bytes, pos : Int32, width : Int32) -> UInt64 raise CacheError {
  guard pos >= 0 && pos <= data.length() && width <= data.length() - pos else {
    raise Invalid("cache record outside file")
  }
  let mut value : UInt64 = 0
  for i = 0; i < width; i = i + 1 {
    value = value | (data[pos + i].to_uint64() << (8 * i))
  }
  value
}

///|
fn small(value : UInt64, limit : Int32) -> Int32 raise CacheError {
  guard value <= limit.to_uint64() else {
    raise Invalid("cache bounds exceeded")
  }
  value.reinterpret_as_int64().to_int()
}

///|
fn cstring(
  data : Bytes,
  pos : Int32,
  start : Int32,
  end : Int32,
) -> Bytes raise CacheError {
  guard pos >= start && pos < end else { raise Invalid("cache string offset") }
  for i = pos; i < end; i = i + 1 {
    if data[i] == 0 {
      return data[pos:i].to_owned()
    }
  }
  raise Invalid("unterminated cache string")
}

///|
fn digit(value : Byte) -> Bool {
  value >= b'0' && value <= b'9'
}

///|
fn compare(left : Bytes, right : Bytes) -> Int32 raise CacheError {
  let mut i = 0
  let mut j = 0
  while i < left.length() && j < right.length() {
    if digit(left[i]) && digit(right[j]) {
      let mut a : UInt64 = 0
      let mut b : UInt64 = 0
      while i < left.length() && digit(left[i]) {
        a = a * 10 + (left[i] - b'0').to_uint64()
        guard a <= 2147483647 else {
          raise Unsupported("oversized numeric cache name")
        }
        i += 1
      }
      while j < right.length() && digit(right[j]) {
        b = b * 10 + (right[j] - b'0').to_uint64()
        guard b <= 2147483647 else {
          raise Unsupported("oversized numeric cache name")
        }
        j += 1
      }
      if a != b {
        return if a > b { 1 } else { -1 }
      }
    } else {
      if digit(left[i]) && !digit(right[j]) {
        return 1
      }
      if !digit(left[i]) && digit(right[j]) {
        return -1
      }
      if left[i] != right[j] {
        return if left[i] > right[j] { 1 } else { -1 }
      }
      i += 1
      j += 1
    }
  }
  if i < left.length() {
    1
  } else if j < right.length() {
    -1
  } else {
    0
  }
}

///|
/// Read modern little-endian glibc cache records, preserving file order.
/// Candidate lookup remains separate from filesystem lookup.
pub fn decode(data : Bytes) -> Array[Record] raise CacheError {
  guard data.length() <= 16777216 else {
    raise Unsupported("cache exceeds 16 MiB")
  }
  let mut base = 0
  if data.length() >= 16 && data[:11] == b"ld.so-1.7.0"[:] {
    let old_count = small(word(data, 12, 4), 100000)
    base = (16 + old_count * 12 + 7) & -8
  }
  guard base <= data.length() - 48 &&
    data[base:base + 20] == b"glibc-ld.so.cache1.1"[:] else {
    raise Unsupported("requires glibc cache 1.1")
  }
  guard data[base + 28] == 0 || data[base + 28] == 2 else {
    raise Unsupported("unsupported cache endian/flags")
  }
  let count = small(word(data, base + 20, 4), 100000)
  let start = base + 48 + count * 24
  guard start <= data.length() else { raise Invalid("cache table truncated") }
  let end = start + small(word(data, base + 24, 4), data.length() - start)
  let extension = small(word(data, base + 32, 4), data.length())
  if extension != 0 {
    guard extension >= end && extension % 4 == 0 else {
      raise Invalid("cache extension offset")
    }
    guard word(data, extension, 4) == 0xeaa42174 else {
      raise Invalid("cache extension magic")
    }
    let sections = small(word(data, extension + 4, 4), 4096)
    for i = 0; i < sections; i = i + 1 {
      let entry = extension + 8 + i * 16
      let offset = small(word(data, entry + 8, 4), data.length())
      ignore(small(word(data, entry + 12, 4), data.length() - offset))
    }
  }
  let records : Array[Record] = []
  for i = 0; i < count; i = i + 1 {
    let entry = base + 48 + i * 24
    let name = cstring(
      data,
      base + small(word(data, entry + 4, 4), data.length() - base),
      start,
      end,
    )
    let path = cstring(
      data,
      base + small(word(data, entry + 8, 4), data.length() - base),
      start,
      end,
    )
    guard !name.is_empty() && !path.is_empty() && path[0] == b'/' else {
      raise Invalid("cache names and paths")
    }
    if i > 0 {
      guard compare(records[i - 1].name, name) >= 0 else {
        raise Invalid("cache is not sorted")
      }
    }
    records.push({
      name,
      path,
      flags: word(data, entry, 4),
      osversion: word(data, entry + 12, 4),
      hwcap: word(data, entry + 16, 8),
    })
  }
  records
}

///|
/// glibc selects one cached pathname. A stale path does not advance to another
/// same-name cache record. Hardware/OS conditions remain explicit unknowns.
pub fn select(
  records : Array[Record],
  name : Bytes,
  machine : Int32,
) -> Bytes? raise CacheError {
  let flags : UInt64 = if machine == 62 { 0x303 } else { 0xa03 }
  for record in records {
    if compare(record.name, name) == 0 && record.flags == flags {
      guard record.hwcap == 0 && record.osversion == 0 else {
        raise Unsupported(
          "cache selection needs hardware or OS-version evidence",
        )
      }
      return Some(record.path)
    }
  }
  None
}
