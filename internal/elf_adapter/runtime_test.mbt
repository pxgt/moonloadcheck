///|
test "runtime metadata survives stripping and section removal on both architectures" {
  for (arch, machine) in [("x86_64", 62), ("aarch64", 183)] {
    let root = "fixtures/generated/\{arch}/"
    let plain = @elf_adapter.read(@fs.read_file_to_bytes(root + "app"))
    assert_eq(plain.machine, machine)
    assert_eq(plain.runpath, Some(b"$ORIGIN/old"))
    assert_true(plain.needed.contains(b"libdemo.so.1"))
    assert_true(plain.interpreter is Some(_))
    assert_true(plain.unsupported.is_empty())
    for suffix in [".stripped", ".sectionless"] {
      assert_true(
        plain ==
        @elf_adapter.read(@fs.read_file_to_bytes(root + "app" + suffix)),
      )
    }
    let rpath = @elf_adapter.read(@fs.read_file_to_bytes(root + "rpath/app"))
    assert_eq(rpath.rpath, Some(b"$ORIGIN/lib"))
    assert_eq(rpath.runpath, None)
  }
}

///|
test "truncated objects are rejected as malformed" {
  try @elf_adapter.read(b"\x7fELF") catch {
    @model.ElfError::Malformed(_) => ()
    _ => fail("wrong error category")
  } noraise {
    _ => fail("accepted truncated input")
  }
}

///|
test "unverified OS ABI cannot silently enter a Linux compatibility result" {
  let original = @fs.read_file_to_bytes("fixtures/generated/x86_64/app")
  for (offset, value) in [(7, b'\xff'), (8, b'\x01')] {
    let bytes = original.to_array()
    bytes[offset] = value
    try @elf_adapter.read(Bytes::from_array(bytes[:])) catch {
      @model.ElfError::Unsupported(_) => ()
      _ => fail("wrong error category")
    } noraise {
      _ => fail("accepted unverified ABI")
    }
  }
}
