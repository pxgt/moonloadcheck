///|
test "saved comparisons roundtrip introduction existing failure and repair" {
  let before = impact_fixture("x86_64", "before")
  let after = impact_fixture("x86_64", "after")
  for (old, current) in [(before, after), (after, after), (after, before)] {
    let original = @analysis.compare(old, current, [
      b"/opt/demo/app", b"/opt/demo/stable-app",
    ])
    let saved = @analysis.read_impact_report(original.to_json().stringify())
    assert_eq(saved.to_json(), original.to_json())
    assert_eq(saved.exit_code(), original.exit_code())
  }
}

///|
test "saved comparisons reject forged classifications nested verdicts and identities" {
  let original = @analysis.compare(
    impact_fixture("x86_64", "before"),
    impact_fixture("x86_64", "after"),
    [b"/opt/demo/app"],
  )
  let entry = original.entries[0]
  let change = entry.changes[0]
  let invalid_entries : Array[@analysis.ImpactEntry] = [
    { ..entry, changes: [{ ..change, classification: "resolved", }], },
    { ..entry, changes: [], },
    { ..entry, changes: [change, change], },
    { ..entry, snapshot_changed: false, },
    { ..entry, entry: { display: "/different", hex: "2f646966666572656e74", }, },
    { ..entry, after: { ..entry.after, status: "pass_static", }, },
    { ..entry, before: { ..entry.before, schema_version: 99, }, },
  ]
  let invalid_reports : Array[@analysis.ImpactReport] = [
    { ..original, status: "pass_static", },
    { ..original, schema_version: 99, },
    { ..original, entries: [], },
    { ..original, entries: [entry, entry], },
  ]
  for entry in invalid_entries {
    invalid_reports.push({ ..original, entries: [entry], })
  }
  for report in invalid_reports {
    try @analysis.read_impact_report(report.to_json().stringify()) catch {
      @analysis.ReportError(_) => ()
      error => fail("unexpected error: \{error}")
    } noraise {
      _ => fail("contradictory saved comparison accepted")
    }
  }
}
