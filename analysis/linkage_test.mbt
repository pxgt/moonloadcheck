///|
fn runtime_fixture(arch : String, case : String) -> @snapshot.Snapshot raise {
  let folder = "fixtures/generated/u2/\{arch}/\{case}/snapshot/"
  @snapshot.load(@fs.read_file_to_string(folder + "manifest.json"), digest => {
    @fs.read_file_to_bytes(folder + "blobs/" + digest)
  })
}

///|
test "version-node strength is independent of symbol binding and call usage" {
  for arch in ["x86_64", "aarch64"] {
    let report = @analysis.check_compatibility(
      runtime_fixture(arch, "weak-symbol"),
      b"/opt/demo/app",
    )
    assert_eq(report.status, "pass_static")
    assert_true(
      report.symbol_checks.any(check => {
        check.symbol.display == "optional" &&
        check.weak &&
        check.provider is None &&
        check.status == "pass"
      }),
    )
    let report = @analysis.check_compatibility(
      runtime_fixture(arch, "node-only"),
      b"/opt/demo/app",
    )
    assert_eq(report.status, "fail")
    assert_true(report.findings.any(finding => finding.code == "MLC004"))
    assert_false(report.findings.any(finding => finding.code == "MLC005"))
    let report = @analysis.check_compatibility(
      runtime_fixture(arch, "weak-node"),
      b"/opt/demo/app",
    )
    assert_eq(report.status, "pass_static")
    let report = @analysis.check_compatibility(
      runtime_fixture(arch, "weak-node-strong-symbol"),
      b"/opt/demo/app",
    )
    assert_eq(report.status, "fail")
    assert_true(report.findings.any(finding => finding.code == "MLC005"))
    assert_false(report.findings.any(finding => finding.code == "MLC004"))
  }
}

///|
test "U2 compares exact version nodes and actual relocation references" {
  for arch in ["x86_64", "aarch64"] {
    for
      case in [
        "baseline", "new-environment", "unused-export-removed", "unversioned-with-versions",
        "sectionless",
      ] {
      let report = @analysis.check_compatibility(
        runtime_fixture(arch, case),
        b"/opt/demo/app",
      )
      assert_eq(report.status, "pass_static", msg=report.to_json().stringify())
      assert_true(!report.symbol_checks.is_empty())
      assert_true(report.symbol_checks.all(check => check.status == "pass"))
    }
    let report = @analysis.check_compatibility(
      runtime_fixture(arch, "old-environment"),
      b"/opt/demo/app",
    )
    assert_eq(report.status, "fail")
    assert_true(
      report.findings.any(finding => {
        finding.code == "MLC004" &&
        finding.version is Some(version) &&
        version.display == "DEMO_2"
      }),
    )
    let report = @analysis.check_compatibility(
      runtime_fixture(arch, "used-export-removed"),
      b"/opt/demo/app",
    )
    assert_eq(report.status, "fail")
    assert_true(
      report.findings.any(finding => {
        finding.code == "MLC005" &&
        finding.requirement is Some(symbol) &&
        symbol.display == "api" &&
        !finding.reference_offsets.is_empty()
      }),
    )
    let report = @analysis.check_compatibility(
      runtime_fixture(arch, "unversioned-provider"),
      b"/opt/demo/app",
    )
    assert_eq(report.status, "fail")
    assert_true(report.findings.any(finding => finding.code == "MLC005"))
  }
}
