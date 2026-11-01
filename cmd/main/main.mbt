///|
fn main {
  let args = @env.args()
  let start = args.length() - 9
  if start < 0 ||
    args[start] != "check" ||
    args[start + 1] != "--snapshot" ||
    args[start + 3] != "--entry" ||
    args[start + 5] != "--scope" ||
    args[start + 6] != "dependencies" ||
    args[start + 7] != "--format" ||
    (args[start + 8] != "json" && args[start + 8] != "text") {
    println(
      "usage: moonloadcheck check --snapshot <directory> --entry <target-path> --scope dependencies --format <json|text>",
    )
    @sys.exit(3)
  }
  try {
    let folder = args[start + 2]
    let snapshot = @snapshot.load(
      @fs.read_file_to_string(folder + "/manifest.json"),
      digest => @fs.read_file_to_bytes(folder + "/blobs/" + digest),
    )
    let report = @analysis.check_dependencies(
      snapshot,
      @utf8.encode(args[start + 4]),
    )
    if args[start + 8] == "json" {
      println(report.to_json().stringify())
    } else {
      println("\{report.status}: interpreter, machine, dependency resolution")
      println("Not checked: \{report.not_checked.join(", ")}")
      for finding in report.findings {
        println(
          "\{finding.code} [\{finding.status}] \{Json::string(finding.subject.display).stringify()}: \{finding.explanation}",
        )
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
    @sys.exit(report.exit_code())
  } catch {
    error => {
      let result : Json = {
        "schema_version": 1,
        "status": "input_error",
        "message": "\{error}",
      }
      println(result.stringify())
      @sys.exit(3)
    }
  }
}
