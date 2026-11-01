///|
test "LIB and PLATFORM are measured target facts, never host guesses" {
  for arch in ["x86_64", "aarch64"] {
    for
      (view, expected) in [
        ("snapshot", "pass_static"),
        ("unknown-snapshot", "inconclusive"),
      ] {
      let folder = "fixtures/generated/tokens/\{arch}/\{view}/"
      let snapshot = @snapshot.load(
        @fs.read_file_to_string(folder + "manifest.json"),
        digest => @fs.read_file_to_bytes(folder + "blobs/" + digest),
      )
      let report = @analysis.check_compatibility(snapshot, b"/opt/demo/app")
      assert_eq(report.status, expected)
      if expected == "pass_static" {
        let path = "/opt/demo/" +
          @utf8.decode(
            @hex.decode(snapshot.profile().lib_token_hex.unwrap()[:]),
          ) +
          "/" +
          @utf8.decode(
            @hex.decode(snapshot.profile().platform_token_hex.unwrap()[:]),
          ) +
          "/libchoice.so.1"
        assert_true(
          report.edges.any(edge => {
            edge.needed.display == "libchoice.so.1" &&
            edge.selected is Some(selected) &&
            selected.display == path
          }),
        )
      }
    }
  }
}
