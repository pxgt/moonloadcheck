///|
test "HTML text escaping preserves markup as text" {
  assert_eq(
    esc("<script a=\"x\">'&</script>"),
    "&lt;script a=&quot;x&quot;&gt;&#39;&amp;&lt;/script&gt;",
  )
  assert_true(
    byte_name({ display: "<img src=x onerror=alert(1)>", hex: "ff", }).contains(
      "&lt;img",
    ),
  )
  assert_false(badge("fail' onclick='alert(1)").contains("onclick='"))
}

///|
test "guidance covers current codes and keeps unfamiliar diagnostics explicit" {
  for
    code in [
      "MLC001", "MLC002", "MLC003", "MLC004", "MLC005", "MLC006", "MLC007", "MLC008",
      "MLC009",
    ] {
    assert_eq(guidance(code).length(), 4)
    assert_false(guidance(code)[0].contains("Unfamiliar"))
  }
  assert_true(guidance("MLC999")[0].contains("Unfamiliar"))
}

///|
test "command errors retain nonpassing summary and inert HTML" {
  let input = "{\"schema_version\":2,\"status\":\"input_error\",\"message\":\"<script>alert(1)</script>\"}"
  let (page, code) = present(input, html=true)
  assert_eq(code, 3)
  assert_true(page.contains("&lt;script&gt;alert(1)&lt;/script&gt;"))
  assert_false(page.contains("<script>"))
  let (brief, code) = present(input, html=false)
  assert_eq(code, 3)
  assert_true(brief.contains("\"status\":\"input_error\""))
}

///|
test "invalid ambiguous and oversized presentation inputs cannot render a pass" {
  for input in ["{}", "{\"entries\":[],\"entry\":{}}", " ".repeat(4194305)] {
    try present(input, html=true) catch {
      @analysis.ReportError(_) => ()
      error => fail("unexpected error: \{error}")
    } noraise {
      _ => fail("invalid input accepted")
    }
  }
  try present("{\"schema_version\":2,\"schema_version\":2}", html=true) catch {
    @json.ParseError::DuplicateKey(_, _) => ()
    error => fail("unexpected error: \{error}")
  } noraise {
    _ => fail("ambiguous JSON accepted")
  }
}
