///|
test "production linkage reads sectionless symbols and object-local GNU versions" {
  for arch in ["x86_64", "aarch64"] {
    let base = "fixtures/generated/\{arch}/"
    for suffix in ["", ".stripped", ".sectionless"] {
      let info = @elf_adapter.read_linkage(
        @fs.read_file_to_bytes(base + "app" + suffix),
      )
      assert_true(
        info.version_needs.any(need => {
          need.name == b"DEMO_1" && need.provider == b"libdemo.so.1"
        }),
      )
      assert_true(
        info.references.any(reference => {
          info.symbols[reference.symbol_index].name == b"api"
        }),
      )
    }
    let old = @elf_adapter.read_linkage(
      @fs.read_file_to_bytes(base + "old/libdemo.so.1"),
    )
    let newer = @elf_adapter.read_linkage(
      @fs.read_file_to_bytes(base + "new-version/libdemo.so.1"),
    )
    assert_eq(old.version_defs[1].index, newer.version_defs[1].index)
    assert_eq(old.version_defs[1].name, b"DEMO_1")
    assert_eq(newer.version_defs[1].name, b"DEMO_2")
    assert_true(
      old.symbols.any(symbol => {
        symbol.lookupable && symbol.name == b"api" && symbol.section != 0
      }),
    )
    let folder = "fixtures/generated/u1/\{arch}/fixed/root/"
    let libc = @elf_adapter.read_linkage(
      @fs.read_file_to_bytes(folder + "lib/libc.so.6"),
    )
    assert_true(libc.version_defs.any(def => def.name == b"GLIBC_2.34"))
  }
}
