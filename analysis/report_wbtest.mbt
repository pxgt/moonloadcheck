///|
test "split lookup diagnostics merge evidence and resource gaps do not erase failures" {
  let report : Report = {
    schema_version: 2,
    tool_version: "test",
    rule_revision: "test",
    snapshot_sha256: "test",
    entry: name(b"/app"),
    checked_scope: [],
    not_checked: [],
    status: "inconclusive",
    objects: [],
    edges: [],
    findings: [],
    version_checks: [],
    symbol_checks: [],
    symbol_scope: [],
  }
  issue(
    report,
    "MLC008",
    "unknown",
    b"/app",
    Some(b"data"),
    [],
    "COPY uncertainty",
    "Review copy",
    provider=b"/lib.so",
    offsets=["64"],
  )
  issue(
    report,
    "MLC008",
    "unknown",
    b"/app",
    Some(b"data"),
    [],
    "Other reference uncertainty",
    "Review reference",
    provider=b"/app",
    offsets=["64", "80"],
  )
  issue(
    report,
    "MLC005",
    "fail",
    b"/app",
    Some(b"missing"),
    [],
    "Missing definition",
    "Replace library",
  )
  issue(
    report,
    "MLC009",
    "unknown",
    b"/app",
    None,
    [],
    "Resource limit",
    "Reduce input",
  )
  let finished = finish(report)
  assert_eq(finished.status, "fail")
  assert_eq(finished.findings.length(), 3)
  let merged = finished.explain(finished.findings[0].id)
  assert_eq(merged.reference_offsets, ["64", "80"])
  assert_true(merged.provider is None)
  assert_eq(merged.explanation, "COPY uncertainty\nOther reference uncertainty")
  assert_true(
    finished.findings.any(f => f.code == "MLC005" && f.status == "fail"),
  )
  assert_true(
    finished.findings.any(f => f.code == "MLC009" && f.status == "unknown"),
  )
  finished.findings.push(merged)
  try read_report(finished.to_json().stringify()) catch {
    ReportError(_) => ()
    _ => fail("wrong duplicate-id error")
  } noraise {
    _ => fail("ambiguous report accepted")
  }
}
