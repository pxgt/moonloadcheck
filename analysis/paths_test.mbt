///|
fn path_fixture(
  arch : String,
  suite : String,
  case : String,
) -> @snapshot.Snapshot raise {
  let folder = "fixtures/generated/paths/\{arch}/\{suite}/\{case}/snapshot/"
  @snapshot.load(@fs.read_file_to_string(folder + "manifest.json"), digest => {
    @fs.read_file_to_bytes(folder + "blobs/" + digest)
  })
}

///|
test "slash dependencies, empty search elements and path precedence match loaders" {
  for arch in ["amd64", "arm64"] {
    for suite in ["jammy", "noble"] {
      for
        (case, expected) in [
          ("absolute-needed", "/libs/libapi.so.1"),
          ("relative-needed", "/libs/libapi.so.1"),
          ("empty-path", "/libapi.so.1"),
          ("rpath-first", "/preferred/libapi.so.1"),
          ("runpath-after-env", "/override/libapi.so.1"),
        ] {
        let report = @analysis.check_compatibility(
          path_fixture(arch, suite, case),
          b"/app",
        )
        assert_eq(
          report.status,
          "pass_static",
          msg=arch + ":" + suite + ":" + case,
        )
        assert_eq(report.edges[0].selected.map(n => n.display), Some(expected))
        if case == "absolute-needed" || case == "relative-needed" {
          assert_eq(report.edges[0].trace.length(), 1)
          assert_eq(report.edges[0].trace[0].source, "DT_NEEDED path")
        }
      }
    }
  }
}

///|
test "cycles terminate and diamonds reuse their shared dependency" {
  for arch in ["amd64", "arm64"] {
    for suite in ["jammy", "noble"] {
      for case in ["cycle", "diamond"] {
        let report = @analysis.check_compatibility(
          path_fixture(arch, suite, case),
          b"/app",
        )
        assert_eq(report.status, "pass_static")
        assert_eq(report.objects.length(), if case == "cycle" { 5 } else { 6 })
        assert_true(
          report.edges.any(e => {
            e.trace.any(t => {
              t.source == "already_loaded" && t.outcome == "reused"
            })
          }),
        )
        if case == "diamond" {
          assert_eq(
            report.edges
            .filter(e => e.needed.display == "libleaf.so.1")
            .length(),
            2,
          )
          assert_eq(
            report.objects
            .filter(o => o.path.display == "/runtime/libleaf.so.1")
            .length(),
            1,
          )
        } else {
          assert_true(
            report.edges.any(e => {
              e.consumer.display == "/runtime/libb.so.1" &&
              e.selected.map(n => n.display) == Some("/runtime/liba.so.1")
            }),
          )
        }
      }
    }
  }
}

///|
test "equal content and hardlinked aliases have different loader identities" {
  for arch in ["amd64", "arm64"] {
    for suite in ["jammy", "noble"] {
      for case in ["hardlink", "same-content"] {
        let report = @analysis.check_compatibility(
          path_fixture(arch, suite, case),
          b"/app",
        )
        assert_eq(report.status, "pass_static")
        let aliases = report.objects.filter(o => {
          o.path.display == "/aliases/libone.so.1" ||
          o.path.display == "/aliases/libtwo.so.1"
        })
        assert_eq(aliases.length(), if case == "hardlink" { 1 } else { 2 })
        if case == "same-content" {
          assert_eq(aliases[0].sha256, aliases[1].sha256)
          assert_true(aliases[0].file_id != aliases[1].file_id)
        }
      }
    }
  }
}

///|
test "missing or malformed first candidates never fall back to an unrelated usable library" {
  for arch in ["amd64", "arm64"] {
    for suite in ["jammy", "noble"] {
      for case in ["direct-missing", "corrupt-first", "host-decoy"] {
        let report = @analysis.check_dependencies(
          path_fixture(arch, suite, case),
          b"/app",
        )
        assert_eq(
          report.status,
          if case == "corrupt-first" {
            "input_error"
          } else {
            "fail"
          },
        )
        assert_true(
          report.findings.any(f => {
            f.code ==
            (if case == "corrupt-first" { "MLC006" } else { "MLC002" })
          }),
        )
        assert_true(report.edges[0].selected is None)
        if case == "corrupt-first" {
          assert_eq(report.edges[0].trace.length(), 1)
        }
      }
    }
  }
}

///|
test "changing only search order rechecks the selected provider and consumer impact" {
  for arch in ["amd64", "arm64"] {
    for suite in ["jammy", "noble"] {
      let good = path_fixture(arch, suite, "select-good")
      let bad = path_fixture(arch, suite, "select-bad")
      let impact = @analysis.compare(good, bad, [b"/app"])
      assert_eq(impact.status, "fail")
      let entry = impact.entries[0]
      assert_false(entry.application_changed)
      assert_eq(
        entry.before.edges[0].selected.map(n => n.display),
        Some("/good/libapi.so.1"),
      )
      assert_eq(
        entry.after.edges[0].selected.map(n => n.display),
        Some("/bad/libapi.so.1"),
      )
      assert_true(entry.changes.all(c => c.classification == "introduced"))
      assert_true(
        entry.after.findings.any(f => {
          f.code == "MLC004" && f.version.map(v => v.display) == Some("PATH_1")
        }),
      )
    }
  }
}
