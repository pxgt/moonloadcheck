# Development report schema 2

Schema 2 adds version/symbol checks, stable finding identifiers and comparisons. It does not silently reinterpret a schema-1 dependency report. Snapshot schema remains 1. All formats remain experimental until the first release.

## Check

A report identifies tool_version, rule_revision, exact snapshot_sha256 and entry, followed by checked_scope, not_checked and status. Byte names contain display (lossy UTF-8) and hex (authoritative original bytes). Semantic comparisons never use display.

- objects records mapped paths, file identity, content digest and machine.
- edges records each consumer, requested dependency, selected path and ordered search trace.
- symbol_scope records startup lookup order; it differs from mapping order.
- version_checks records named-provider requirements independently of symbol references.
- symbol_checks records actual relocation-referenced names, requested versions, selected providers/definition versions, lookup policy, reference offsets/types and startup versus lazy phase.
- findings contains id, code, status, subject, optional requirement/version/provider, dependency chain, explanation, suggested action and reference offsets.

Offsets are decimal strings so JavaScript consumers do not lose ELF64 precision. Optional fields are omitted, never JSON null. read_report validates schema/status and decodes the typed report; it does not authenticate the saved report or re-run analysis.

Finding IDs hash code, raw subject, requirement and requested version. They intentionally exclude the selected provider and snapshot digest so an unchanged unmet requirement can be classified as existing across snapshots. Symbol-free unsupported relocations include kind/offset in their requirement identity.

| Code | Meaning |
| --- | --- |
| MLC001 | Interpreter problem |
| MLC002 | Dependency resolution failure |
| MLC003 | Architecture mismatch |
| MLC004 | Required version node unavailable |
| MLC005 | Referenced symbol/version cannot be resolved |
| MLC006 | Invalid input evidence |
| MLC007 | Incomplete scope or version-provider evidence |
| MLC008 | Unsupported behavior |
| MLC009 | Analysis resource limit |

## Compare

The diff command reads two complete snapshots and a JSON array of explicit entry paths. Each entry includes full before/after check reports and changes:

| Classification | Evidence |
| --- | --- |
| introduced | New failing requirement, complete earlier analysis |
| existing | Same failing requirement in both views |
| resolved | Earlier failure absent from a complete later analysis |
| indeterminate | Unknown/input-error evidence prevents reliable attribution |

An incomplete before view cannot establish a new regression, even if the after view fails. Earlier input_error keeps the aggregate input_error. Otherwise current failures dominate unknowns; a resolved old failure alone does not make the current result fail.

application_changed compares the entry's content digest. snapshot_changed compares exact manifest digests, including application and profile data. It is not an environment-only causal claim. The tool reports compatibility consequences for these explicit consumers, not all installed applications or all possible future dlopen callers.

## Explain

explain --report FILE --finding ID returns the saved finding as JSON. It needs no snapshot or original filesystem. A missing ID or unsupported schema returns input_error / exit 3. To explain a diff finding, save the corresponding entry's before or after check report first.
