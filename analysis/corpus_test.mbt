///|
fn corpus(arch : String, view : String) -> @snapshot.Snapshot raise {
  let folder = "fixtures/generated/corpus/\{arch}/\{view}/snapshot/"
  @snapshot.load(@fs.read_file_to_string(folder + "manifest.json"), digest => {
    @fs.read_file_to_bytes(folder + "blobs/" + digest)
  })
}

///|
test "pinned real applications agree with both distribution loaders" {
  for arch in ["amd64", "arm64"] {
    for
      view in [
        "jammy-on-jammy", "noble-on-noble", "jammy-on-noble", "noble-on-jammy",
      ] {
      let target = corpus(arch, view)
      for app in ["hello", "jq", "zstd"] {
        let report = @analysis.check_compatibility(
          target,
          @utf8.encode("/usr/bin/" + app),
        )
        let broken = view == "noble-on-jammy" && app != "zstd"
        assert_eq(
          report.status,
          if broken {
            "fail"
          } else {
            "pass_static"
          },
          msg=arch + ":" + view + ":" + app,
        )
        if broken {
          assert_true(
            report.findings.any(f => {
              f.code == "MLC004" &&
              f.version is Some(v) &&
              v.display == "GLIBC_2.38"
            }),
          )
          if app == "jq" {
            assert_true(
              report.findings.any(f => {
                f.code == "MLC005" &&
                f.requirement is Some(v) &&
                v.display == "jq_set_stderr_cb"
              }),
            )
          }
        }
      }
    }
  }
}

///|
test "real environment downgrade identifies impacted consumers without changing programs" {
  for arch in ["amd64", "arm64"] {
    let impact = @analysis.compare(
      corpus(arch, "noble-on-noble"),
      corpus(arch, "noble-on-jammy"),
      [b"/usr/bin/hello", b"/usr/bin/jq", b"/usr/bin/zstd"],
    )
    assert_eq(impact.status, "fail")
    assert_true(impact.entries.all(e => !e.application_changed))
    assert_true(
      impact.entries[0].changes.all(c => c.classification == "introduced"),
    )
    assert_true(
      impact.entries[1].changes.all(c => c.classification == "introduced"),
    )
    assert_eq(impact.entries[2].after.status, "pass_static")
    assert_true(impact.entries[2].changes.is_empty())
  }
}
