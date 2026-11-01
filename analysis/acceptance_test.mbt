///|
test "RUNPATH is not inherited by indirect dependencies" {
  assert_eq(
    @analysis.check_dependencies(
      fixture("x86_64", "runpath"),
      b"/opt/relocated-demo/app",
    ).status,
    "fail",
  )
}

///|
test "GNU version requirements are not replaced by bare symbol names" {
  let report = @analysis.check_compatibility(
    runtime_fixture("x86_64", "old-environment"),
    b"/opt/demo/app",
  )
  assert_eq(report.status, "fail")
  assert_true(report.findings.any(f => f.code == "MLC004"))
}

///|
test "a usable library present only on the host cannot repair the target snapshot" {
  let report = @analysis.check_compatibility(
    path_fixture("amd64", "jammy", "host-decoy"),
    b"/app",
  )
  assert_eq(report.status, "fail")
  assert_true(report.edges[0].selected is None)
}

///|
test "unknown target rules cannot become a static pass" {
  let unknown = changed(source => {
    ..source,
    profile: { ..source.profile, rule_revision: "unmodeled-loader", },
  })
  assert_eq(
    @analysis.check_dependencies(unknown, b"/opt/relocated-demo/app").status,
    "inconclusive",
  )
}

///|
test "export removal affects only consumers that require it" {
  let impact = @analysis.compare(
    impact_fixture("x86_64", "before"),
    impact_fixture("x86_64", "after"),
    [b"/opt/demo/app", b"/opt/demo/stable-app"],
  )
  assert_eq(impact.entries[0].after.status, "fail")
  assert_eq(impact.entries[1].after.status, "pass_static")
  assert_true(impact.entries[1].changes.is_empty())
}

///|
test "namespace order changes only the exact manifest digest, not semantic reports" {
  let folder = "fixtures/generated/paths/amd64/jammy/diamond/snapshot/"
  let source : @snapshot.Manifest = @json.from_json(
    @json.parse(@fs.read_file_to_string(folder + "manifest.json")[:]),
  )
  let reversed = []
  for i = source.entries.length() - 1; i >= 0; i = i - 1 {
    reversed.push(source.entries[i])
  }
  let reordered = @snapshot.load(
    { ..source, entries: reversed, }.to_json().stringify(),
    digest => @fs.read_file_to_bytes(folder + "blobs/" + digest),
  )
  let baseline = @analysis.check_compatibility(
    path_fixture("amd64", "jammy", "diamond"),
    b"/app",
  )
  let report = @analysis.check_compatibility(reordered, b"/app")
  assert_true(report.snapshot_sha256 != baseline.snapshot_sha256)
  assert_eq(
    { ..report, snapshot_sha256: baseline.snapshot_sha256, }
    .to_json()
    .stringify(),
    baseline.to_json().stringify(),
  )
}

///|
test "excluded profile modes stay unknown and changed-rule analyses do not contaminate later calls" {
  let original = fixture("x86_64", "fixed")
  let baseline = @analysis.check_compatibility(
      original, b"/opt/relocated-demo/app",
    )
    .to_json()
    .stringify()
  for mode in ["secure", "preload", "audit", "hwcaps", "loader", "revision"] {
    let target = changed(source => {
      ..source,
      profile: {
        ..source.profile,
        secure_execution: mode == "secure",
        preload: if mode == "preload" {
          ["/preload.so"]
        } else {
          []
        },
        audit: if mode == "audit" {
          ["/audit.so"]
        } else {
          []
        },
        hwcaps_policy: if mode == "hwcaps" {
          "unmodeled"
        } else {
          "none"
        },
        loader_family: if mode == "loader" {
          "musl"
        } else {
          "glibc"
        },
        rule_revision: if mode == "revision" {
          "unknown"
        } else {
          source.profile.rule_revision
        },
      },
    })
    let report = @analysis.check_compatibility(
      target, b"/opt/relocated-demo/app",
    )
    assert_eq(report.status, "inconclusive", msg=mode)
    assert_true(report.findings.any(f => f.code == "MLC007"))
    assert_eq(
      @analysis.check_compatibility(original, b"/opt/relocated-demo/app")
      .to_json()
      .stringify(),
      baseline,
    )
    let comparison = @analysis.compare(target, original, [
      b"/opt/relocated-demo/app",
    ])
    assert_eq(comparison.status, "inconclusive")
    assert_eq(comparison.entries[0].after.status, "pass_static")
    assert_true(
      comparison.entries[0].changes.all(c => c.classification == "indeterminate"),
    )
  }
}
