///|
priv struct MatrixTarget {
  id : String
  config_sha256 : String
  entries : Array[String]
  reports : Array[Json]
  error : String?
} derive(@json.FromJson)

///|
priv struct MatrixInput {
  schema_version : Int32
  kind : String
  targets : Array[MatrixTarget]
} derive(@json.FromJson)

///|
/// Matrix aggregation validates every nested check and derives its verdict.
/// Input metadata is not authenticated. Comparisons never imply causation.
pub fn present_matrix(text : String, html~ : Bool) -> (String, Int32) raise {
  guard text.length() <= 4194304 else {
    raise @analysis.ReportError(
      "matrix input exceeds 4194304 UTF-16 code units",
    )
  }
  let input : MatrixInput = @json.from_json(
    @json.parse(text[:], reject_duplicate_keys=true),
  )
  guard input.schema_version == 1 &&
    input.kind == "deployment_matrix" &&
    input.targets.length() > 0 &&
    input.targets.length() <= 16 else {
    raise @analysis.ReportError("expected matrix schema 1 with 1..16 targets")
  }
  let ids : Array[String] = []
  let statuses : Array[String] = []
  let cells : Array[Json] = []
  let identity : Map[String, Array[String]] = Map([])
  let content : Array[String] = [
    "<p>Saved deployment matrix. A pass covers only each recorded scope. Target facts and program digests are saved evidence, not authenticated facts. Different program digests are not an environment-only comparison.</p>",
  ]
  let rows : Array[String] = []
  let mut declared = 0
  let mut count = 0
  for target in input.targets {
    guard target.id != "" &&
      !ids.contains(target.id) &&
      target.entries.length() <= 128 &&
      target.reports.length() <= target.entries.length() else {
      raise @analysis.ReportError(
        "duplicate target or invalid entry/report count",
      )
    }
    ids.push(target.id)
    declared += target.entries.length()
    guard declared <= 128 else {
      raise @analysis.ReportError("matrix exceeds 128 declared entries")
    }
    guard target.config_sha256.length() == 64 &&
      target.config_sha256
      .iter()
      .all(c => "0123456789abcdef".contains(c.to_string())) else {
      raise @analysis.ReportError("invalid config digest")
    }
    let entries : Array[String] = []
    for entry in target.entries {
      guard entry.has_prefix("/") && !entries.contains(entry) else {
        raise @analysis.ReportError("entries must be distinct absolute paths")
      }
      entries.push(entry)
    }
    content.push(
      "<section><h2>" +
      esc(target.id) +
      "</h2><p>Configuration SHA-256: <code>" +
      esc(target.config_sha256) +
      "</code></p>",
    )
    match target.error {
      Some(message) => {
        guard message != "" else {
          raise @analysis.ReportError("empty target error")
        }
        statuses.push("input_error")
        cells.push({
          "target": target.id,
          "status": "input_error",
          "message": message,
        })
        content.push(badge("input_error") + "<pre>" + esc(message) + "</pre>")
      }
      None => {
        guard !target.entries.is_empty() &&
          target.entries.length() == target.reports.length() else {
          raise @analysis.ReportError(
            "missing target results without an explicit error",
          )
        }
      }
    }
    for index, value in target.reports {
      let (brief, code) = present(value.stringify(), html=false)
      let parsed = @json.parse(brief[:])
      guard parsed is { "source_kind": "check" | "command_error", .. } else {
        raise @analysis.ReportError(
          "matrix cells require checks or command errors",
        )
      }
      let status = match code {
        0 => "pass_static"
        1 => "fail"
        2 => "inconclusive"
        _ => "input_error"
      }
      statuses.push(status)
      count += 1
      guard count <= 128 else {
        raise @analysis.ReportError("matrix exceeds 128 checks")
      }
      let entry = target.entries[index]
      let mut program : Json = Json::null()
      let mut detail = ""
      if value is { "entry": _, .. } {
        let report = @analysis.read_report(value.stringify())
        guard report.entry.display == entry else {
          raise @analysis.ReportError("matrix entry differs from nested check")
        }
        if !report.objects.is_empty() {
          let object = report.objects[0]
          let key = Json::array([
            Json::string(report.entry.hex),
            Json(object.machine),
          ]).stringify()
          let hashes = identity.get(key).unwrap_or([])
          if !hashes.contains(object.sha256) {
            hashes.push(object.sha256)
          }
          identity[key] = hashes
          program = { "machine": object.machine, "sha256": object.sha256 }
          detail = "<p>Program machine: " +
            object.machine.to_string() +
            "; SHA-256: <code>" +
            esc(object.sha256) +
            "</code></p>"
        }
        if html {
          detail += check_html(report)
        }
      } else if html {
        detail = raw(value)
      }
      cells.push({
        "target": target.id,
        "entry": entry,
        "status": status,
        "program": program,
      })
      rows.push(
        "<tr><td>" +
        esc(target.id) +
        "</td><td><a href='#consumer-" +
        count.to_string() +
        "'>" +
        esc(entry) +
        "</a></td><td>" +
        badge(status) +
        "</td></tr>",
      )
      if html {
        content.push(
          "<details id='consumer-" +
          count.to_string() +
          "'><summary>" +
          esc(entry) +
          " — " +
          badge(status) +
          "</summary>" +
          detail +
          "</details>",
        )
      }
    }
    for i = target.reports.length(); i < target.entries.length(); i = i + 1 {
      rows.push(
        "<tr><td>" +
        esc(target.id) +
        "</td><td>" +
        esc(target.entries[i]) +
        "</td><td>not_run (target error)</td></tr>",
      )
      cells.push({
        "target": target.id,
        "entry": target.entries[i],
        "status": "not_run",
      })
    }
    content.push("</section>")
  }
  let status = if statuses.contains("input_error") {
    "input_error"
  } else if statuses.contains("fail") {
    "fail"
  } else if statuses.contains("inconclusive") {
    "inconclusive"
  } else {
    "pass_static"
  }
  let mut differing = 0
  for _, hashes in identity {
    if hashes.length() > 1 {
      differing += 1
    }
  }
  let result : Json = {
    "schema_version": 1,
    "kind": "deployment_matrix_summary",
    "status": status,
    "exit_code": exit_code(status),
    "target_count": input.targets.length(),
    "check_count": count,
    "different_program_groups": differing,
    "cells": cells,
  }
  let output = if html {
    document(
      "deployment matrix",
      status,
      "<p>Same entry/architecture groups with different program digests: " +
      differing.to_string() +
      "</p><table><thead><tr><th>Target</th><th>Application</th><th>Verdict</th></tr></thead><tbody>" +
      rows.join("") +
      "</tbody></table>" +
      content.join(""),
    )
  } else {
    result.stringify()
  }
  guard output.length() <= 33554432 else {
    raise @analysis.ReportError(
      "matrix output exceeds 33554432 UTF-16 code units",
    )
  }
  (output, exit_code(status))
}
