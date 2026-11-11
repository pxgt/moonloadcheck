# Development report schema 2

Schema 2 adds version/symbol checks, stable finding identifiers and comparisons. It does not silently reinterpret a schema-1 dependency report. Snapshot schema remains 1. See the [compatibility policy](API_CONTRACT.md) and [published 0.1.0 record](RELEASE_0.1.0.md); later source additions are identified separately.

## Check

A report identifies tool_version, rule_revision, exact snapshot_sha256 and entry, followed by checked_scope, not_checked and status. Byte names contain display (lossy UTF-8) and hex (authoritative original bytes). Semantic comparisons never use display.

- objects records mapped paths, file identity, content digest and machine.
- edges records each consumer, requested dependency, selected path and ordered search trace.
- symbol_scope records startup lookup order; it differs from mapping order.
- version_checks records named-provider requirements independently of symbol references.
- symbol_checks records actual relocation-referenced names, requested versions, selected providers/definition versions, lookup policy, reference offsets/types and startup versus lazy phase. COPY and ordinary references to one symbol produce separate records. COPY uses copy-source-excluding-executable and adds optional decimal-string copy_destination_size/copy_source_size evidence; missing source size means no source was selected. Older schema-2 reports without these additive fields still decode.
- findings contains id, code, status, subject, optional requirement/version/provider, dependency chain, explanation, suggested action and reference offsets.

Offsets and sizes are decimal strings so JavaScript consumers do not lose ELF64 precision. The emitter omits absent optional fields. read_report dispatches on schema before decoding current fields, validates report/finding statuses, rejects empty or duplicate finding IDs, and checks that the aggregate status agrees with the findings. It does not authenticate the saved report, validate every nested byte/offset string, or re-run analysis. Direct derived FromJson decoding bypasses these checks.

Unknown object fields are accepted but not retained when re-encoding. Existing
optional fields may be absent (older schema-2 COPY sizes remain supported).
Missing required fields are rejected. Report text is limited to 67,108,864 UTF-16
code units after reading; this is not a file-byte or allocation bound.

Finding IDs hash code, raw subject, requirement and requested version. They intentionally exclude the selected provider and snapshot digest so an unchanged unmet requirement can be classified as existing across snapshots. Symbol-free unsupported relocations include kind/offset in their requirement identity. Multiple diagnostics for one identity merge their offsets and explanations. If their providers differ, the merged finding omits its provider; individual symbol_checks retain each selection. This keeps explain and diff unambiguous.

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

Post-0.1.0 `analysis.read_impact_report` validates saved comparisons using the
same classification/aggregation rules, including nested check validation,
consumer identity/uniqueness, snapshot flags and exact ordered change evidence.
It does not rerun ELF analysis or authenticate the saved metadata. The
[local HTML renderer](DIAGNOSTICS.md) uses this reader and preserves all four
verdicts. Its concise summary schema is separate from report schema 2.

## Explain

explain --report FILE --finding ID returns the saved finding as JSON. It needs no snapshot or original filesystem. A missing ID or unsupported schema returns input_error / exit 3. To explain a diff finding, save the corresponding entry's before or after check report first.

## Command errors before analysis

These are a separate shape from check reports, diff reports and finding objects:

```json
{"schema_version":2,"status":"input_error","error_kind":"report","message":"unsupported report schema"}
```

`error_kind` is arguments, io, json, snapshot, path, report or other. It is an
additive field; earlier command errors contained only schema_version, status and
message. The message now retains the relevant reason, field/path or blob digest.
Consumers should use status/error_kind rather than parse message wording.
Errors use this JSON envelope even when text output was requested. It is not an
input for read_report/explain. Analysis findings, including MLC006, continue to
use full check reports with checked_scope and evidence.
