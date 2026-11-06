///|
fn recorded_report() -> String raise {
  @fs.read_file_to_string("fixtures/reports/schema-2.json")
}

///|
test "recorded schema 2 retains optional-field and UInt64 string compatibility" {
  let report = @analysis.read_report(recorded_report())
  assert_eq(report.exit_code(), 1)
  assert_true(report.symbol_checks[0].copy_source_size is None)
  assert_true(report.symbol_checks[0].copy_destination_size is None)
  let saved = @analysis.read_report(report.to_json().stringify())
  assert_eq(saved.explain("serialization-fixture-id").reference_offsets, [
    "18446744073709551615",
  ])
  let extended = recorded_report().replace(
    old="\"schema_version\": 2,",
    new="\"schema_version\": 2, \"future_optional_evidence\": true,",
  )
  assert_eq(@analysis.read_report(extended).exit_code(), 1)
}

///|
test "old and future schemas are rejected before current report field decoding" {
  for version in [1, 3, 999] {
    try @analysis.read_report("{\"schema_version\":\{version}}") catch {
      @analysis.ReportError(message) =>
        assert_eq(message, "unsupported report schema")
      _ => fail("schema was decoded as a current report")
    } noraise {
      _ => fail("unsupported schema accepted")
    }
  }
}

///|
test "saved reports reject ambiguous identities and contradictory verdicts" {
  let original = recorded_report()
  for
    (source, replacement, expected) in [
      (
        "\"status\": \"fail\"", "\"status\": \"pass_static\"", "report status conflicts with its findings",
      ),
      ("serialization-fixture-id", "", "empty finding id"),
    ] {
    try
      @analysis.read_report(original.replace(old=source, new=replacement))
    catch {
      @analysis.ReportError(message) => assert_eq(message, expected)
      _ => fail("wrong report validation error")
    } noraise {
      _ => fail("invalid saved report accepted")
    }
  }
  let report = @analysis.read_report(original)
  let invalid : @analysis.Report = {
    ..report,
    findings: [{ ..report.findings[0], status: "pass", }],
  }
  try @analysis.read_report(invalid.to_json().stringify()) catch {
    @analysis.ReportError(message) =>
      assert_eq(message, "invalid finding status")
    _ => fail("wrong finding status error")
  } noraise {
    _ => fail("invalid finding status accepted")
  }
  let altered : @analysis.Report = { ..report, status: "pass_static", }
  try @analysis.read_report(altered.to_json().stringify()) catch {
    @analysis.ReportError(message) =>
      assert_eq(message, "report status conflicts with its findings")
    _ => fail("wrong verdict conflict error")
  } noraise {
    _ => fail("contradictory saved report accepted")
  }
}
