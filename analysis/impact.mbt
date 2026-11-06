///|
pub(all) struct Change {
  classification : String
  finding_id : String
  before : Finding?
  after : Finding?
} derive(ToJson)

///|
pub extend Change with ToJson::{to_json}

///|
pub(all) struct ImpactEntry {
  entry : ByteName
  application_changed : Bool
  snapshot_changed : Bool
  before : Report
  after : Report
  changes : Array[Change]
} derive(ToJson)

///|
pub extend ImpactEntry with ToJson::{to_json}

///|
pub(all) struct ImpactReport {
  schema_version : Int32
  status : String
  entries : Array[ImpactEntry]
} derive(ToJson)

///|
pub extend ImpactReport with ToJson::{to_json}

///|
pub fn ImpactReport::exit_code(self : ImpactReport) -> Int32 {
  match self.status {
    "pass_static" => 0
    "fail" => 1
    "inconclusive" => 2
    _ => 3
  }
}

///|
fn incomplete(report : Report) -> Bool {
  report.findings.any(finding => {
    finding.status == "unknown" || finding.status == "input_error"
  })
}

///|
fn compare_findings(before : Report, after : Report) -> Array[Change] {
  let old : Map[String, Finding] = Map([])
  let current : Map[String, Finding] = Map([])
  for finding in before.findings {
    old[finding.id] = finding
  }
  for finding in after.findings {
    current[finding.id] = finding
  }
  let changes = []
  for finding in after.findings {
    let previous = old.get(finding.id)
    let classification = if finding.status != "fail" ||
      (previous is Some(value) && value.status != "fail") {
      "indeterminate"
    } else if previous is Some(_) {
      "existing"
    } else if incomplete(before) {
      "indeterminate"
    } else {
      "introduced"
    }
    changes.push({
      classification,
      finding_id: finding.id,
      before: previous,
      after: Some(finding),
    })
  }
  for finding in before.findings {
    if current.get(finding.id) is None {
      changes.push({
        classification: if finding.status != "fail" || incomplete(after) {
          "indeterminate"
        } else {
          "resolved"
        },
        finding_id: finding.id,
        before: Some(finding),
        after: None,
      })
    }
  }
  changes
}

///|
fn entry_digest(snapshot : @snapshot.Snapshot, entry : Bytes) -> String? {
  try snapshot.resolve(entry) catch {
    _ => None
  } noraise {
    resolved =>
      match resolved.entry {
        @snapshot.Entry::File(id) => snapshot.digest(id)
        _ => None
      }
  }
}

///|
/// Recomputes both complete views for each explicit consumer. Snapshot change
/// includes application bytes; it is not an attribution to the environment alone.
pub fn compare(
  before : @snapshot.Snapshot,
  after : @snapshot.Snapshot,
  entries : Array[Bytes],
) -> ImpactReport raise {
  guard !entries.is_empty() && entries.length() <= 64 else {
    raise ReportError("provide 1..64 explicit consumers")
  }
  let seen : Map[Bytes, Bool] = Map([])
  let results = []
  let mut severity = 0
  for entry in entries {
    guard seen.get(entry) is None else {
      raise ReportError("duplicate consumer entry")
    }
    seen[entry] = true
    let earlier = check_compatibility(before, entry)
    let later = check_compatibility(after, entry)
    let changes = compare_findings(earlier, later)
    let level = if earlier.status == "input_error" ||
      later.status == "input_error" {
      3
    } else if later.status == "fail" {
      2
    } else if incomplete(earlier) || incomplete(later) {
      1
    } else {
      0
    }
    if level > severity {
      severity = level
    }
    results.push({
      entry: name(entry),
      application_changed: entry_digest(before, entry) !=
      entry_digest(after, entry),
      snapshot_changed: before.manifest_digest() != after.manifest_digest(),
      before: earlier,
      after: later,
      changes,
    })
  }
  {
    schema_version: 2,
    status: match severity {
      0 => "pass_static"
      1 => "inconclusive"
      2 => "fail"
      _ => "input_error"
    },
    entries: results,
  }
}

///|
pub(all) suberror ReportError {
  ReportError(String)
}

///|
priv struct ReportHeader {
  schema_version : Int32
} derive(@json.FromJson)

///|
pub fn read_report(json : String) -> Report raise {
  guard json.length() <= 67108864 else {
    raise ReportError("report exceeds 67108864 UTF-16 code units")
  }
  let value = @json.parse(json[:])
  let header : ReportHeader = @json.from_json(value)
  guard header.schema_version == 2 else {
    raise ReportError("unsupported report schema")
  }
  let report : Report = @json.from_json(value)
  guard ["pass_static", "fail", "inconclusive", "input_error"].contains(
    report.status,
  ) else {
    raise ReportError("invalid report status")
  }
  let ids : Map[String, Bool] = Map([])
  let mut severity = 0
  for finding in report.findings {
    guard !finding.id.is_empty() else { raise ReportError("empty finding id") }
    guard ids.get(finding.id) is None else {
      raise ReportError("duplicate finding id")
    }
    ids[finding.id] = true
    let level = match finding.status {
      "unknown" => 1
      "fail" => 2
      "input_error" => 3
      _ => raise ReportError("invalid finding status")
    }
    if level > severity {
      severity = level
    }
  }
  let expected = match severity {
    0 => "pass_static"
    1 => "inconclusive"
    2 => "fail"
    _ => "input_error"
  }
  guard report.status == expected else {
    raise ReportError("report status conflicts with its findings")
  }
  report
}

///|
pub fn Report::explain(self : Report, id : String) -> Finding raise ReportError {
  for finding in self.findings {
    if finding.id == id {
      return finding
    }
  }
  raise ReportError("finding id is not present in this report")
}
