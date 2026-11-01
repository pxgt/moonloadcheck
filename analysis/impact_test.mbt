///|
fn impact_fixture(arch : String, view : String) -> @snapshot.Snapshot raise {
  let folder = "fixtures/generated/u3/\{arch}/\{view}/snapshot/"
  @snapshot.load(@fs.read_file_to_string(folder + "manifest.json"), digest => {
    @fs.read_file_to_bytes(folder + "blobs/" + digest)
  })
}

///|
test "U3 separates impacted consumer, existing failure and repair" {
  for arch in ["x86_64", "aarch64"] {
    let before = impact_fixture(arch, "before")
    let after = impact_fixture(arch, "after")
    let entries = [b"/opt/demo/app", b"/opt/demo/stable-app"]
    let impact = @analysis.compare(before, after, entries)
    assert_eq(impact.status, "fail")
    assert_eq(impact.exit_code(), 1)
    assert_true(
      impact.entries.all(e => !e.application_changed && e.snapshot_changed),
    )
    assert_eq(impact.entries[0].changes.length(), 1)
    assert_eq(impact.entries[0].changes[0].classification, "introduced")
    assert_eq(
      impact.entries[0].changes[0].after.unwrap().requirement.unwrap().display,
      "api",
    )
    assert_eq(impact.entries[1].after.status, "pass_static")
    assert_true(impact.entries[1].changes.is_empty())
    let same = @analysis.compare(after, after, entries)
    assert_eq(same.entries[0].changes[0].classification, "existing")
    assert_false(same.entries[0].snapshot_changed)
    let repaired = @analysis.compare(after, before, entries)
    assert_eq(repaired.status, "pass_static")
    assert_eq(repaired.entries[0].changes[0].classification, "resolved")
  }
}

///|
test "incomplete baseline cannot establish newly introduced failure" {
  let folder = "fixtures/generated/u3/x86_64/before/snapshot/"
  let text = @fs.read_file_to_string(folder + "manifest.json").replace(
    old="\"cache_mode\": \"disabled\"",
    new="\"cache_mode\": \"enabled\"",
  )
  let unknown = @snapshot.load(text, digest => {
    @fs.read_file_to_bytes(folder + "blobs/" + digest)
  })
  let report = @analysis.compare(unknown, impact_fixture("x86_64", "after"), [
    b"/opt/demo/app",
  ])
  assert_eq(report.entries[0].before.status, "inconclusive")
  assert_true(
    report.entries[0].changes.all(change => {
      change.classification == "indeterminate"
    }),
  )
  let changed = @analysis.compare(
    runtime_fixture("x86_64", "baseline"),
    runtime_fixture("x86_64", "unused-export-removed"),
    [b"/opt/demo/app"],
  )
  assert_true(changed.entries[0].application_changed)
}

///|
test "offline explain roundtrips stable finding evidence without a snapshot" {
  let report = @analysis.check_compatibility(
    runtime_fixture("x86_64", "used-export-removed"),
    b"/opt/demo/app",
  )
  let text = report.to_json().stringify()
  let restored = @analysis.read_report(text)
  assert_eq(restored.to_json().stringify(), text)
  let finding = restored.explain(report.findings[0].id)
  assert_eq(
    finding.to_json().stringify(),
    report.findings[0].to_json().stringify(),
  )
  try restored.explain("absent") catch {
    @analysis.ReportError(_) => ()
  } noraise {
    _ => fail("missing finding accepted")
  }
  try
    @analysis.read_report(
      text.replace(old="\"schema_version\":2", new="\"schema_version\":99"),
    )
  catch {
    @analysis.ReportError(_) => ()
    error => fail("unexpected error: \{error}")
  } noraise {
    _ => fail("unknown report schema accepted")
  }
  let before = impact_fixture("x86_64", "before")
  let after = impact_fixture("x86_64", "after")
  try @analysis.compare(before, after, []) catch {
    @analysis.ReportError(_) => ()
    error => fail("unexpected error: \{error}")
  } noraise {
    _ => fail("empty consumer set accepted")
  }
}
