///|
fn copy_snapshot(
  arch : String,
  suite : String,
  case : String,
) -> @snapshot.Snapshot raise {
  let folder = "fixtures/generated/copy/\{arch}/\{suite}/\{case}/snapshot/"
  @snapshot.load(@fs.read_file_to_string(folder + "manifest.json"), digest => {
    @fs.read_file_to_bytes(folder + "blobs/" + digest)
  })
}

///|
test "COPY source lookup excludes executable while ordinary DSO references use its copy" {
  for arch in ["amd64", "arm64"] {
    for suite in ["jammy", "noble"] {
      for case in ["equal", "pie", "weak-first", "strong-first", "weak-missing"] {
        let report = @analysis.check_compatibility(
          copy_snapshot(arch, suite, case),
          b"/app",
        )
        assert_eq(
          report.status,
          "pass_static",
          msg=arch + ":" + suite + ":" + case + report.to_json().stringify(),
        )
        let copies = report.symbol_checks.filter(c => {
          c.lookup_policy == "copy-source-excluding-executable"
        })
        if arch == "arm64" && case == "pie" {
          assert_true(copies.is_empty())
          assert_true(
            report.symbol_checks.any(c => {
              c.consumer.display == "/app" &&
              c.symbol.display == "data" &&
              c.provider.map(p => p.display) == Some("/runtime/libcopy.so.1") &&
              c.relocation_types.contains(1025)
            }),
          )
          continue
        }
        assert_eq(copies.length(), 1)
        let copy = copies[0]
        assert_eq(copy.consumer.display, "/app")
        assert_eq(copy.symbol.display, "data")
        assert_eq(copy.version.map(v => v.display), Some("COPY_2"))
        assert_eq(copy.copy_destination_size, Some("16"))
        if case == "weak-missing" {
          assert_true(copy.weak)
          assert_true(copy.provider is None)
          assert_eq(copy.copy_source_size, None)
        } else {
          assert_eq(
            copy.provider.map(p => p.display),
            Some(
              if case == "strong-first" {
                "/runtime/libsecond.so.1"
              } else {
                "/runtime/libcopy.so.1"
              },
            ),
          )
          assert_eq(copy.copy_source_size, Some("16"))
          assert_true(
            report.symbol_checks.any(c => {
              c.consumer.display == "/runtime/libcopy.so.1" &&
              c.symbol.display == "data" &&
              c.provider.map(p => p.display) == Some("/app") &&
              c.lookup_policy == "startup-global-scope" &&
              c.status == "pass"
            }),
          )
        }
      }
    }
  }
}

///|
test "COPY missing versioned data fails and size or protected combinations retain unknown" {
  for arch in ["amd64", "arm64"] {
    for suite in ["jammy", "noble"] {
      for case in ["missing", "wrong-version", "smaller", "larger", "protected"] {
        let report = @analysis.check_compatibility(
          copy_snapshot(arch, suite, case),
          b"/app",
        )
        let fails = case == "missing" || case == "wrong-version"
        assert_eq(
          report.status,
          if fails {
            "fail"
          } else {
            "inconclusive"
          },
          msg=arch + ":" + suite + ":" + case,
        )
        assert_true(
          report.findings.any(f => {
            f.code == (if fails { "MLC005" } else { "MLC008" }) &&
            f.requirement.map(v => v.display) == Some("data")
          }),
        )
        let copies = report.symbol_checks.filter(c => {
          c.lookup_policy == "copy-source-excluding-executable"
        })
        assert_eq(copies.length(), 1)
        assert_eq(copies[0].status, if fails { "fail" } else { "unknown" })
        if case == "smaller" || case == "larger" {
          assert_eq(
            copies[0].copy_source_size,
            Some(if case == "smaller" { "8" } else { "32" }),
          )
          assert_eq(copies[0].copy_destination_size, Some("16"))
        }
      }
    }
  }
}

///|
test "schema 2 reports without additive COPY size fields still decode" {
  let report = @analysis.check_compatibility(
    copy_snapshot("amd64", "jammy", "equal"),
    b"/app",
  )
  let text = report
    .to_json()
    .stringify()
    .replace(old=",\"copy_destination_size\":\"16\"", new="")
    .replace(old=",\"copy_source_size\":\"16\"", new="")
  let old = @analysis.read_report(text)
  assert_true(
    old.symbol_checks.all(c => {
      c.copy_source_size is None && c.copy_destination_size is None
    }),
  )
  assert_eq(old.status, "pass_static")
}
