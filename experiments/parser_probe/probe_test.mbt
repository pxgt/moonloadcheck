///|
test "ordinary and stripped objects retain version requirements" {
  let ordinary = @parser_probe.observe(
    @fs.read_file_to_bytes("fixtures/generated/x86_64/app"),
  )
  let stripped = @parser_probe.observe(
    @fs.read_file_to_bytes("fixtures/generated/x86_64/app.stripped"),
  )
  assert_eq(ordinary.machine, 62)
  assert_true(ordinary.dynamic_entries > 0)
  assert_true(ordinary.dynamic_symbols is Some(n) && n > 0)
  assert_true(ordinary.version_requirements.contains("libdemo.so.1:DEMO_1"))
  assert_eq(ordinary.dynamic_symbols, stripped.dynamic_symbols)
  assert_eq(ordinary.version_requirements, stripped.version_requirements)
}

///|
test "sectionless upstream gap is observable, not success" {
  let observed = @parser_probe.observe(
    @fs.read_file_to_bytes("fixtures/generated/x86_64/app.sectionless"),
  )
  assert_true(!observed.has_sections)
  assert_true(observed.dynamic_entries > 0)
  assert_eq(observed.dynamic_symbols, None)
  assert_eq(observed.version_requirements.length(), 0)
}

///|
test "truncated input returns an error" {
  let data = @fs.read_file_to_bytes("fixtures/generated/x86_64/app.truncated")
  let rejected = try {
    ignore(@parser_probe.observe(data))
    false
  } catch {
    _ => true
  }
  assert_true(rejected)
}
