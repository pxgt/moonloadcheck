///|
fn environment_fixture(
  arch : String,
  suite : String,
  case : String,
) -> @snapshot.Snapshot raise {
  let folder = "fixtures/generated/environment-edges/\{arch}/\{suite}/\{case}/snapshot/"
  @snapshot.load(@fs.read_file_to_string(folder + "manifest.json"), digest => {
    @fs.read_file_to_bytes(folder + "blobs/" + digest)
  })
}

///|
test "semicolons are literal in RPATH and RUNPATH, never extra search directories" {
  for arch in ["amd64", "arm64"] {
    for suite in ["jammy", "noble"] {
      for kind in ["rpath", "runpath"] {
        let good = @analysis.check_compatibility(
          environment_fixture(arch, suite, kind + "-semicolon"),
          b"/app/bin/app",
        )
        assert_eq(good.status, "pass_static")
        assert_eq(
          good.edges[0].selected.unwrap().display,
          "/good;/decoy/libapi.so.1",
        )
        let missing = @analysis.check_compatibility(
          environment_fixture(arch, suite, kind + "-semicolon-missing"),
          b"/app/bin/app",
        )
        assert_eq(missing.status, "fail")
        assert_true(missing.edges[0].selected is None)
        assert_false(
          missing.edges[0].trace.any(c => c.path.display == "/good/libapi.so.1"),
        )
      }
    }
  }
}

///|
test "all eight braced and unbraced token combinations use measured target facts" {
  for arch in ["amd64", "arm64"] {
    for suite in ["jammy", "noble"] {
      for bits in ["000", "001", "010", "011", "100", "101", "110", "111"] {
        let snapshot = environment_fixture(arch, suite, "tokens-" + bits)
        let profile = snapshot.profile()
        let expected = "/app/bin/" +
          @utf8.decode(@hex.decode(profile.lib_token_hex.unwrap()[:])) +
          "/" +
          @utf8.decode(@hex.decode(profile.platform_token_hex.unwrap()[:])) +
          "/libapi.so.1"
        let report = @analysis.check_compatibility(snapshot, b"/app/bin/app")
        assert_eq(report.status, "pass_static")
        assert_eq(report.edges[0].selected.unwrap().display, expected)
      }
    }
  }
}

///|
test "each ORIGIN is anchored to the declaring object or main environment" {
  for arch in ["amd64", "arm64"] {
    for suite in ["jammy", "noble"] {
      for
        (case, path) in [
          ("dso-origin", "/app/bin/providers/private/libleaf.so.1"),
          ("ancestor-origin", "/app/bin/providers/libleaf.so.1"),
          ("environment-origin", "/app/bin/providers/libleaf.so.1"),
        ] {
        let report = @analysis.check_compatibility(
          environment_fixture(arch, suite, case),
          b"/app/bin/app",
        )
        assert_eq(report.status, "pass_static")
        let edges = report.edges.filter(e => e.needed.display == "libleaf.so.1")
        assert_eq(edges.length(), 1)
        assert_eq(edges[0].selected.unwrap().display, path)
      }
    }
  }
}

///|
test "an empty RUNPATH is disabled while colon empty components search cwd" {
  for arch in ["amd64", "arm64"] {
    for suite in ["jammy", "noble"] {
      let empty = @analysis.check_compatibility(
        environment_fixture(arch, suite, "empty-runpath"),
        b"/app/bin/app",
      )
      assert_eq(empty.status, "fail")
      assert_true(empty.edges[0].selected is None)
      let colon = @analysis.check_compatibility(
        environment_fixture(arch, suite, "colon-runpath"),
        b"/app/bin/app",
      )
      assert_eq(colon.status, "pass_static")
      assert_eq(colon.edges[0].selected.unwrap().display, "/libapi.so.1")
    }
  }
}

///|
test "eligible conditional cache records are unknown and irrelevant records are skipped" {
  for arch in ["amd64", "arm64"] {
    for
      case in [
        "cache-tls", "cache-os-old", "cache-os-future", "cache-foreign", "cache-plain-first",
      ] {
      let report = @analysis.check_compatibility(
        environment_fixture(arch, "jammy", case),
        b"/app/bin/app",
      )
      if case == "cache-foreign" || case == "cache-plain-first" {
        assert_eq(report.status, "pass_static")
        assert_eq(
          report.edges[0].selected.unwrap().display,
          "/fallback/libapi.so.1",
        )
      } else {
        assert_eq(report.status, "inconclusive")
        assert_true(report.edges[0].selected is None)
        assert_true(report.edges[0].trace.any(c => c.source == "cache_unknown"))
        assert_true(report.findings.any(f => f.code == "MLC007"))
      }
    }
  }
}

///|
priv struct FactCase {
  case : String
  expected_code : Int32
} derive(@json.FromJson)

///|
test "required, empty, missing and unknown profile facts have distinct outcomes" {
  let cases : Array[FactCase] = @json.from_json(
    @json.parse(
      @fs.read_file_to_string("fixtures/generated/environment-edges/facts.json")[:],
    ),
  )
  assert_eq(cases.length(), 50)
  for fact in cases {
    let folder = "fixtures/generated/environment-edges/facts/\{fact.case}/snapshot/"
    try
      @snapshot.load(@fs.read_file_to_string(folder + "manifest.json"), digest => {
        @fs.read_file_to_bytes(folder + "blobs/" + digest)
      })
    catch {
      @json.JsonDecodeError(_) => assert_eq(fact.expected_code, 3)
      @snapshot.SnapshotError::InvalidSnapshot(_) =>
        assert_eq(fact.expected_code, 3)
      @snapshot.SnapshotError::ContentMismatch(_) =>
        assert_eq(fact.expected_code, 3)
      _ => fail("unexpected fact loading error")
    } noraise {
      snapshot => {
        assert_true(fact.expected_code != 3)
        let report = @analysis.check_compatibility(snapshot, b"/app/bin/app")
        assert_eq(
          report.status,
          ["pass_static", "fail", "inconclusive"][fact.expected_code],
        )
      }
    }
  }
}
