///|
test "pinned loaders follow runtime hash order for same-object version fallback" {
  for arch in ["amd64", "arm64"] {
    for suite in ["jammy", "noble"] {
      for style in ["gnu", "sysv"] {
        let folder = "fixtures/generated/fallback/\{arch}/\{suite}/\{style}/snapshot/"
        let target = @snapshot.load(
          @fs.read_file_to_string(folder + "manifest.json"),
          digest => @fs.read_file_to_bytes(folder + "blobs/" + digest),
        )
        let report = @analysis.check_compatibility(target, b"/app")
        assert_eq(report.status, "pass_static")
        assert_true(
          report.symbol_checks.any(check => {
            check.consumer.display == "/app" &&
            check.symbol.display == "api" &&
            check.version.map(v => v.display) == Some("SELECT_2") &&
            check.definition_version is None
          }),
        )
      }
    }
  }
}
