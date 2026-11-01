///|
test "symbol scope agrees with weak, visibility, interposition and version oracles" {
  for arch in ["x86_64", "aarch64"] {
    for
      (case, consumer, provider, version) in [
        ("weak-first", "/opt/demo/app", "/runtime/libfirst.so.1", None),
        ("strong-first", "/opt/demo/app", "/runtime/libsecond.so.1", None),
        ("hidden-first", "/opt/demo/app", "/runtime/libsecond.so.1", None),
        (
          "main-interposition",
          "/runtime/libinterposed.so.1",
          "/opt/demo/app",
          None,
        ),
        (
          "unversioned-oldest",
          "/opt/demo/app",
          "/runtime/libversions.so.1",
          None,
        ),
        (
          "default-version",
          "/opt/demo/app",
          "/runtime/libversions.so.1",
          Some("SELECT_2"),
        ),
        (
          "explicit-old-version",
          "/opt/demo/app",
          "/runtime/libversions.so.1",
          Some("SELECT_1"),
        ),
        ("sysv-only", "/opt/demo/app", "/runtime/libversions.so.1", None),
      ] {
      let folder = "fixtures/generated/symbols/\{arch}/\{case}/snapshot/"
      let snapshot = @snapshot.load(
        @fs.read_file_to_string(folder + "manifest.json"),
        digest => @fs.read_file_to_bytes(folder + "blobs/" + digest),
      )
      let report = @analysis.check_compatibility(snapshot, b"/opt/demo/app")
      assert_eq(
        report.status,
        "pass_static",
        msg=case + ": " + report.to_json().stringify(),
      )
      assert_true(
        report.symbol_checks.any(check => {
          check.consumer.display == consumer &&
          check.symbol.display == "api" &&
          check.provider is Some(selected) &&
          selected.display == provider &&
          check.version.map(v => v.display) == version
        }),
      )
      if case == "unversioned-oldest" {
        assert_true(
          report.symbol_checks.any(check => {
            check.symbol.display == "api" &&
            check.definition_version is Some(v) &&
            v.display == "SELECT_1"
          }),
        )
      }
    }
  }
}
