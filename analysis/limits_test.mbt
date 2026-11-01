///|
test "real dependency step exhaustion retains an earlier missing-library failure" {
  let folder = "fixtures/generated/limits/dependency-steps/snapshot/"
  let target = @snapshot.load(
    @fs.read_file_to_string(folder + "manifest.json"),
    digest => @fs.read_file_to_bytes(folder + "blobs/" + digest),
  )
  let report = @analysis.check_dependencies(target, b"/app")
  assert_eq(report.status, "fail")
  assert_eq(report.exit_code(), 1)
  assert_true(
    report.findings.any(f => {
      f.code == "MLC002" &&
      f.status == "fail" &&
      f.requirement.map(n => n.display) == Some("libapi.so.1")
    }),
  )
  assert_true(
    report.findings.any(f => f.code == "MLC009" && f.status == "unknown"),
  )
  assert_true(report.edges.length() > 16000 && report.edges.length() <= 16384)
}
