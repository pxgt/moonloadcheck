///|
fn maturity_snapshot(folder : String) -> @snapshot.Snapshot raise {
  @snapshot.load(@fs.read_file_to_string(folder + "/manifest.json"), digest => {
    @fs.read_file_to_bytes(folder + "/blobs/" + digest)
  })
}

///|
test "TLS type collisions retain the first actual provider and cannot pass" {
  for arch in ["amd64", "arm64"] {
    for suite in ["jammy", "noble"] {
      for
        (case, provider) in [
          ("tls-type-first", "/runtime/libfirst.so.1"),
          ("ordinary-to-tls", "/runtime/libprovider.so.1"),
        ] {
        let report = @analysis.check_compatibility(
          maturity_snapshot(
            "fixtures/generated/bindings/\{arch}/\{suite}/\{case}/snapshot",
          ),
          b"/app",
        )
        assert_eq(report.status, "inconclusive")
        let checks = report.symbol_checks.filter(c => {
          c.consumer.display == "/runtime/libclient.so.1" &&
          c.symbol.display == "slot"
        })
        assert_eq(checks.length(), 1)
        assert_eq(checks[0].status, "unknown")
        assert_eq(checks[0].provider.unwrap().display, provider)
        assert_true(
          report.findings.any(f => {
            f.code == "MLC008" && f.explanation.contains("TLS type mismatch")
          }),
        )
      }
    }
  }
}

///|
test "ordinary interposition and TLS checks stay distinct from excluded bindings" {
  for arch in ["amd64", "arm64"] {
    for suite in ["jammy", "noble"] {
      for
        (case, expected) in [
          ("interposition", "pass_static"),
          ("tls", "pass_static"),
          ("tls-missing", "fail"),
          ("unique", "inconclusive"),
          ("protected", "inconclusive"),
          ("symbolic", "inconclusive"),
        ] {
        let report = @analysis.check_compatibility(
          maturity_snapshot(
            "fixtures/generated/bindings/\{arch}/\{suite}/\{case}/snapshot",
          ),
          b"/app",
        )
        assert_eq(report.status, expected, msg=case)
        if case == "interposition" || case == "tls" {
          let check = report.symbol_checks.filter(c => {
              c.symbol.display == "slot"
            })[0]
          assert_eq(check.status, "pass")
          assert_eq(
            check.provider.unwrap().display,
            if case == "tls" {
              "/runtime/libprovider.so.1"
            } else {
              "/runtime/libfirst.so.1"
            },
          )
        } else if case == "tls-missing" {
          assert_true(
            report.symbol_checks.any(c => {
              c.symbol.display == "slot" &&
              c.status == "fail" &&
              c.provider is None
            }),
          )
        } else {
          assert_true(report.findings.any(f => f.code == "MLC008"))
        }
      }
    }
  }
}

///|
test "real GLIBCXX requirements detect a library-only downgrade with unchanged consumers" {
  for arch in ["amd64", "arm64"] {
    for app in ["modern", "stable"] {
      let entry = "/app/" + app
      let before = @analysis.check_compatibility(
        maturity_snapshot(
          "fixtures/generated/glibcxx/\{arch}/baseline/snapshot",
        ),
        @utf8.encode(entry),
      )
      let after = @analysis.check_compatibility(
        maturity_snapshot(
          "fixtures/generated/glibcxx/\{arch}/downgrade/snapshot",
        ),
        @utf8.encode(entry),
      )
      // Existing unvalidated bindings within the real libstdc++ remain unknown.
      assert_eq(before.status, "inconclusive")
      assert_eq(
        after.status,
        if app == "modern" {
          "fail"
        } else {
          "inconclusive"
        },
      )
      assert_eq(
        before.objects.filter(o => o.path.display == entry)[0].sha256,
        after.objects.filter(o => o.path.display == entry)[0].sha256,
      )
      let check = after.version_checks.filter(v => {
        v.consumer.display == entry && v.version.display == "GLIBCXX_3.4.32"
      })
      if app == "modern" {
        assert_eq(check.length(), 1)
        assert_eq(check[0].status, "fail")
        assert_eq(check[0].provider.unwrap().display, "/runtime/libstdc++.so.6")
        assert_true(
          before.version_checks.any(v => {
            v.consumer.display == entry &&
            v.version.display == "GLIBCXX_3.4.32" &&
            v.status == "pass"
          }),
        )
      } else {
        assert_true(check.is_empty())
      }
    }
  }
}

///|
test "higher GLIBCXX nodes and a surviving name string do not repair a missing requirement" {
  for arch in ["amd64", "arm64"] {
    let folder = "fixtures/generated/glibcxx/\{arch}/version-hole/"
    let provider = @elf.read_linkage(
      @fs.read_file_to_bytes(folder + "root/runtime/libstdc++.so.6"),
    )
    assert_true(provider.version_defs.any(v => v.name == b"GLIBCXX_3.4.33"))
    assert_false(provider.version_defs.any(v => v.name == b"GLIBCXX_3.4.32"))
    assert_true(provider.symbols.any(s => s.name == b"GLIBCXX_3.4.32"))
    let snapshot = maturity_snapshot(folder + "snapshot")
    let modern = @analysis.check_compatibility(snapshot, b"/app/modern")
    assert_eq(modern.status, "fail")
    assert_true(
      modern.version_checks.any(v => {
        v.consumer.display == "/app/modern" &&
        v.version.display == "GLIBCXX_3.4.32" &&
        v.status == "fail"
      }),
    )
    assert_eq(
      @analysis.check_compatibility(snapshot, b"/app/stable").status,
      "inconclusive",
    )
  }
}
