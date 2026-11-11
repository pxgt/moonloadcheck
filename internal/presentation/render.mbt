///|
fn esc(text : String) -> String {
  text
  .replace_all(old="&", new="&amp;")
  .replace_all(old="<", new="&lt;")
  .replace_all(old=">", new="&gt;")
  .replace_all(old="\"", new="&quot;")
  .replace_all(old="'", new="&#39;")
}

///|
fn byte_name(name : @analysis.ByteName) -> String {
  "<span class=bytes><code>" +
  esc(Json::string(name.display).stringify()) +
  "</code><small>hex: " +
  esc(name.hex) +
  "</small></span>"
}

///|
fn optional_name(name : @analysis.ByteName?) -> String {
  match name {
    Some(value) => byte_name(value)
    None => "<span class=muted>Not recorded / not selected</span>"
  }
}

///|
fn badge(status : String) -> String {
  // Classes are selected from literals; input is never an attribute value.
  let style = match status {
    "pass_static" | "resolved" => "good"
    "fail" | "introduced" | "input_error" => "bad"
    _ => "warn"
  }
  "<span class='badge " + style + "'>" + esc(status) + "</span>"
}

///|
fn strings(items : Array[String]) -> String {
  "<ul>" + items.map(item => "<li>" + esc(item) + "</li>").join("") + "</ul>"
}

///|
fn raw(value : Json) -> String {
  "<details><summary>Decoded schema-2 evidence (JSON)</summary><pre>" +
  esc(value.stringify(indent=2)) +
  "</pre></details>"
}

///|
fn finding_html(finding : @analysis.Finding) -> String {
  let steps = guidance(finding.code)
  "<article class=finding><h4>" +
  esc(finding.code) +
  " · " +
  esc(steps[0]) +
  " " +
  badge(finding.status) +
  "</h4><p class=muted>Finding ID: <code>" +
  esc(finding.id) +
  "</code></p><dl><dt>Subject</dt><dd>" +
  byte_name(finding.subject) +
  "</dd><dt>Requirement</dt><dd>" +
  optional_name(finding.requirement) +
  "</dd><dt>Version</dt><dd>" +
  optional_name(finding.version) +
  "</dd><dt>Provider</dt><dd>" +
  optional_name(finding.provider) +
  "</dd></dl><p>" +
  esc(finding.explanation) +
  "</p><p><strong>Saved action:</strong> " +
  esc(finding.suggested_action) +
  "</p><h5>Dependency chain</h5><ol>" +
  finding.dependency_chain
  .map(item => "<li>" + byte_name(item) + "</li>")
  .join("") +
  "</ol><p>Reference offsets (decimal): <code>" +
  esc(finding.reference_offsets.join(", ")) +
  "</code></p><div class=guide><h5>Investigation and repair guide</h5><ol>" +
  steps[1:].to_owned().map(step => "<li>" + esc(step) + "</li>").join("") +
  "</ol></div></article>"
}

///|
fn check_html(report : @analysis.Report) -> String {
  let html = [
    "<section class=check><h3>" +
    byte_name(report.entry) +
    " " +
    badge(report.status) +
    "</h3>",
    "<dl><dt>Analyzer version</dt><dd>" +
    esc(report.tool_version) +
    "</dd><dt>Rule revision</dt><dd>" +
    esc(report.rule_revision) +
    "</dd><dt>Snapshot SHA-256</dt><dd><code>" +
    esc(report.snapshot_sha256) +
    "</code></dd></dl>",
    "<div class=scope><div><h4>Checked scope</h4>" +
    strings(report.checked_scope) +
    "</div><div><h4>Not checked</h4>" +
    strings(report.not_checked) +
    "</div></div>",
    "<h4>Findings (" + report.findings.length().to_string() + ")</h4>",
  ]
  if report.findings.is_empty() {
    html.push(
      "<p>No findings in the declared checks. This does not certify general runtime or ABI compatibility.</p>",
    )
  }
  for finding in report.findings {
    html.push(finding_html(finding))
  }
  html.push("<h4>Dependency selection</h4>")
  if report.edges.is_empty() {
    html.push("<p>No dependency edges recorded.</p>")
  }
  for edge in report.edges {
    html.push(
      "<details class=edge><summary>" +
      byte_name(edge.consumer) +
      " needs " +
      byte_name(edge.needed) +
      "</summary><p><strong>Selected:</strong> " +
      optional_name(edge.selected) +
      "</p><div class=scroll><table><thead><tr><th>Order</th><th>Search source</th><th>Candidate</th><th>Outcome</th></tr></thead><tbody>",
    )
    for i, candidate in edge.trace {
      html.push(
        "<tr><td>" +
        (i + 1).to_string() +
        "</td><td>" +
        esc(candidate.source) +
        "</td><td>" +
        byte_name(candidate.path) +
        "</td><td>" +
        esc(candidate.outcome) +
        "</td></tr>",
      )
    }
    html.push("</tbody></table></div></details>")
  }
  html.push(
    "<details><summary>Loaded objects and startup symbol scope</summary><div class=scroll><table><thead><tr><th>Path</th><th>Machine</th><th>File identity / SHA-256</th></tr></thead><tbody>",
  )
  for object in report.objects {
    html.push(
      "<tr><td>" +
      byte_name(object.path) +
      "</td><td>" +
      object.machine.to_string() +
      "</td><td><code>" +
      esc(object.file_id) +
      "<br>" +
      esc(object.sha256) +
      "</code></td></tr>",
    )
  }
  html.push(
    "</tbody></table></div><h5>Startup lookup order</h5><ol>" +
    report.symbol_scope.map(item => "<li>" + byte_name(item) + "</li>").join("") +
    "</ol></details>",
  )
  html.push(
    "<details><summary>Version requirements (" +
    report.version_checks.length().to_string() +
    ")</summary><div class=scroll><table><thead><tr><th>Consumer</th><th>Version / provider</th><th>Result</th></tr></thead><tbody>",
  )
  for item in report.version_checks {
    html.push(
      "<tr><td>" +
      byte_name(item.consumer) +
      "</td><td>" +
      byte_name(item.version) +
      optional_name(item.provider) +
      "</td><td>" +
      badge(item.status) +
      "<p>weak=" +
      item.weak.to_string() +
      "</p>" +
      esc(item.explanation) +
      "</td></tr>",
    )
  }
  html.push(
    "</tbody></table></div></details><details><summary>Referenced symbols (" +
    report.symbol_checks.length().to_string() +
    ")</summary><div class=scroll><table><thead><tr><th>Consumer / requirement</th><th>Selected definition</th><th>Lookup / references</th></tr></thead><tbody>",
  )
  for item in report.symbol_checks {
    html.push(
      "<tr><td>" +
      byte_name(item.consumer) +
      byte_name(item.symbol) +
      optional_name(item.version) +
      "</td><td>" +
      optional_name(item.provider) +
      optional_name(item.definition_version) +
      badge(item.status) +
      "</td><td>" +
      esc(item.lookup_policy) +
      "<p>phase=" +
      esc(item.phase) +
      "; weak=" +
      item.weak.to_string() +
      "</p><p>Offsets: <code>" +
      esc(item.reference_offsets.join(", ")) +
      "</code></p><p>Relocations: " +
      esc(item.relocation_types.map(value => value.to_string()).join(", ")) +
      "</p><p>COPY sizes (destination/source): " +
      esc(item.copy_destination_size.unwrap_or("not recorded")) +
      " / " +
      esc(item.copy_source_size.unwrap_or("not recorded")) +
      "</p></td></tr>",
    )
  }
  html.push(
    "</tbody></table></div></details>" + raw(report.to_json()) + "</section>",
  )
  html.join("")
}

///|
fn document(kind : String, status : String, content : String) -> String {
  let head =
    #|<!doctype html>
    #|<html lang="en"><head><meta charset="utf-8">
    #|<meta name="viewport" content="width=device-width,initial-scale=1">
    #|<meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
    #|<title>MoonLoadCheck · Deployment report</title>
    #|<style>
    #|:root{color-scheme:light;--ink:#17283e;--muted:#50647a;--line:#d9e1ea;--accent:#2454a4}*{box-sizing:border-box}body{margin:0;background:#f2f5fa;color:var(--ink);font:16px/1.6 system-ui,sans-serif}header{background:#14283f;color:#fff;padding:36px max(24px,calc((100% - 1120px)/2))}header p{margin:0;color:#bacbe1}h1{font-size:30px;margin:8px 0}h2{font-size:24px}h3{font-size:20px}h4{font-size:17px}h5{font-size:15px;margin:16px 0 6px}main{max-width:1168px;margin:auto;padding:24px}section,.notice,.entry{background:white;border:1px solid var(--line);border-radius:12px;padding:24px;margin:0 0 24px}.check{margin-top:20px}article.finding{border-left:4px solid #d49b42;background:#fbfcfe;padding:16px 20px;margin:16px 0}.guide{background:#eef4ff;border-radius:8px;padding:8px 16px}.scope{display:grid;grid-template-columns:1fr 1fr;gap:24px;background:#f5f8fc;padding:4px 16px;border-radius:8px}dl{display:grid;grid-template-columns:180px 1fr;gap:6px 16px}dt{color:var(--muted)}dd{margin:0;min-width:0}code,pre{font:13px/1.6 ui-monospace,Consolas,monospace;overflow-wrap:anywhere;white-space:pre-wrap}pre{max-height:480px;overflow:auto;background:#f4f6f9;padding:16px}small,.muted{color:var(--muted)}.bytes{display:inline-block;vertical-align:top;max-width:100%;margin-right:8px;unicode-bidi:isolate;direction:ltr}.bytes small{display:block;font:11px/1.5 ui-monospace,monospace;overflow-wrap:anywhere}.badge{display:inline-block;font:600 12px/1.7 system-ui;padding:2px 9px;border-radius:20px;vertical-align:middle}.good{background:#dff4e8;color:#155f39}.bad{background:#fde6e4;color:#982d26}.warn{background:#fff0ca;color:#75520e}details{border-top:1px solid var(--line);padding:12px 0}summary{cursor:pointer;font-weight:600}table{width:100%;border-collapse:collapse;font-size:14px}th{text-align:left;color:var(--muted);background:#f4f7fb}th,td{padding:10px;border-bottom:1px solid var(--line);vertical-align:top}.scroll{overflow:auto}a{color:var(--accent)}nav{display:flex;gap:16px;flex-wrap:wrap}footer{color:var(--muted);font-size:13px;margin:24px 0}li{margin:5px 0}p,dd,td,h3,h4{overflow-wrap:anywhere}@media(max-width:700px){main{padding:12px}section,.entry,.notice{padding:16px}.scope{grid-template-columns:1fr;gap:0}dl{grid-template-columns:1fr}dt{font-weight:600}h1{font-size:25px}}@media print{body{background:white}header{background:white;color:var(--ink);padding:0}header p{color:var(--muted)}main{max-width:none;padding:0}details>*{display:block}pre{max-height:none}section,.entry{break-inside:auto}.badge{border:1px solid}nav{display:none}}
    #|</style></head><body><header><p>MOONLOADCHECK / OFFLINE EVIDENCE</p><h1>Deployment report</h1>
  head +
  "<p>" +
  esc(kind) +
  " · " +
  badge(status) +
  "</p></header><main><aside class=notice>" +
  "<strong>Saved evidence, not a fresh analysis.</strong> This page preserves the recorded verdict. " +
  "A static pass covers only the declared checks; review uncertainty and not_checked. " +
  "Guidance is general investigation advice, not proof that a repair is safe. " +
  "Report authenticity and the target's current state are not verified. Paths and symbols are text; hex is authoritative." +
  "</aside>" +
  content +
  "<footer>Generated locally by MoonLoadCheck. No scripts, network assets or binary snapshots are embedded. " +
  "Reports can expose internal paths and symbols; review their contents before sharing.</footer></main></body></html>"
}

///|
fn summary(
  kind : String,
  status : String,
  entries : Int32,
  findings : Array[@analysis.Finding],
  changes : Array[@analysis.Change],
) -> Json {
  let counts : Map[String, Int32] = Map([])
  for finding in findings {
    counts[finding.code] = counts.get(finding.code).unwrap_or(0) + 1
  }
  let classes : Map[String, Int32] = Map([])
  for change in changes {
    classes[change.classification] = classes
      .get(change.classification)
      .unwrap_or(0) +
      1
  }
  {
    "schema_version": 1,
    "kind": "report_summary",
    "source_kind": kind,
    "report_schema_version": 2,
    "status": status,
    "exit_code": exit_code(status),
    "entries": entries,
    "findings": findings.length(),
    "codes": Json(counts),
    "changes": Json(classes),
  }
}

///|
fn exit_code(status : String) -> Int32 {
  match status {
    "pass_static" => 0
    "fail" => 1
    "inconclusive" => 2
    _ => 3
  }
}

///|
/// Rendering preserves the source verdict as its exit code. A 4 Mi-code-unit
/// presentation bound is narrower than the saved evidence reader's bound.
pub fn present(text : String, html~ : Bool) -> (String, Int32) raise {
  guard text.length() <= 4194304 else {
    raise @analysis.ReportError(
      "presentation input exceeds 4194304 UTF-16 code units",
    )
  }
  let value = @json.parse(text[:], reject_duplicate_keys=true)
  let (kind, status, content, brief) = match value {
    { "entries": _, "entry": _, .. } =>
      raise @analysis.ReportError("ambiguous report shape")
    { "entries": _, .. } => {
      let report = @analysis.read_impact_report(text)
      let sections = [
        "<h2>Explicit consumer comparison</h2><p>Application/snapshot change flags are saved metadata; this page does not establish environment-only causation.</p><nav>",
      ]
      for i, _ in report.entries {
        sections.push(
          "<a href='#consumer-" +
          i.to_string() +
          "'>Consumer " +
          (i + 1).to_string() +
          "</a>",
        )
      }
      sections.push("</nav>")
      let findings = []
      let changes = []
      for i, entry in report.entries {
        for finding in entry.after.findings {
          findings.push(finding)
        }
        for change in entry.changes {
          changes.push(change)
        }
        if html {
          sections.push(
            "<article class=entry id='consumer-" +
            i.to_string() +
            "'><h2>Consumer " +
            (i + 1).to_string() +
            "</h2>" +
            byte_name(entry.entry) +
            "<p>" +
            badge(entry.before.status) +
            " → " +
            badge(entry.after.status) +
            "</p><p>application_changed=" +
            entry.application_changed.to_string() +
            "; snapshot_changed=" +
            entry.snapshot_changed.to_string() +
            "</p><h3>Changes</h3>",
          )
          if entry.changes.is_empty() {
            sections.push("<p>No finding changes recorded.</p>")
          }
          for change in entry.changes {
            sections.push(
              "<div class=change><h4>" +
              badge(change.classification) +
              " <code>" +
              esc(change.finding_id) +
              "</code></h4>",
            )
            match change.before {
              Some(f) =>
                sections.push(
                  "<details><summary>Earlier finding</summary>" +
                  finding_html(f) +
                  "</details>",
                )
              None => ()
            }
            match change.after {
              Some(f) =>
                sections.push(
                  "<details><summary>Later finding</summary>" +
                  finding_html(f) +
                  "</details>",
                )
              None => ()
            }
            sections.push("</div>")
          }
          sections.push(
            "<details><summary>Before: complete check</summary>" +
            check_html(entry.before) +
            "</details>" +
            "<h3>After</h3>" +
            check_html(entry.after) +
            "</article>",
          )
        }
      }
      (
        "comparison",
        report.status,
        sections.join(""),
        summary(
          "comparison",
          report.status,
          report.entries.length(),
          findings,
          changes,
        ),
      )
    }
    { "entry": _, .. } => {
      let report = @analysis.read_report(text)
      (
        "check",
        report.status,
        if html {
          check_html(report)
        } else {
          ""
        },
        summary("check", report.status, 1, report.findings, []),
      )
    }
    {
      "schema_version": 2,
      "status": "input_error",
      "message": String(message),
      ..
    } => {
      let kind = match value {
        { "error_kind": String(kind), .. } => kind
        _ => "unspecified"
      }
      (
        "command error",
        "input_error",
        "<section><h2>Analysis could not run</h2><p>" +
        esc(kind) +
        "</p><pre>" +
        esc(message) +
        "</pre><p>Repair the named input or command invocation, then rerun analysis. No deployment verdict was established.</p>" +
        raw(value) +
        "</section>",
        summary("command_error", "input_error", 0, [], []),
      )
    }
    _ =>
      raise @analysis.ReportError(
        "expected a schema-2 check, comparison or command error",
      )
  }
  let output = if html {
    document(kind, status, content)
  } else {
    brief.stringify()
  }
  guard output.length() <= 33554432 else {
    raise @analysis.ReportError(
      "presentation output exceeds 33554432 UTF-16 code units",
    )
  }
  (output, exit_code(status))
}
