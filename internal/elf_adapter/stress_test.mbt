///|
struct StressCase {
  architecture : String
  case : String
  expected_code : Int32
  sha256 : String
} derive(@json.FromJson)

///|
fn stress_cases() -> Array[StressCase] raise {
  @json.from_json(
    @json.parse(
      @fs.read_file_to_string("fixtures/generated/stress/oracle.json")[:],
    ),
  )
}

///|
fn stress_bytes(row : StressCase) -> Bytes raise {
  @fs.read_file_to_bytes(
    "fixtures/generated/stress/\{row.architecture}/\{row.case}/snapshot/blobs/\{row.sha256}",
  )
}

///|
test "out-of-range integers and overflowing mappings are rejected without panic" {
  let cases = stress_cases()
  assert_eq(cases.length(), 68)
  for row in cases {
    if row.expected_code == 3 {
      try @elf_adapter.read_linkage(stress_bytes(row)) catch {
        @model.ElfError::Malformed(message) =>
          if row.case == "virtual-memory-wrap" {
            assert_true(message.contains("virtual memory range overflows"))
          }
        _ => fail("wrong range error: \{row.case}")
      } noraise {
        _ => fail("accepted malformed range: \{row.case}")
      }
    }
  }
}

///|
test "actual production count limits distinguish admitted boundaries from resource limits" {
  for row in stress_cases() {
    if row.expected_code == 2 {
      try @elf_adapter.read_linkage(stress_bytes(row)) catch {
        @model.ElfError::ResourceLimit(_) => ()
        _ => fail("wrong count-limit error: \{row.case}")
      } noraise {
        _ => fail("accepted over-budget count: \{row.case}")
      }
    } else if row.expected_code == 0 {
      let linkage = @elf_adapter.read_linkage(stress_bytes(row))
      assert_eq(
        linkage.object.machine,
        if row.architecture == "amd64" {
          62
        } else {
          183
        },
      )
      if row.case == "relocations-500000" {
        assert_eq(linkage.references.length(), 500000)
        assert_true(
          linkage.references.all(r => r.symbol_index == 0 && r.relocation == 0),
        )
      }
    }
  }
}
