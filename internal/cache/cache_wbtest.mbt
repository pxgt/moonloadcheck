///|
test "cache conditions are not guessed and the first pathname is final" {
  let entries : Array[Record] = [
    {
      name: b"libx.so.1",
      path: b"/first",
      flags: 0x303,
      osversion: 0,
      hwcap: 0,
    },
    {
      name: b"libx.so.1",
      path: b"/second",
      flags: 0x303,
      osversion: 0,
      hwcap: 0,
    },
  ]
  assert_eq(select(entries, b"libx.so.1", 62), Some(b"/first"))
  assert_eq(select(entries, b"libx.so.1", 183), None)
  entries[0] = { ..entries[0], hwcap: 1, }
  try select(entries, b"libx.so.1", 62) catch {
    Unsupported(_) => ()
    _ => fail("wrong error category")
  } noraise {
    _ => fail("guessed hardware conditions")
  }
}

///|
test "malformed cache bounds and strings are rejected" {
  let header = b"glibc-ld.so.cache1.1".to_array()
  while header.length() < 48 {
    header.push(0)
  }
  header[20] = 1
  try decode(Bytes::from_array(header[:])) catch {
    Invalid(_) => ()
    _ => fail("wrong error category")
  } noraise {
    _ => fail("accepted truncated record")
  }
  assert_true(compare(b"libx.so.10", b"libx.so.9") > 0)
  assert_true(compare(b"libx.so.1", b"libx.so.a") > 0)
}
