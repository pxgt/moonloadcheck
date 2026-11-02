///|
fn edge_fixture(
  arch : String,
  suite : String,
  case : String,
) -> @snapshot.Snapshot raise {
  let folder = "fixtures/generated/linkage-edges/\{arch}/\{suite}/\{case}/snapshot/"
  @snapshot.load(@fs.read_file_to_string(folder + "manifest.json"), digest => {
    @fs.read_file_to_bytes(folder + "blobs/" + digest)
  })
}

///|
fn edge_linkage(
  arch : String,
  suite : String,
  case : String,
  path : String,
) -> @model.Linkage raise {
  @elf.read_linkage(
    @fs.read_file_to_bytes(
      "fixtures/generated/linkage-edges/\{arch}/\{suite}/\{case}/root/\{path}",
    ),
  )
}

///|
test "non-UTF8 dynamic names retain byte identity in lookup and saved reports" {
  for arch in ["amd64", "arm64"] {
    for suite in ["jammy", "noble"] {
      let app = edge_linkage(arch, suite, "raw-name", "app")
      assert_true(app.symbols.any(s => s.name == b"a\xffi"))
      let report = @analysis.check_compatibility(
        edge_fixture(arch, suite, "raw-name"),
        b"/app",
      )
      assert_eq(report.status, "pass_static")
      assert_true(
        report.symbol_checks.any(c => {
          c.symbol.hex == "61ff69" &&
          c.status == "pass" &&
          c.provider.map(p => p.display) == Some("/runtime/libedge.so.1")
        }),
      )
      let encoded = report.to_json().stringify()
      assert_eq(@analysis.read_report(encoded).to_json().stringify(), encoded)
      let other = edge_linkage(
        arch, suite, "raw-mismatch", "runtime/libedge.so.1",
      )
      assert_true(other.symbols.any(s => s.name == b"a\xfei"))
      assert_eq(
        @utf8.decode_lossy(b"a\xffi"[:]),
        @utf8.decode_lossy(b"a\xfei"[:]),
      )
      let missing = @analysis.check_compatibility(
        edge_fixture(arch, suite, "raw-mismatch"),
        b"/app",
      )
      assert_eq(missing.status, "fail")
      assert_true(
        missing.symbol_checks.any(c => {
          c.symbol.hex == "61ff69" && c.status == "fail" && c.provider is None
        }),
      )
    }
  }
}

///|
test "a strong undefined dynsym with no active relocation is not a requirement" {
  for arch in ["amd64", "arm64"] {
    for suite in ["jammy", "noble"] {
      let app = edge_linkage(arch, suite, "unused-undefined", "app")
      let indices = []
      for i in 0..<app.symbols.length() {
        if app.symbols[i].name == b"absent_strong_unused" {
          assert_eq(app.symbols[i].binding, 1)
          assert_eq(app.symbols[i].section, 0)
          indices.push(i)
        }
      }
      assert_eq(indices.length(), 1)
      assert_false(
        app.references.any(r => {
          r.relocation != 0 && indices.contains(r.symbol_index)
        }),
      )
      let report = @analysis.check_compatibility(
        edge_fixture(arch, suite, "unused-undefined"),
        b"/app",
      )
      assert_eq(report.status, "pass_static")
      assert_false(
        report.symbol_checks.any(c => c.symbol.display == "absent_strong_unused"),
      )
    }
  }
}

///|
test "different object-local GNU version indices match by name and hash" {
  for arch in ["amd64", "arm64"] {
    for suite in ["jammy", "noble"] {
      let app = edge_linkage(arch, suite, "version-index", "app")
      let lib = edge_linkage(
        arch, suite, "version-index", "runtime/libedge.so.1",
      )
      let needs = app.version_needs.filter(n => n.name == b"EDGE_1")
      let defs = lib.version_defs.filter(d => d.name == b"EDGE_1")
      assert_eq(needs.length(), 1)
      assert_eq(defs.length(), 1)
      let need = needs[0]
      let def = defs[0]
      assert_eq(def.index, 17)
      assert_true(need.index != def.index)
      assert_eq(need.hash, def.hash)
      let report = @analysis.check_compatibility(
        edge_fixture(arch, suite, "version-index"),
        b"/app",
      )
      assert_eq(report.status, "pass_static")
      assert_true(
        report.symbol_checks.any(c => {
          c.symbol.display == "api" &&
          c.version.map(v => v.display) == Some("EDGE_1") &&
          c.definition_version.map(v => v.display) == Some("EDGE_1")
        }),
      )
    }
  }
}

///|
test "LOCAL, INTERNAL and HIDDEN candidates do not satisfy another object" {
  for arch in ["amd64", "arm64"] {
    for suite in ["jammy", "noble"] {
      for case in ["local-first", "internal-first", "hidden-first"] {
        let lib = edge_linkage(arch, suite, case, "runtime/libedge.so.1")
        let symbols = lib.symbols.filter(s => s.name == b"api")
        assert_eq(symbols.length(), 1)
        let symbol = symbols[0]
        assert_true(symbol.lookupable)
        assert_true(
          if case == "local-first" {
            symbol.binding == 0
          } else {
            symbol.visibility == (if case == "internal-first" { 1 } else { 2 })
          },
        )
        let report = @analysis.check_compatibility(
          edge_fixture(arch, suite, case),
          b"/app",
        )
        assert_eq(report.status, "pass_static")
        assert_true(
          report.symbol_checks.any(c => {
            c.symbol.display == "api" &&
            c.provider.map(p => p.display) == Some("/runtime/libsecond.so.1")
          }),
        )
      }
    }
  }
}

///|
test "IFUNC checks definition availability without claiming resolver behavior" {
  for arch in ["amd64", "arm64"] {
    for suite in ["jammy", "noble"] {
      for case in ["ifunc-good", "ifunc-wrong-value"] {
        let lib = edge_linkage(arch, suite, case, "runtime/libedge.so.1")
        assert_true(lib.symbols.any(s => s.name == b"api" && s.kind == 10))
        let report = @analysis.check_compatibility(
          edge_fixture(arch, suite, case),
          b"/app",
        )
        assert_eq(report.status, "pass_static")
        assert_true(report.not_checked.contains("IFUNC resolver results"))
        assert_true(
          report.symbol_checks.any(c => {
            c.symbol.display == "api" && c.status == "pass"
          }),
        )
      }
    }
  }
}

///|
test "missing lazy references fail statically and retain deferred-call phase" {
  for arch in ["amd64", "arm64"] {
    for suite in ["jammy", "noble"] {
      let app = edge_linkage(arch, suite, "lazy-missing", "app")
      assert_false(app.bind_now)
      let report = @analysis.check_compatibility(
        edge_fixture(arch, suite, "lazy-missing"),
        b"/app",
      )
      assert_eq(report.status, "fail")
      assert_true(
        report.symbol_checks.any(c => {
          c.symbol.display == "api" &&
          c.status == "fail" &&
          c.phase == "startup-or-first-call"
        }),
      )
    }
  }
}

///|
test "unknown relocation types stay unknown while NONE and RELATIVE need no lookup" {
  for (arch, relative) in [("amd64", 8), ("arm64", 1027)] {
    for suite in ["jammy", "noble"] {
      for case in ["unknown-symbol", "unknown-free"] {
        let report = @analysis.check_compatibility(
          edge_fixture(arch, suite, case),
          b"/app",
        )
        assert_eq(report.status, "inconclusive")
        assert_true(
          report.findings.any(f => {
            f.code == "MLC008" &&
            f.status == "unknown" &&
            !f.reference_offsets.is_empty()
          }),
        )
        assert_false(report.symbol_checks.any(c => c.symbol.hex == ""))
        assert_true(report.symbol_checks.any(c => c.status == "pass"))
        if case == "unknown-free" {
          assert_true(report.symbol_checks.all(c => c.status == "pass"))
        } else {
          assert_true(
            report.symbol_checks.any(c => {
              c.symbol.display == "api" && c.status == "unknown"
            }),
          )
        }
      }
      for case in ["baseline-pie", "baseline-exec", "relative-none"] {
        let report = @analysis.check_compatibility(
          edge_fixture(arch, suite, case),
          b"/app",
        )
        assert_eq(report.status, "pass_static")
        assert_false(report.symbol_checks.any(c => c.symbol.hex == ""))
      }
      let app = edge_linkage(arch, suite, "baseline-pie", "app")
      assert_true(
        app.references.any(r => r.symbol_index == 0 && r.relocation == relative),
      )
      let none = edge_linkage(arch, suite, "relative-none", "app")
      assert_true(none.references.any(r => r.relocation == 0))
    }
  }
}
