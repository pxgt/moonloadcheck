///|
priv struct Version {
  name : Bytes
  hash : UInt64
  hidden : Bool
  provider : Bytes?
}

///|
fn indexed_versions(linkage : @model.Linkage) -> Map[Int32, Version] {
  let versions : Map[Int32, Version] = Map([])
  for need in linkage.version_needs {
    versions[need.index] = {
      name: need.name,
      hash: need.hash,
      hidden: need.hidden,
      provider: Some(need.provider),
    }
  }
  for def in linkage.version_defs {
    if def.index >= 2 {
      versions[def.index] = {
        name: def.name,
        hash: def.hash,
        hidden: false,
        provider: None,
      }
    }
  }
  versions
}

///|
fn exported(symbol : @model.DynamicSymbol) -> Bool {
  symbol.lookupable &&
  symbol.section != 0 &&
  symbol.version_index != 0 &&
  symbol.visibility != 1 &&
  symbol.visibility != 2 &&
  (symbol.binding == 1 || symbol.binding == 2 || symbol.binding == 10) &&
  (
    symbol.kind == 0 ||
    symbol.kind == 1 ||
    symbol.kind == 2 ||
    symbol.kind == 5 ||
    symbol.kind == 6 ||
    symbol.kind == 10
  ) &&
  (symbol.value != 0 || symbol.section == 0xfff1 || symbol.kind == 6)
}

///|
fn supported_reference(machine : Int32, kind : Int32) -> Bool {
  if machine == 62 {
    [1, 2, 5, 6, 7, 10, 11, 16, 17, 18, 36].contains(kind)
  } else {
    [257, 258, 259, 260, 261, 262, 1024, 1025, 1026, 1028, 1029, 1030, 1031].contains(
      kind,
    )
  }
}

///|
fn scope_order(nodes : Array[Node], report : Report) -> Array[Int32] {
  let order = [0]
  let seen : Map[Int32, Bool] = Map([(0, true)])
  let indices : Map[String, Int32] = Map([])
  for i = 0; i < nodes.length(); i = i + 1 {
    indices[@hex.encode(nodes[i].path[:])] = i
  }
  let mut i = 0
  while i < order.length() {
    for edge in report.edges {
      if edge.consumer.hex == @hex.encode(nodes[order[i]].path[:]) &&
        edge.selected is Some(selected) {
        if indices.get(selected.hex) is Some(next) && seen.get(next) is None {
          order.push(next)
          seen[next] = true
        }
      }
    }
    i += 1
  }
  // The interpreter is already mapped, but is not inserted before the normal
  // breadth-first symbol scope. Append it if no NEEDED edge brought it in.
  for i = 0; i < nodes.length(); i = i + 1 {
    if seen.get(i) is None {
      order.push(i)
    }
  }
  order
}

///|
fn check_linkage(
  snapshot : @snapshot.Snapshot,
  nodes : Array[Node],
  report : Report,
) -> Unit raise {
  if !report.findings.is_empty() || nodes.is_empty() {
    issue(
      report,
      "MLC007",
      "unknown",
      @hex.decode(report.entry.hex[:]),
      None,
      [],
      "Symbol analysis requires a complete, supported dependency scope.",
      "Resolve dependency findings first.",
    )
    return
  }
  let linkages : Array[@model.Linkage] = []
  let mut symbol_total = 0
  let mut reference_total = 0
  let mut version_total = 0
  for node in nodes {
    try @elf.read_linkage(snapshot.content(node.id).unwrap()) catch {
      error => {
        parse_issue(report, node.path, None, [], error)
        return
      }
    } noraise {
      linkage => {
        symbol_total += linkage.symbols.length()
        reference_total += linkage.references.length()
        version_total += linkage.version_defs.length() +
          linkage.version_needs.length()
        guard symbol_total <= 200000 &&
          reference_total <= 1000000 &&
          version_total <= 100000 else {
          raise @model.ElfError::ResourceLimit(
            "startup scope exceeds symbol/reference budget",
          )
        }
        linkages.push(linkage)
      }
    }
  }
  let scope = scope_order(nodes, report)
  let versions = linkages.map(indexed_versions)
  for index in scope {
    report.symbol_scope.push(name(nodes[index].path))
  }
  let definitions : Map[Bytes, Array[(Int32, Int32)]] = Map([])
  for provider in scope {
    let linkage = linkages[provider]
    for index in linkage.lookup_order {
      let symbol = linkage.symbols[index]
      if exported(symbol) {
        match definitions.get(symbol.name) {
          Some(list) => list.push((provider, index))
          None => definitions[symbol.name] = [(provider, index)]
        }
      }
    }
  }
  let mut lookup_steps = 0
  for consumer = 0; consumer < nodes.length(); consumer = consumer + 1 {
    let node = nodes[consumer]
    let linkage = linkages[consumer]
    let dependency_chain = chain(nodes, consumer)
    for need in linkage.version_needs {
      let mut provider = None
      for candidate in scope {
        lookup_steps += 1
        guard lookup_steps <= 1000000 else {
          raise @model.ElfError::ResourceLimit(
            "version/symbol lookup budget exceeded",
          )
        }
        if nodes[candidate].aliases.contains(need.provider) {
          provider = Some(candidate)
          break
        }
      }
      let (status, explanation) = match provider {
        None =>
          (
            "unknown", "The version's named dependency is absent from the resolved scope.",
          )
        Some(i) => {
          let defs = linkages[i].version_defs
          if defs.is_empty() {
            (
              "pass", "glibc accepts the absent VERDEF at the version-node stage, with a warning. Symbol lookup is checked separately.",
            )
          } else if defs.any(def => {
              def.name == need.name && def.hash == need.hash
            }) {
            ("pass", "Named version node is provided.")
          } else if need.weak {
            ("pass", "An absent weak version node is not fatal.")
          } else {
            (
              "fail", "The named dependency does not provide the required version node.",
            )
          }
        }
      }
      report.version_checks.push({
        consumer: name(node.path),
        provider: provider.map(i => name(nodes[i].path)),
        version: name(need.name),
        weak: need.weak,
        status,
        explanation,
      })
      if status != "pass" {
        issue(
          report,
          if status == "fail" {
            "MLC004"
          } else {
            "MLC007"
          },
          status,
          node.path,
          Some(need.provider),
          dependency_chain,
          explanation,
          "Use a provider with the required version, or rebuild against the target baseline.",
          version=need.name,
          provider?=provider.map(i => nodes[i].path),
        )
      }
    }
    let grouped : Map[Int32, Array[@model.Reference]] = Map([])
    let reference_order = []
    for reference in linkage.references {
      if reference.relocation == 0 {
        continue
      }
      if reference.symbol_index == 0 {
        let supported = if node.object.machine == 62 {
          [8, 16, 17, 18, 36, 37].contains(reference.relocation)
        } else {
          [1027, 1028, 1029, 1030, 1031, 1032].contains(reference.relocation)
        }
        if !supported {
          issue(
            report,
            "MLC008",
            "unknown",
            node.path,
            Some(
              @utf8.encode(
                "relocation:\{reference.relocation}:\{reference.offset}",
              ),
            ),
            dependency_chain,
            "Unmodeled symbol-free relocation type: \{reference.relocation}.",
            "Validate this relocation with the target loader.",
            offsets=[reference.offset.to_string()],
          )
        }
        continue
      }
      // COPY uses a different lookup scope from ordinary references to the same
      // symbol (including GLOB_DAT references in a native MoonBit executable).
      let copy_kind = if node.object.machine == 62 { 5 } else { 1024 }
      let key = reference.symbol_index * 2 +
        (if reference.relocation == copy_kind { 1 } else { 0 })
      match grouped.get(key) {
        Some(list) => list.push(reference)
        None => {
          grouped[key] = [reference]
          reference_order.push(key)
        }
      }
    }
    for key in reference_order {
      let index = key / 2
      let refs = grouped[key]
      let symbol = linkage.symbols[index]
      let desired = versions[consumer].get(symbol.version_index)
      let offsets = refs.map(reference => reference.offset.to_string())
      let kinds = refs.map(reference => reference.relocation)
      let copy = kinds.contains(
        if node.object.machine == 62 {
          5
        } else {
          1024
        },
      )
      let tls = kinds.any(kind => {
        if node.object.machine == 62 {
          [16, 17, 18, 36].contains(kind)
        } else {
          [1028, 1029, 1030, 1031].contains(kind)
        }
      })
      let phase = if linkage.bind_now ||
        refs.any(reference => reference.table != "JMPREL") {
        "startup"
      } else {
        "startup-or-first-call"
      }
      let mut unknown = !kinds.all(kind => {
          supported_reference(node.object.machine, kind)
        }) ||
        (
          copy &&
          (
            consumer != 0 ||
            symbol.kind != 1 ||
            symbol.section == 0 ||
            symbol.section >= 0xff00 ||
            symbol.visibility != 0 ||
            (symbol.binding != 1 && symbol.binding != 2) ||
            symbol.size == 0 ||
            refs.length() != 1 ||
            refs[0].table != "RELA" ||
            refs[0].offset != symbol.value
          )
        ) ||
        symbol.binding == 10 ||
        symbol.visibility == 3 ||
        linkage.symbolic
      let mut selected = None
      let mut rejected_version_table = None
      if !copy &&
        symbol.section != 0 &&
        (symbol.binding == 0 || symbol.visibility != 0) {
        selected = Some((consumer, index))
      } else {
        let candidates = definitions.get(symbol.name).unwrap_or([])
        let search = if linkage.symbolic {
          let self_first = candidates.filter(pair => pair.0 == consumer)
          for pair in candidates {
            if pair.0 != consumer {
              self_first.push(pair)
            }
          }
          self_first
        } else {
          candidates
        }
        let mut candidate_pos = 0
        while candidate_pos < search.length() {
          let provider = search[candidate_pos].0
          let mut fallback = None
          let mut fallback_count = 0
          while candidate_pos < search.length() &&
                search[candidate_pos].0 == provider {
            lookup_steps += 1
            guard lookup_steps <= 1000000 else {
              raise @model.ElfError::ResourceLimit(
                "version/symbol lookup budget exceeded",
              )
            }
            let pair = search[candidate_pos]
            candidate_pos += 1
            if copy && provider == 0 {
              continue
            }
            let provided = linkages[provider].symbols[pair.1]
            if tls && provided.kind != 6 {
              continue
            }
            let version = versions[provider].get(provided.version_index)
            if desired is Some(required) &&
              !linkages[provider].has_versions &&
              required.provider is Some(filename) &&
              nodes[provider].aliases.contains(filename) {
              rejected_version_table = Some(provider)
              break
            }
            let matches = match desired {
              Some(required) =>
                match version {
                  Some(actual) =>
                    actual.name == required.name && actual.hash == required.hash
                  None =>
                    !linkages[provider].has_versions ||
                    (
                      !required.hidden &&
                      provided.version_index == 1 &&
                      !provided.version_hidden
                    )
                }
              None =>
                if provided.version_index >= 3 {
                  if !provided.version_hidden {
                    fallback = Some(pair)
                    fallback_count += 1
                  }
                  false
                } else {
                  true
                }
            }
            if matches {
              selected = Some(pair)
              break
            }
          }
          if selected is None &&
            rejected_version_table is None &&
            fallback_count == 1 {
            selected = fallback
          }
          if selected is Some(_) || rejected_version_table is Some(_) {
            break
          }
        }
      }
      if selected is Some((provider, symbol_index)) &&
        (
          linkages[provider].symbols[symbol_index].binding == 10 ||
          linkages[provider].symbols[symbol_index].visibility == 3
        ) {
        unknown = true
      }
      let mut size_mismatch = false
      if copy && selected is Some((provider, selected_index)) {
        let source = linkages[provider].symbols[selected_index]
        if source.kind != 1 ||
          source.section >= 0xff00 ||
          linkages[provider].symbolic {
          unknown = true
        }
        size_mismatch = source.size != symbol.size
        if size_mismatch {
          unknown = true
        }
      }
      let status = if unknown {
        "unknown"
      } else if rejected_version_table is Some(_) {
        "fail"
      } else if selected is Some(_) || symbol.binding == 2 {
        "pass"
      } else {
        "fail"
      }
      report.symbol_checks.push({
        consumer: name(node.path),
        symbol: name(symbol.name),
        version: desired.map(v => name(v.name)),
        provider: selected.map(pair => name(nodes[pair.0].path)),
        definition_version: match selected {
          Some((p, s)) =>
            versions[p]
            .get(linkages[p].symbols[s].version_index)
            .map(v => name(v.name))
          None => None
        },
        lookup_policy: if copy {
          "copy-source-excluding-executable"
        } else if symbol.section != 0 &&
          (symbol.binding == 0 || symbol.visibility != 0) {
          "local-definition"
        } else if linkage.symbolic {
          "symbolic-self-first"
        } else {
          "startup-global-scope"
        },
        weak: symbol.binding == 2,
        status,
        phase,
        reference_offsets: offsets,
        relocation_types: kinds,
        copy_destination_size: if copy {
          Some(symbol.size.to_string())
        } else {
          None
        },
        copy_source_size: if copy {
          selected.map(pair => linkages[pair.0].symbols[pair.1].size.to_string())
        } else {
          None
        },
      })
      if status != "pass" {
        issue(
          report,
          if unknown {
            "MLC008"
          } else {
            "MLC005"
          },
          status,
          node.path,
          Some(symbol.name),
          dependency_chain,
          if size_mismatch {
            "COPY source and destination sizes differ. The loader may copy only the smaller size and continue; application data compatibility is not established."
          } else if unknown {
            "This reference uses GNU_UNIQUE, protected/SYMBOLIC binding or a relocation combination outside the validated model."
          } else if rejected_version_table is Some(_) {
            "glibc rejects this versioned lookup against the named provider because that provider has no VERSYM table."
          } else {
            "No visible definition matching this referenced symbol and version exists in the startup scope."
          },
          if unknown {
            "Retain the coverage gap and validate this relocation with the target loader."
          } else {
            "Provide a matching exported symbol or rebuild the consumer against the target libraries."
          },
          version?=desired.map(v => v.name),
          provider?=match rejected_version_table {
            Some(i) => Some(nodes[i].path)
            None => selected.map(pair => nodes[pair.0].path)
          },
          offsets~,
        )
      }
    }
  }
}
