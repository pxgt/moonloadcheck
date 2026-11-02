///|
struct ReadelfObject {
  path : String
  machine : Int32
  object_type : Int32
  interpreter : String?
  needed : Array[String]
  soname : String?
  rpath : String?
  runpath : String?
  pie : Bool
  no_default_lib : Bool
} derive(@json.FromJson)

///|
test "runtime fields match independent readelf output for PIE, EXEC and DSO" {
  let objects : Array[ReadelfObject] = @json.from_json(
    @json.parse(
      @fs.read_file_to_string(
        "fixtures/generated/linkage-edges/readelf-objects.json",
      )[:],
    ),
  )
  assert_eq(objects.length(), 120)
  for expected in objects {
    let actual = @elf_adapter.read(@fs.read_file_to_bytes(expected.path))
    assert_eq(actual.machine, expected.machine, msg=expected.path)
    assert_eq(actual.object_type, expected.object_type)
    assert_eq(
      actual.interpreter,
      expected.interpreter.map(s => @utf8.encode(s)),
    )
    assert_eq(actual.needed, expected.needed.map(s => @utf8.encode(s)))
    assert_eq(actual.soname, expected.soname.map(s => @utf8.encode(s)))
    assert_eq(actual.rpath, expected.rpath.map(s => @utf8.encode(s)))
    assert_eq(actual.runpath, expected.runpath.map(s => @utf8.encode(s)))
    assert_eq(actual.pie, expected.pie)
    assert_eq(actual.no_default_lib, expected.no_default_lib)
    assert_true(actual.unsupported.is_empty())
  }
}

///|
struct ParserEdge {
  path : String
  original : String
  table : String
  valid : Bool
  table_address : String
} derive(@json.FromJson)

///|
test "exact mapped table boundaries accept controls and reject incomplete final records" {
  let cases : Array[ParserEdge] = @json.from_json(
    @json.parse(
      @fs.read_file_to_string("fixtures/generated/parser-edges/cases.json")[:],
    ),
  )
  assert_eq(cases.length(), 36)
  assert_eq(cases.filter(c => c.valid).length(), 12)
  for case in cases {
    let bytes = @fs.read_file_to_bytes(case.path)
    if case.valid {
      let actual = @elf_adapter.read_linkage(bytes)
      let original = @elf_adapter.read_linkage(
        @fs.read_file_to_bytes(case.original),
      )
      assert_true(actual.object == original.object)
      assert_eq(actual.symbols.length(), original.symbols.length())
      assert_eq(
        actual.symbols.map(s => s.name),
        original.symbols.map(s => s.name),
      )
      assert_eq(actual.references.length(), original.references.length())
      assert_eq(
        actual.version_needs.map(v => v.name),
        original.version_needs.map(v => v.name),
      )
      assert_eq(
        actual.version_defs.map(v => v.name),
        original.version_defs.map(v => v.name),
      )
      if case.table == "gnu" || case.table == "sysv" {
        assert_true(actual.lookup_order.contains(actual.symbols.length() - 1))
      }
    } else {
      try @elf_adapter.read_linkage(bytes) catch {
        @model.ElfError::Malformed(message) =>
          assert_true(
            message.contains("address=" + case.table_address),
            msg=message,
          )
        _ => fail("incorrect boundary error: " + case.path)
      } noraise {
        _ => fail("incomplete runtime table accepted: " + case.path)
      }
    }
  }
}
