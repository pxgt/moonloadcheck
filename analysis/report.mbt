///|
pub(all) struct ByteName {
  display : String
  hex : String
} derive(ToJson)

///|
pub extend ByteName with ToJson::{to_json}

///|
fn name(bytes : Bytes) -> ByteName {
  { display: @utf8.decode_lossy(bytes[:]), hex: @hex.encode(bytes[:]), }
}

///|
pub(all) struct Candidate {
  source : String
  path : ByteName
  outcome : String
} derive(ToJson)

///|
pub extend Candidate with ToJson::{to_json}

///|
pub(all) struct DependencyEdge {
  consumer : ByteName
  needed : ByteName
  selected : ByteName?
  trace : Array[Candidate]
} derive(ToJson)

///|
pub extend DependencyEdge with ToJson::{to_json}

///|
pub(all) struct Finding {
  code : String
  status : String
  subject : ByteName
  requirement : ByteName?
  dependency_chain : Array[ByteName]
  explanation : String
  suggested_action : String
} derive(ToJson)

///|
pub extend Finding with ToJson::{to_json}

///|
pub(all) struct LoadedObject {
  path : ByteName
  file_id : String
  sha256 : String
  machine : Int32
} derive(ToJson)

///|
pub extend LoadedObject with ToJson::{to_json}

///|
pub(all) struct Report {
  schema_version : Int32
  tool_version : String
  rule_revision : String
  snapshot_sha256 : String
  entry : ByteName
  checked_scope : Array[String]
  not_checked : Array[String]
  status : String
  objects : Array[LoadedObject]
  edges : Array[DependencyEdge]
  findings : Array[Finding]
} derive(ToJson)

///|
pub extend Report with ToJson::{to_json}

///|
pub fn Report::exit_code(self : Report) -> Int32 {
  match self.status {
    "pass_static" => 0
    "fail" => 1
    "inconclusive" => 2
    _ => 3
  }
}

///|
fn finish(report : Report) -> Report {
  let mut level = 0
  for finding in report.findings {
    let value = match finding.status {
      "input_error" => 3
      "fail" => 2
      _ => 1
    }
    if value > level {
      level = value
    }
  }
  {
    ..report,
    status: match level {
      0 => "pass_static"
      1 => "inconclusive"
      2 => "fail"
      _ => "input_error"
    },
  }
}

///|
fn issue(
  report : Report,
  code : String,
  status : String,
  subject : Bytes,
  requirement : Bytes?,
  chain : Array[ByteName],
  message : String,
  action : String,
) -> Unit {
  report.findings.push({
    code,
    status,
    subject: name(subject),
    requirement: requirement.map(name),
    dependency_chain: chain,
    explanation: message,
    suggested_action: action,
  })
}
