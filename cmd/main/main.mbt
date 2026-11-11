///|
fn load(folder : String) -> @snapshot.Snapshot raise {
  @snapshot.load(read_text(folder + "/manifest.json"), digest => {
    @fs.read_file_to_bytes(folder + "/blobs/" + digest)
  })
}

///|
fn show(report : @analysis.Report) -> Unit {
  println("\{report.status}: \{report.checked_scope.join(", ")}")
  println("Not checked: \{report.not_checked.join(", ")}")
  for finding in report.findings {
    println(
      "\{finding.code} [\{finding.status}] \{Json::string(finding.subject.display).stringify()}: \{finding.explanation}",
    )
    println("  finding: \{finding.id}")
    if !finding.dependency_chain.is_empty() {
      println(
        "  chain: \{finding.dependency_chain.map(item => Json::string(item.display).stringify()).join(" -> ")}",
      )
    }
    println("  action: \{finding.suggested_action}")
    for step in @presentation.guidance(finding.code) {
      println("  guide: \{step}")
    }
  }
  for edge in report.edges {
    println(
      "\{Json::string(edge.consumer.display).stringify()} needs \{Json::string(edge.needed.display).stringify()}",
    )
    for candidate in edge.trace {
      println(
        "  \{candidate.source}: \{Json::string(candidate.path.display).stringify()} [\{candidate.outcome}]",
      )
    }
  }
}

///|
fn dispatch(args : Array[String]) -> Int32 raise {
  if args == ["--help"] {
    println(usage())
    return 0
  }
  let start = 0
  if args.length() == 5 &&
    args[0] == "report" &&
    args[1] == "--input" &&
    args[3] == "--format" &&
    ["html", "summary"].contains(args[4]) {
    let (output, code) = @presentation.present(
      read_text(args[2]),
      html=args[4] == "html",
    )
    println(output)
    return code
  }
  if args.length() == 9 &&
    args[start] == "check" &&
    args[start + 1] == "--snapshot" &&
    args[start + 3] == "--entry" &&
    args[start + 5] == "--scope" &&
    ["dependencies", "compatibility"].contains(args[start + 6]) &&
    args[start + 7] == "--format" &&
    ["json", "text"].contains(args[start + 8]) {
    let snapshot = load(args[start + 2])
    let entry = @utf8.encode(args[start + 4])
    let report = if args[start + 6] == "dependencies" {
      @analysis.check_dependencies(snapshot, entry)
    } else {
      @analysis.check_compatibility(snapshot, entry)
    }
    if args[start + 8] == "json" {
      println(report.to_json().stringify())
    } else {
      show(report)
    }
    return report.exit_code()
  }
  if args.length() == 9 &&
    args[start] == "diff" &&
    args[start + 1] == "--before" &&
    args[start + 3] == "--after" &&
    args[start + 5] == "--entries" &&
    args[start + 7] == "--format" &&
    ["json", "text"].contains(args[start + 8]) {
    let input = read_text(args[start + 6])
    guard input.length() <= 1048576 else {
      raise @analysis.ReportError(
        "entries file exceeds 1048576 UTF-16 code units",
      )
    }
    let entries : Array[String] = @json.from_json(@json.parse(input[:]))
    let report = @analysis.compare(
      load(args[start + 2]),
      load(args[start + 4]),
      entries.map(entry => @utf8.encode(entry)),
    )
    if args[start + 8] == "json" {
      println(report.to_json().stringify())
    } else {
      println("\{report.status}: explicit-consumer compatibility comparison")
      for entry in report.entries {
        println(
          "\{Json::string(entry.entry.display).stringify()}: \{entry.before.status} -> \{entry.after.status}; application_changed=\{entry.application_changed}",
        )
        for change in entry.changes {
          println("  \{change.classification}: \{change.finding_id}")
        }
        show(entry.after)
      }
    }
    return report.exit_code()
  }
  if args.length() == 5 &&
    args[start] == "explain" &&
    args[start + 1] == "--report" &&
    args[start + 3] == "--finding" {
    let report = @analysis.read_report(read_text(args[start + 2]))
    println(report.explain(args[start + 4]).to_json().stringify())
    return 0
  }
  raise CommandError("arguments", usage())
}

///|
#cfg(target="js")
extern "js" fn finish_exit(code : Int32) -> Unit =
  #| (code) => { process.exitCode = code; }

///|
#cfg(target="native")
extern "C" fn finish_exit(code : Int32) -> Unit = "exit"

///|
fn main {
  // Node's stdout pipe is asynchronous on Linux. Let pending writes drain
  // instead of calling process.exit immediately after a large JSON report.
  finish_exit(dispatch(arguments())) catch {
    error => {
      let (kind, message) = describe_error(error)
      let result : Json = {
        "schema_version": 2,
        "status": "input_error",
        "error_kind": kind,
        "message": message,
      }
      println(result.stringify())
      finish_exit(3)
    }
  }
}

///|
fn usage() -> String {
  "usage: moonloadcheck check --snapshot DIR --entry PATH --scope dependencies|compatibility --format json|text; diff --before DIR --after DIR --entries JSON_FILE --format json|text; explain --report JSON_FILE --finding ID; report --input JSON_FILE --format html|summary; --help"
}

///|
priv suberror CommandError {
  CommandError(String, String)
}

///|
fn read_text(path : String) -> String raise {
  @fs.read_file_to_string(path) catch {
    @fs.IOError(_) =>
      raise CommandError(
        "io",
        "cannot read file: " + Json::string(path).stringify(),
      )
  }
}

///|
#cfg(target="js")
fn arguments() -> Array[String] {
  let all = @env.args()
  if all.length() < 2 {
    []
  } else {
    all[2:].to_owned()
  }
}

///|
#cfg(target="native")
fn arguments() -> Array[String] {
  let all = @env.args()
  if all.is_empty() {
    []
  } else {
    all[1:].to_owned()
  }
}

///|
fn describe_error(error : Error) -> (String, String) {
  match error {
    CommandError(kind, message) => (kind, message)
    @analysis.ReportError(message) => ("report", message)
    @snapshot.InvalidSnapshot(message) => ("snapshot", message)
    @snapshot.ContentMismatch(message) =>
      ("snapshot", "content mismatch: " + message)
    @snapshot.SnapshotLimit(message) => ("snapshot", message)
    @snapshot.PathError::InvalidPath(path) =>
      ("path", "invalid path bytes: " + @hex.encode(path[:]))
    @snapshot.PathError::DuplicatePath(path) =>
      ("path", "duplicate path bytes: " + @hex.encode(path[:]))
    @snapshot.PathError::MissingPath(path) =>
      ("path", "missing path bytes: " + @hex.encode(path[:]))
    @snapshot.PathError::NotDirectory(path) =>
      ("path", "not a directory, path bytes: " + @hex.encode(path[:]))
    @snapshot.PathError::TooManyLinks => ("path", "too many symbolic links")
    @snapshot.PathError::TooManySteps =>
      ("path", "path traversal step limit exceeded")
    @json.JsonDecodeError(details) =>
      ("json", @json.JsonDecodeError(details).to_string())
    @json.ParseError::InvalidChar(pos, char) =>
      ("json", @json.ParseError::InvalidChar(pos, char).to_string())
    @json.ParseError::InvalidEof => ("json", "unexpected end of JSON input")
    @json.ParseError::InvalidNumber(pos, value) =>
      ("json", @json.ParseError::InvalidNumber(pos, value).to_string())
    @json.ParseError::InvalidIdentEscape(pos) =>
      ("json", @json.ParseError::InvalidIdentEscape(pos).to_string())
    @json.ParseError::DepthLimitExceeded =>
      ("json", "JSON nesting depth limit exceeded")
    @json.ParseError::DuplicateKey(pos, key) =>
      ("json", @json.ParseError::DuplicateKey(pos, key).to_string())
    _ => ("other", error.to_string())
  }
}
