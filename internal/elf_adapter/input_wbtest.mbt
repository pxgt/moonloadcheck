///|
fn edit_dynamic(data : Bytes, key : UInt64, value : UInt64) -> Bytes raise {
  let frame = read_frame(data)
  let segments = frame.elf.segments().unwrap()
  for i in 0..<segments.len() {
    let segment = segments.get(i)
    if segment.p_type == @elf.PT_DYNAMIC {
      let start = bounded(segment.p_offset, data.length())
      let size = bounded(segment.p_filesz, data.length() - start)
      for offset = start; offset < start + size; offset = offset + 16 {
        if uint(data[:], offset, 8) == key {
          return edited(data, offset + 8, value, 8)
        }
      }
    }
  }
  fail("test dynamic tag absent")
}

///|
fn malformed_linkage(data : Bytes) -> Unit raise {
  try read_linkage(data) catch {
    @model.ElfError::Malformed(_) => ()
    _ => fail("expected malformed input")
  } noraise {
    _ => fail("invalid input accepted")
  }
}

///|
test "valid unsupported ELF classes differ from non-ELF and truncated headers" {
  for case in ["rel64", "elf32", "big-endian"] {
    let data = @fs.read_file_to_bytes("fixtures/generated/inputs/\{case}.o")
    try read_linkage(data) catch {
      @model.ElfError::Unsupported(_) => ()
      _ => fail("valid unsupported ELF misclassified: " + case)
    } noraise {
      _ => fail("unsupported ELF accepted")
    }
  }
  malformed_linkage(b"not an ELF input")
  let source = @fs.read_file_to_bytes("fixtures/generated/x86_64/app")
  for size in [0, 1, 7, 15, 31, 63] {
    malformed_linkage(source[0:size].to_owned())
  }
}

///|
test "unterminated strings and zero-advance version chains are malformed" {
  for arch in ["x86_64", "aarch64"] {
    let source = @fs.read_file_to_bytes("fixtures/generated/\{arch}/app")
    let frame = read_frame(source)
    let start = file_range(
      frame.elf,
      tag(frame, 5),
      frame.strings.data.length(),
    )
    let bytes = source.to_array()
    for i in start..<(start + frame.strings.data.length()) {
      bytes[i] = b'a'
    }
    malformed_linkage(Bytes::from_array(bytes[:]))
    let needs = at(frame, tag(frame, 0x6ffffffe), 0, 16)
    assert_true(tag(frame, 0x6fffffff) > 1)
    malformed_linkage(edited(source, needs + 12, 0, 4))
    let auxiliary = bounded(uint(source[:], needs + 8, 4), source.length())
    let stalled = edited(
      edited(source, needs + 2, 2, 2),
      needs + auxiliary + 12,
      0,
      4,
    )
    malformed_linkage(stalled)
    let library = @fs.read_file_to_bytes(
      "fixtures/generated/\{arch}/old/libdemo.so.1",
    )
    let frame = read_frame(library)
    let defs = at(frame, tag(frame, 0x6ffffffc), 0, 20)
    assert_true(tag(frame, 0x6ffffffd) > 1)
    malformed_linkage(edited(library, defs + 16, 0, 4))
  }
}

///|
test "dynamic and string table truncation and unmapped version addresses cannot pass" {
  for arch in ["x86_64", "aarch64"] {
    let source = @fs.read_file_to_bytes("fixtures/generated/\{arch}/app")
    let frame = read_frame(source)
    let segments = frame.elf.segments().unwrap()
    let phoff = bounded(uint(source[:], 32, 8), source.length())
    for i in 0..<segments.len() {
      if segments.get(i).p_type == @elf.PT_DYNAMIC {
        malformed_linkage(edited(source, phoff + i * 56 + 32, 16, 8))
      }
    }
    malformed_linkage(edit_dynamic(source, 10, 1))
    malformed_linkage(edit_dynamic(source, 0x6ffffffe, 0xfffffffffffffff8))
    let library = @fs.read_file_to_bytes(
      "fixtures/generated/\{arch}/old/libdemo.so.1",
    )
    malformed_linkage(edit_dynamic(library, 0x6ffffffc, 0xfffffffffffffff8))
  }
}
