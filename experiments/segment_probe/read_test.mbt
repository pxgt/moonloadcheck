///|
test "runtime metadata survives removal of section headers on both architectures" {
  for (architecture, machine) in [("x86_64", 62), ("aarch64", 183)] {
    let prefix = "fixtures/generated/" + architecture + "/"
    let normal = @segment_probe.read(@fs.read_file_to_bytes(prefix + "app"))
    let stripped = @segment_probe.read(
      @fs.read_file_to_bytes(prefix + "app.stripped"),
    )
    let sectionless = @segment_probe.read(
      @fs.read_file_to_bytes(prefix + "app.sectionless"),
    )
    assert_eq(normal.machine, machine)
    assert_true(normal.needed.contains(b"libdemo.so.1"))
    assert_true(normal.symbol_names.contains(b"api"))
    assert_true(normal.required_versions.contains(b"DEMO_1"))
    assert_true(normal == stripped)
    assert_true(normal == sectionless)
  }
}

///|
test "different requested version is observable" {
  let object = @segment_probe.read(
    @fs.read_file_to_bytes("fixtures/generated/x86_64/version-app"),
  )
  assert_true(object.required_versions.contains(b"DEMO_2"))
  assert_true(!object.required_versions.contains(b"DEMO_1"))
}

///|
test "truncated runtime metadata is rejected" {
  let rejected = try {
    ignore(
      @segment_probe.read(
        @fs.read_file_to_bytes("fixtures/generated/x86_64/app.truncated"),
      ),
    )
    false
  } catch {
    _ => true
  }
  assert_true(rejected)
}
