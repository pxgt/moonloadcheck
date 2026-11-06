# 0.1 API and report contract review

This is the reviewed contract for the planned 0.1 release, still unpublished.
The generated `.mbti` files are the exact source signatures. The supported public
packages are the root facade, `model`, `snapshot` and `analysis`. Internal parser,
cache and experiment packages are implementation details.

## Public entry points

| Facade function | Input and result | Error boundary |
| --- | --- | --- |
| `read_elf` | ELF bytes → runtime object metadata | `ElfError`: Malformed, Unsupported, ResourceLimit |
| `read_linkage` | ELF bytes → symbols, versions and relocation references | Same typed ELF errors |
| `load_snapshot` | Manifest text and digest-to-bytes callback → verified snapshot | SnapshotError, PathError, JSON parse/decode errors; callback failure becomes InvalidSnapshot naming its digest |
| `check_dependencies` | Snapshot and byte-valued entry → Report | Analysis problems are findings, including input_error; no raised error |
| `check_compatibility` | Same, including symbol/version checks → Report | Same finding-based boundary |
| `compare` | Two snapshots and 1..64 distinct byte entries → ImpactReport | Invalid entry-list size/duplicates raise ReportError; individual analyses remain in the result |
| `read_report` | Saved schema-2 check JSON → Report | ReportError for unsupported schema, ambiguous IDs or verdict conflicts; JSON parse/decode errors for malformed shape |

The root facade now also re-exports `SnapshotError`, so callers can catch its
InvalidSnapshot, ContentMismatch and SnapshotLimit variants without an internal
import. This is an additive source API change. Library tests and the standalone
consumer compile that path. No function signature or existing type was removed.

`Report.exit_code`, `ImpactReport.exit_code` and `Report.explain` retain their
existing meanings. `explain` returns saved evidence and raises ReportError for
an absent ID; it does not access the snapshot or re-run analysis.

## Data and trust boundaries

Linux paths and ELF names are bytes. JSON `hex` is authoritative; `display` is
lossy presentation. Offsets and sizes are decimal strings, including values
above JavaScript's exact numeric range. Returned report arrays and public
structs are ordinary caller-owned data, not authenticated or immutable objects.
Constructing structs or using their derived `FromJson` directly bypasses the
`read_report` validation. Use `read_report` for saved check reports.

The snapshot loader validates indexed digests and file identities before
analysis. Its callback receives a validated digest, never a target pathname.
Returned profile arrays are copied. Analysis does not execute files or consult
host libraries. The caller supplies a bounded storage reader when accepting
untrusted input; CLI file reads precede the decoded-size checks.

Manifest, saved-report and CLI entry-list text limits count UTF-16 code units,
as defined by MoonBit String.length: 4,194,304, 67,108,864 and 1,048,576 respectively.
They are not UTF-8 file-byte or process-memory bounds. ELF/blob limits count
bytes. See [SUPPORTED_PROFILE.md](SUPPORTED_PROFILE.md) for other limits.

## Versioning and compatibility policy

- Snapshot schema 1 and report schema 2 are independent. The saved check reader
  explicitly rejects schema 1 and unknown report schemas before decoding current
  fields. There is no implicit migration.
- Additive optional fields may remain within the same schema. Readers accept
  unknown object fields and older schema-2 records without COPY size evidence.
  Re-encoding preserves known semantic data, not unknown fields or original JSON
  formatting. The checked-in synthetic [schema-2 sample](../fixtures/reports/schema-2.json)
  freezes this reader contract; it is not loader execution evidence.
- Changes to required fields, byte/identity interpretation, or status meanings
  require a new schema. Source-breaking public changes require a new minor
  version while the module is pre-1.0; compatible additions and documented
  corrective fixes can stay within 0.1. Release notes must identify changed
  verdicts and their regression evidence.
- MLC001–MLC009 retain their documented meanings. Consumers must preserve the
  reported severity of unfamiliar future codes, rather than treating them as a
  pass. Finding identity excludes provider/snapshot as documented in the report
  schema; explanation wording is not a machine API.

## CLI boundary

The command grammar is available through `--help`. Fixed-order options are
validated after stripping only the actual runtime executable prefix (one item
for native, two for Node). Extra or duplicate arguments cannot be ignored.

Exit 0/1/2/3 means pass_static/fail/inconclusive/input_error for analysis commands.
`--help` and successful `explain` return 0. JSON analysis stdout contains exactly
one JSON value. Before analysis, an argument/read/decode error produces the
separate error envelope described in [REPORT_SCHEMA.md](REPORT_SCHEMA.md), even
when text output was requested. I/O messages report operation and path without
depending on platform-specific OS error wording.

## Review and evidence

This review covers all seven facade operations, their publicly exposed data
packages, error paths, CLI grammar and saved-report compatibility. Three focused
MoonBit tests check recorded reports, schema dispatch and invalid identities/
verdicts; 28 CLI contract cases per backend check errors and argument handling.
Existing tests retain exact backend report comparisons, all four exits, mixed
fail/unknown findings, optional-field decoding and offline explanation.

The independent README walkthrough starts without `.tools`, `.mooncakes`,
`_build` or generated fixtures. It executes the documented blocks verbatim and
checks U1 failure/fix, unchanged U2 executable, selective U3 impact/restoration,
saved explanation and a standalone source consumer. Full reference/test CI runs
separately. Published-package consumption remains a release-stage check.
