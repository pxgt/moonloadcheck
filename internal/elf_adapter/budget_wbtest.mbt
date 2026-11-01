///|
test "resource budgets differ from malformed input and repeated names share storage" {
  let source = @fs.read_file_to_bytes(
    "fixtures/generated/x86_64/old/libdemo.so.1",
  )
  let frame = read_frame(source)
  let hash = at(frame, tag(frame, 4), 0, 8)
  try read_linkage(edited(source, hash + 4, 100001, 4)) catch {
    @model.ElfError::ResourceLimit(_) => ()
    _ => fail("count limit misclassified")
  } noraise {
    _ => fail("count limit ignored")
  }
  let bytes = Bytes::make(65538, b'a').to_array()
  bytes[65537] = 0
  let data = Bytes::from_array(bytes[:])
  let frame = {
    ..frame,
    strings: @elf.StringTable::new(data[:]),
    names: { cache: Map([]), bytes: 0, },
  }
  try string_at(frame, 0) catch {
    @model.ElfError::ResourceLimit(_) => ()
    _ => fail("name limit misclassified")
  } noraise {
    _ => fail("name limit ignored")
  }
  let value = string_at(frame, 1)
  for _ in 0..<256 {
    assert_eq(string_at(frame, 1), value)
  }
  assert_eq(frame.names.bytes, 65536)
  // Distinct suffix offsets still consume the aggregate name budget.
  try {
    for offset in 2..<131 {
      ignore(string_at(frame, offset.to_uint64()))
    }
    fail("aggregate name budget ignored")
  } catch {
    @model.ElfError::ResourceLimit(_) => ()
    _ => fail("aggregate name limit misclassified")
  }
}
