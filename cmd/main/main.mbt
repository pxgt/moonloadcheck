///|
fn load(folder : String) -> @snapshot.Snapshot raise {
  @snapshot.load(@fs.read_file_to_string(folder + "/manifest.json"), digest => {
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
  let start = args.length() - 9
  if start >= 0 &&
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
  if start >= 0 &&
    args[start] == "diff" &&
    args[start + 1] == "--before" &&
    args[start + 3] == "--after" &&
    args[start + 5] == "--entries" &&
    args[start + 7] == "--format" &&
    ["json", "text"].contains(args[start + 8]) {
    let input = @fs.read_file_to_string(args[start + 6])
    guard input.length() <= 1048576 else {
      raise @analysis.ReportError("entries file exceeds 1 MiB")
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
  let start = args.length() - 5
  if start >= 0 &&
    args[start] == "explain" &&
    args[start + 1] == "--report" &&
    args[start + 3] == "--finding" {
    let report = @analysis.read_report(@fs.read_file_to_string(args[start + 2]))
    println(report.explain(args[start + 4]).to_json().stringify())
    return 0
  }
  raise @analysis.ReportError(
    "usage: moonloadcheck check --snapshot DIR --entry PATH --scope dependencies|compatibility --format json|text; diff --before DIR --after DIR --entries JSON_FILE --format json|text; explain --report JSON_FILE --finding ID",
  )
}

///|
fn main {
  @sys.exit(dispatch(@env.args())) catch {
    error => {
      let result : Json = {
        "schema_version": 2,
        "status": "input_error",
        "message": "\{error}",
      }
      println(result.stringify())
      @sys.exit(3)
    }
  }
}
