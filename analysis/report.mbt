///|
pub(all) struct ByteName {
  display : String
  hex : String
} derive(ToJson, @json.FromJson)

///|
pub extend ByteName with ToJson::{to_json}

///|
pub extend ByteName with @json.FromJson::{from_json}

///|
fn name(bytes : Bytes) -> ByteName {
  { display: @utf8.decode_lossy(bytes[:]), hex: @hex.encode(bytes[:]), }
}

///|
pub(all) struct Candidate {
  source : String
  path : ByteName
  outcome : String
} derive(ToJson, @json.FromJson)

///|
pub extend Candidate with ToJson::{to_json}

///|
pub extend Candidate with @json.FromJson::{from_json}

///|
pub(all) struct DependencyEdge {
  consumer : ByteName
  needed : ByteName
  selected : ByteName?
  trace : Array[Candidate]
} derive(ToJson, @json.FromJson)

///|
pub extend DependencyEdge with ToJson::{to_json}

///|
pub extend DependencyEdge with @json.FromJson::{from_json}

///|
pub(all) struct Finding {
  id : String
  code : String
  status : String
  subject : ByteName
  requirement : ByteName?
  dependency_chain : Array[ByteName]
  explanation : String
  suggested_action : String
  version : ByteName?
  provider : ByteName?
  reference_offsets : Array[String]
} derive(ToJson, @json.FromJson)

///|
pub extend Finding with ToJson::{to_json}

///|
pub extend Finding with @json.FromJson::{from_json}

///|
pub(all) struct LoadedObject {
  path : ByteName
  file_id : String
  sha256 : String
  machine : Int32
} derive(ToJson, @json.FromJson)

///|
pub extend LoadedObject with ToJson::{to_json}

///|
pub extend LoadedObject with @json.FromJson::{from_json}

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
  version_checks : Array[VersionCheck]
  symbol_checks : Array[SymbolCheck]
  symbol_scope : Array[ByteName]
} derive(ToJson, @json.FromJson)

///|
pub extend Report with ToJson::{to_json}

///|
pub extend Report with @json.FromJson::{from_json}

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
  version? : Bytes,
  provider? : Bytes,
  offsets~ : Array[String] = [],
) -> Unit {
  let version_hex = version.map(v => @hex.encode(v[:])).unwrap_or("")
  let requirement_hex = requirement.map(v => @hex.encode(v[:])).unwrap_or("")
  let key = "\{code}|\{@hex.encode(subject[:])}|\{requirement_hex}|\{version_hex}"
  report.findings.push({
    id: @snapshot.sha256(@utf8.encode(key)),
    code,
    status,
    subject: name(subject),
    requirement: requirement.map(name),
    dependency_chain: chain,
    explanation: message,
    suggested_action: action,
    version: version.map(name),
    provider: provider.map(name),
    reference_offsets: offsets,
  })
}

///|
pub(all) struct VersionCheck {
  consumer : ByteName
  provider : ByteName?
  version : ByteName
  weak : Bool
  status : String
  explanation : String
} derive(ToJson, @json.FromJson)

///|
pub extend VersionCheck with ToJson::{to_json}

///|
pub extend VersionCheck with @json.FromJson::{from_json}

///|
pub(all) struct SymbolCheck {
  consumer : ByteName
  symbol : ByteName
  version : ByteName?
  provider : ByteName?
  definition_version : ByteName?
  lookup_policy : String
  weak : Bool
  status : String
  phase : String
  reference_offsets : Array[String]
  relocation_types : Array[Int32]
} derive(ToJson, @json.FromJson)

///|
pub extend SymbolCheck with ToJson::{to_json}

///|
pub extend SymbolCheck with @json.FromJson::{from_json}
