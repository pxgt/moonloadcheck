///|
test "cache order, stale selected path and NODEFLIB match isolated loaders" {
  for arch in ["x86_64", "aarch64"] {
    for
      (case, expected) in [
        ("preferred", "/preferred/libchoice.so.1"),
        ("disabled", "/lib/libchoice.so.1"),
        ("stale-first", "/lib/libchoice.so.1"),
        ("nodeflib-allowed", "/preferred/libchoice.so.1"),
        ("nodeflib-filtered", ""),
      ] {
      let folder = "fixtures/generated/cache/\{arch}/\{case}/snapshot/"
      let snapshot = @snapshot.load(
        @fs.read_file_to_string(folder + "manifest.json"),
        digest => @fs.read_file_to_bytes(folder + "blobs/" + digest),
      )
      let report = @analysis.check_dependencies(snapshot, b"/app")
      if expected == "" {
        assert_eq(report.status, "fail")
        assert_true(report.edges[0].selected is None)
        assert_true(
          report.edges[0].trace.any(item => item.source == "cache_nodeflib"),
        )
      } else {
        assert_eq(report.status, "pass_static")
        assert_eq(report.edges[0].selected.unwrap().display, expected)
      }
    }
  }
}
