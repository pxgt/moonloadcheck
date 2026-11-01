///|
fn fixture(arch : String, case : String) -> @snapshot.Snapshot raise {
  let folder = "fixtures/generated/u1/\{arch}/\{case}/snapshot/"
  @snapshot.load(@fs.read_file_to_string(folder + "manifest.json"), digest => {
    @fs.read_file_to_bytes(folder + "blobs/" + digest)
  })
}

///|
fn changed(
  change : (@snapshot.Manifest) -> @snapshot.Manifest,
) -> @snapshot.Snapshot raise {
  let folder = "fixtures/generated/u1/x86_64/fixed/snapshot/"
  let source : @snapshot.Manifest = @json.from_json(
    @json.parse(@fs.read_file_to_string(folder + "manifest.json")[:]),
  )
  @snapshot.load(change(source).to_json().stringify(), digest => {
    @fs.read_file_to_bytes(folder + "blobs/" + digest)
  })
}

///|
test "missing interpreter, wrong machine and unmodeled cache have distinct outcomes" {
  let snapshot = changed(source => {
    ..source,
    entries: source.entries.filter(item => {
      item.path_hex != source.profile.loader_path_hex
    }),
  })
  let report = @analysis.check_dependencies(
    snapshot, b"/opt/relocated-demo/app",
  )
  assert_eq(report.status, "fail")
  assert_true(report.findings.any(item => item.code == "MLC001"))
  let snapshot = changed(source => {
    ..source,
    profile: { ..source.profile, machine: 183, },
  })
  let report = @analysis.check_dependencies(
    snapshot, b"/opt/relocated-demo/app",
  )
  assert_eq(report.status, "fail")
  assert_eq(report.findings[0].code, "MLC003")
  let snapshot = changed(source => {
    ..source,
    profile: { ..source.profile, cache_mode: "enabled", },
  })
  let report = @analysis.check_dependencies(
    snapshot, b"/opt/relocated-demo/app",
  )
  assert_eq(report.status, "inconclusive")
  assert_eq(report.exit_code(), 2)
  assert_eq(report.findings[0].code, "MLC007")
  assert_eq(report.edges.length(), 0)
}

///|
test "missing entry is input_error, not a passing empty graph" {
  let report = @analysis.check_dependencies(
    fixture("x86_64", "fixed"),
    b"/absent",
  )
  assert_eq(report.status, "input_error")
  assert_eq(report.exit_code(), 3)
}

///|
test "loader skips foreign machine but terminates on a directory or PIE candidate" {
  for arch in ["x86_64", "aarch64"] {
    let report = @analysis.check_dependencies(
      fixture(arch, "wrong-machine-first"),
      b"/opt/relocated-demo/app",
    )
    assert_eq(report.status, "pass_static")
    assert_true(
      report.edges.any(edge => {
        edge.trace.any(candidate => candidate.outcome == "wrong_machine")
      }),
    )
    for case in ["directory-first", "pie-first"] {
      let report = @analysis.check_dependencies(
        fixture(arch, case),
        b"/opt/relocated-demo/app",
      )
      assert_eq(report.status, "fail")
      assert_eq(report.findings[0].code, "MLC002")
      assert_true(report.edges[0].selected is None)
      assert_eq(report.edges[0].trace.length(), 1)
    }
  }
}

///|
test "DSO ORIGIN follows the load pathname while identity follows the symlink target" {
  for arch in ["x86_64", "aarch64"] {
    let report = @analysis.check_dependencies(
      fixture(arch, "symlink-origin"),
      b"/opt/relocated-demo/app",
    )
    assert_eq(report.status, "pass_static")
    assert_true(
      report.objects.any(item => item.path.display == "/store/libmiddle.so.1"),
    )
    assert_true(
      report.edges.any(edge => {
        edge.consumer.display == "/store/libmiddle.so.1" &&
        edge.selected is Some(selected) &&
        selected.display == "/opt/relocated-demo/lib/libleaf.so.1"
      }),
    )
  }
}

///|
test "U1 diagnoses indirect RUNPATH failure and passes both tested fixes" {
  for arch in ["x86_64", "aarch64"] {
    let failed = @analysis.check_dependencies(
      fixture(arch, "runpath"),
      b"/opt/relocated-demo/app",
    )
    assert_eq(failed.status, "fail")
    assert_eq(failed.findings.length(), 1)
    let finding = failed.findings[0]
    assert_eq(finding.code, "MLC002")
    assert_eq(finding.requirement.unwrap().display, "libleaf.so.1")
    assert_eq(finding.dependency_chain.length(), 2)
    assert_eq(
      finding.dependency_chain[1].display,
      "/opt/relocated-demo/lib/libmiddle.so.1",
    )
    for edge in failed.edges {
      if edge.needed.display == "libleaf.so.1" {
        assert_true(edge.selected is None)
        assert_false(edge.trace.any(candidate => candidate.source == "RUNPATH"))
      }
    }
    for case in ["rpath", "fixed"] {
      let report = @analysis.check_dependencies(
        fixture(arch, case),
        b"/opt/relocated-demo/app",
      )
      assert_eq(report.status, "pass_static")
      assert_eq(report.objects.length(), 5)
      assert_eq(report.findings.length(), 0)
      assert_eq(report.exit_code(), 0)
      assert_true(report.not_checked.contains("symbol-versions"))
      assert_eq(
        report.to_json().stringify(),
        @analysis.check_dependencies(
          fixture(arch, case),
          b"/opt/relocated-demo/app",
        )
        .to_json()
        .stringify(),
      )
    }
  }
}
