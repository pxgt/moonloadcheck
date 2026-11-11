///|
priv struct Node {
  path : Bytes
  origin : Bytes
  id : String
  object : @model.ElfObject
  parent : Int32?
  aliases : Array[Bytes]
}

///|
fn chain(nodes : Array[Node], index : Int32) -> Array[ByteName] {
  let result = []
  let mut current = Some(index)
  while current is Some(i) {
    result.push(name(nodes[i].path))
    current = nodes[i].parent
  }
  let ordered = []
  for i = result.length() - 1; i >= 0; i = i - 1 {
    ordered.push(result[i])
  }
  ordered
}

///|
fn load_object(
  snapshot : @snapshot.Snapshot,
  id : String,
) -> @model.ElfObject raise @model.ElfError {
  match snapshot.content(id) {
    Some(bytes) => @elf.read(bytes)
    None => raise @model.ElfError::Malformed("snapshot content absent")
  }
}

///|
fn parse_issue(
  report : Report,
  path : Bytes,
  requirement : Bytes?,
  chain : Array[ByteName],
  error : @model.ElfError,
) -> Unit {
  match error {
    @model.ElfError::Malformed(message) =>
      issue(
        report, "MLC006", "input_error", path, requirement, chain, message, "Regenerate or replace the malformed ELF input.",
      )
    @model.ElfError::Unsupported(message) =>
      issue(
        report, "MLC008", "unknown", path, requirement, chain, message, "Use a supported ELF profile or retain this coverage gap.",
      )
    @model.ElfError::ResourceLimit(message) =>
      issue(
        report, "MLC009", "unknown", path, requirement, chain, message, "Reduce input size or review the configured resource limit.",
      )
  }
}

///|
fn register(
  snapshot : @snapshot.Snapshot,
  report : Report,
  nodes : Array[Node],
  resolved : @snapshot.Resolved,
  lookup : Bytes,
  object : @model.ElfObject,
  parent : Int32?,
  requested_name : Bytes,
) -> Int32 {
  let id = match resolved.entry {
    @snapshot.Entry::File(id) => id
    _ => ""
  }
  for i = 0; i < nodes.length(); i = i + 1 {
    if nodes[i].id == id {
      nodes[i].aliases.push(requested_name)
      return i
    }
  }
  let aliases = [requested_name, lookup]
  if object.soname is Some(soname) {
    aliases.push(soname)
  }
  let index = nodes.length()
  nodes.push({
    path: resolved.path,
    origin: directory(lookup),
    id,
    object,
    parent,
    aliases,
  })
  report.objects.push({
    path: name(resolved.path),
    file_id: id,
    sha256: snapshot.digest(id).unwrap_or(""),
    machine: object.machine,
  })
  index
}

///|
fn search_paths(
  nodes : Array[Node],
  index : Int32,
  profile : @snapshot.Profile,
  needed : Bytes,
  cache : CacheState,
) -> Array[(String, Bytes)] raise {
  let node = nodes[index]
  let cwd = @hex.decode(profile.cwd_hex[:])
  let expanded = expand(needed, node.origin, profile)
  if contains(expanded, b'/') {
    return [("DT_NEEDED path", absolute(expanded, cwd))]
  }
  let directories : Array[(String, Bytes)] = []
  if node.object.runpath is None {
    let mut current = Some(index)
    while current is Some(i) {
      let ancestor = nodes[i]
      if ancestor.object.runpath is None && ancestor.object.rpath is Some(rpath) {
        for dir in path_list(rpath, ancestor.origin, profile) {
          directories.push(("RPATH", dir))
        }
      }
      current = ancestor.parent
    }
  }
  for hex in profile.library_path_hex {
    directories.push(
      ("library_path", expand(@hex.decode(hex[:]), nodes[0].origin, profile)),
    )
  }
  if node.object.runpath is Some(runpath) {
    for dir in path_list(runpath, node.origin, profile) {
      directories.push(("RUNPATH", dir))
    }
  }
  let candidates = []
  guard directories.length() <= 4096 else {
    raise UnmodeledPath("combined search list exceeds 4096 entries")
  }
  for (source, dir) in directories {
    let path = if dir.is_empty() {
      expanded
    } else {
      concat(concat(dir, b"/"), expanded)
    }
    candidates.push((source, absolute(path, cwd)))
  }
  if cache_candidate(cache, profile, expanded, node.object.no_default_lib)
    is Some(candidate) {
    candidates.push(candidate)
  }
  if !node.object.no_default_lib {
    for hex in profile.default_dirs_hex {
      candidates.push(
        ("default", concat(concat(@hex.decode(hex[:]), b"/"), expanded)),
      )
    }
  }
  candidates
}

///|
fn run(
  snapshot : @snapshot.Snapshot,
  entry : Bytes,
  report : Report,
  nodes : Array[Node],
) -> Unit raise {
  let profile = snapshot.profile()
  let resolved = snapshot.resolve(entry)
  let root_id = match resolved.entry {
    @snapshot.Entry::File(id) => id
    _ => raise @model.ElfError::Malformed("entry is not a regular file")
  }
  let object = load_object(snapshot, root_id)
  if object.machine != profile.machine {
    issue(
      report,
      "MLC003",
      "fail",
      entry,
      None,
      [],
      "Entry architecture differs from the target profile.",
      "Build the program for the target architecture.",
    )
    return
  }
  ignore(
    register(
      snapshot,
      report,
      nodes,
      resolved,
      resolved.path,
      object,
      None,
      entry,
    ),
  )
  if (
      profile.rule_revision != "glibc-2.35-controlled-v1" &&
      profile.rule_revision != "glibc-2.35-controlled-v2" &&
      profile.rule_revision != "ubuntu-noble-2.39-0ubuntu8-v1"
    ) ||
    profile.loader_family != "glibc" ||
    (
      profile.cache_mode != "disabled" &&
      !(profile.rule_revision == "glibc-2.35-controlled-v2" &&
      profile.cache_mode == "glibc-cache-v1")
    ) ||
    profile.hwcaps_policy != "none" ||
    profile.secure_execution ||
    !profile.preload.is_empty() ||
    !profile.audit.is_empty() {
    issue(
      report,
      "MLC007",
      "unknown",
      entry,
      None,
      [],
      "Profile requires loader behavior outside the controlled dependency model.",
      "Supply an explicit supported profile; do not relabel an uncontrolled environment.",
    )
    return
  }
  match object.interpreter {
    None => {
      issue(
        report,
        "MLC008",
        "unknown",
        entry,
        None,
        [],
        "Entry has no interpreter; shared-object and static-PIE entry modes are not modeled.",
        "Select a dynamically linked executable entry.",
      )
      return
    }
    Some(interpreter) => {
      if interpreter != @hex.decode(profile.loader_path_hex[:]) {
        issue(
          report,
          "MLC007",
          "unknown",
          entry,
          Some(interpreter),
          [],
          "Entry interpreter differs from the declared loader profile.",
          "Capture the actual interpreter and its loading profile.",
        )
        return
      }
      try snapshot.resolve(interpreter) catch {
        _ =>
          issue(
            report,
            "MLC001",
            "fail",
            entry,
            Some(interpreter),
            [],
            "ELF interpreter cannot be reached in the target namespace.",
            "Provide the matching interpreter in the target root.",
          )
      } noraise {
        found =>
          match found.entry {
            @snapshot.Entry::File(id) =>
              try load_object(snapshot, id) catch {
                error => parse_issue(report, interpreter, None, [], error)
              } noraise {
                loader =>
                  if loader.machine != profile.machine {
                    issue(
                      report,
                      "MLC003",
                      "fail",
                      interpreter,
                      None,
                      [],
                      "Interpreter architecture differs from the target.",
                      "Capture the matching loader.",
                    )
                  } else {
                    ignore(
                      register(
                        snapshot,
                        report,
                        nodes,
                        found,
                        interpreter,
                        loader,
                        Some(0),
                        interpreter,
                      ),
                    )
                  }
              }
            _ =>
              issue(
                report,
                "MLC001",
                "fail",
                entry,
                Some(interpreter),
                [],
                "ELF interpreter is not a regular file.",
                "Repair the target interpreter path.",
              )
          }
      }
    }
  }
  let cache = read_cache(snapshot)
  let mut index = 0
  let mut steps = 0
  while index < nodes.length() {
    let node = nodes[index]
    let dependency_chain = chain(nodes, index)
    if !node.object.unsupported.is_empty() {
      issue(
        report,
        "MLC008",
        "unknown",
        node.path,
        None,
        dependency_chain,
        node.object.unsupported.join("; "),
        "Review unsupported dynamic loading behavior.",
      )
      index += 1
      continue
    }
    for needed in node.object.needed {
      steps += 1
      if steps > 16384 || nodes.length() >= 2048 {
        issue(
          report,
          "MLC009",
          "unknown",
          node.path,
          Some(needed),
          dependency_chain,
          "Dependency graph resource limit reached.",
          "Reduce the graph or review analysis limits.",
        )
        return
      }
      let trace = []
      let mut selected = None
      let expanded = expand(needed, node.origin, profile) catch {
        UnmodeledPath(message) => {
          issue(
            report,
            "MLC008",
            "unknown",
            node.path,
            Some(needed),
            dependency_chain,
            message,
            "Declare and validate the additional dynamic token.",
          )
          report.edges.push({
            consumer: name(node.path),
            needed: name(needed),
            selected: None,
            trace,
          })
          continue
        }
      }
      for loaded in nodes {
        if loaded.aliases.contains(expanded) {
          selected = Some(name(loaded.path))
          trace.push({
            source: "already_loaded",
            path: name(loaded.path),
            outcome: "reused",
          })
          break
        }
      }
      let mut uncertain = false
      if selected is None {
        let candidates = search_paths(nodes, index, profile, needed, cache) catch {
          error => {
            issue(
              report,
              "MLC008",
              "unknown",
              node.path,
              Some(needed),
              dependency_chain,
              "\{error}",
              "Review the unmodeled search token.",
            )
            report.edges.push({
              consumer: name(node.path),
              needed: name(needed),
              selected: None,
              trace,
            })
            continue
          }
        }
        for (source, path) in candidates {
          if source == "cache_nodeflib" {
            trace.push({ source, path: name(path), outcome: "filtered", })
            continue
          }
          if source == "cache_unknown" {
            trace.push({ source, path: name(path), outcome: "unknown", })
            issue(
              report,
              "MLC007",
              "unknown",
              node.path,
              Some(needed),
              dependency_chain,
              "Cache selection requires unsupported format, hardware or OS-version evidence.",
              "Capture supported cache conditions before selecting a provider.",
            )
            uncertain = true
            break
          }
          steps += 1
          if steps > 16384 {
            issue(
              report,
              "MLC009",
              "unknown",
              node.path,
              Some(needed),
              dependency_chain,
              "Search resource limit reached.",
              "Reduce the search scope or review analysis limits.",
            )
            return
          }
          let found = snapshot.resolve(path) catch {
            @snapshot.PathError::TooManySteps => {
              uncertain = true
              issue(
                report,
                "MLC009",
                "unknown",
                node.path,
                Some(needed),
                dependency_chain,
                "Target path resolution limit reached.",
                "Review the path and resolution limits.",
              )
              break
            }
            error => {
              let outcome = match error {
                @snapshot.PathError::MissingPath(_) => "missing"
                @snapshot.PathError::NotDirectory(_) => "not_directory"
                @snapshot.PathError::TooManyLinks => "symlink_limit"
                _ => "invalid_path"
              }
              trace.push({ source, path: name(path), outcome, })
              if error is @snapshot.PathError::MissingPath(_) {
                continue
              }
              issue(
                report,
                "MLC008",
                "unknown",
                node.path,
                Some(needed),
                dependency_chain,
                "Exceptional path lookup requires unmodeled search-group handling.",
                "Repair the path or retain this unresolved search result.",
              )
              uncertain = true
              break
            }
          }
          let id = match found.entry {
            @snapshot.Entry::File(id) => id
            _ => {
              trace.push({ source, path: name(path), outcome: "not_regular", })
              issue(
                report,
                "MLC002",
                "fail",
                node.path,
                Some(needed),
                dependency_chain,
                "A directory occupies the selected library candidate; glibc stops with a read error.",
                "Replace the directory with the required library or repair the search path.",
              )
              uncertain = true
              break
            }
          }
          let provider = load_object(snapshot, id) catch {
            error => {
              trace.push({
                source,
                path: name(path),
                outcome: "unreadable_elf",
              })
              parse_issue(report, path, Some(needed), dependency_chain, error)
              uncertain = true
              break
            }
          }
          if provider.machine != profile.machine {
            trace.push({ source, path: name(path), outcome: "wrong_machine", })
            continue
          }
          if provider.object_type != 3 || provider.pie {
            trace.push({
              source,
              path: name(path),
              outcome: "not_shared_object",
            })
            issue(
              report,
              "MLC002",
              "fail",
              path,
              Some(needed),
              dependency_chain,
              "An executable cannot be loaded as a shared-library dependency.",
              "Provide a shared library for this dependency.",
            )
            uncertain = true
            break
          }
          let loaded = register(
            snapshot,
            report,
            nodes,
            found,
            path,
            provider,
            Some(index),
            expanded,
          )
          selected = Some(name(nodes[loaded].path))
          trace.push({ source, path: name(path), outcome: "selected", })
          break
        }
      }
      if selected is None && !uncertain {
        issue(
          report,
          "MLC002",
          "fail",
          node.path,
          Some(needed),
          dependency_chain,
          "No loadable dependency was found in the declared search order. RUNPATH applies only to direct dependencies.",
          "Provide the missing library or fix the requesting object's search path.",
        )
      }
      report.edges.push({
        consumer: name(node.path),
        needed: name(needed),
        selected,
        trace,
      })
    }
    index += 1
  }
}

///|
/// Shared driver; compatibility additionally checks versions and symbol lookup.
fn check_with_scope(
  snapshot : @snapshot.Snapshot,
  entry : Bytes,
  compatibility : Bool,
) -> Report {
  let report : Report = {
    schema_version: 2,
    tool_version: "0.3.0-dev",
    rule_revision: snapshot.profile().rule_revision,
    snapshot_sha256: snapshot.manifest_digest(),
    entry: name(entry),
    checked_scope: ["interpreter", "machine", "dependency-resolution"],
    not_checked: [
      "symbol-versions", "symbol-resolution", "relocations", "CPU features", "file permissions",
      "application behavior",
    ],
    status: "inconclusive",
    objects: [],
    edges: [],
    findings: [],
    version_checks: [],
    symbol_checks: [],
    symbol_scope: [],
  }
  let nodes = []
  try {
    run(snapshot, entry, report, nodes)
    if compatibility {
      report.checked_scope.push("version-requirements")
      report.checked_scope.push("symbol-resolution")
      check_linkage(snapshot, nodes, report)
    }
  } catch {
    @model.ElfError::Malformed(message) =>
      issue(
        report,
        "MLC006",
        "input_error",
        entry,
        None,
        [],
        message,
        "Repair the input.",
      )
    @model.ElfError::Unsupported(message) =>
      issue(
        report,
        "MLC008",
        "unknown",
        entry,
        None,
        [],
        message,
        "Use a supported entry.",
      )
    @model.ElfError::ResourceLimit(message) =>
      issue(
        report,
        "MLC009",
        "unknown",
        entry,
        None,
        [],
        message,
        "Review analysis limits.",
      )
    error =>
      issue(
        report,
        "MLC006",
        "input_error",
        entry,
        None,
        [],
        "\{error}",
        "Check the entry and snapshot.",
      )
  }
  let report = if compatibility {
    {
      ..report,
      not_checked: [
        "relocation-values", "IFUNC resolver results", "TLS layout", "CPU features",
        "file permissions", "application behavior", "type ABI",
      ],
    }
  } else {
    report
  }
  finish(report)
}

///|
pub fn check_dependencies(
  snapshot : @snapshot.Snapshot,
  entry : Bytes,
) -> Report {
  check_with_scope(snapshot, entry, false)
}

///|
pub fn check_compatibility(
  snapshot : @snapshot.Snapshot,
  entry : Bytes,
) -> Report {
  check_with_scope(snapshot, entry, true)
}
