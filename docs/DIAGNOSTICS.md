# Diagnose a deployment and read an offline report

The `report` command renders saved schema-2 check/comparison JSON or a CLI
command-error envelope. The renderer and diagnostic guide are implemented in
MoonBit. It needs no snapshot, target binaries, Python server, network connection
or browser JavaScript. These features are included in the 0.2.0 package; build
the matching CLI with the pinned compiler. They are not in the 0.1.0 registry ZIP.

## Generate a local report

Save the output of `check --format json` or `diff --format json` first. For the
deployment helper, use `report-000.json` (or another numbered entry), not its
`summary.json` or snapshot manifest. Then run:

```sh
mlc report --input /path/to/report.json --format html > /path/to/report.html
mlc report --input /path/to/report.json --format summary
```

Here `mlc` means the CLI alias from the README; the equivalent direct commands
are `_build/native/debug/build/cmd/main/main.exe report ...` or
`node _build/js/debug/build/cmd/main/main.js report ...`. The saved-report step
also works on Windows with the JS CLI. Open the resulting HTML file locally.
No server is necessary. Browser find, expandable evidence sections and print
are available without scripts. Choose a new output filename: shell redirection
can overwrite an existing file and must never target the input JSON.

**Rendering retains the saved verdict's exit code:** 0 pass_static, 1 fail,
2 inconclusive, 3 input_error. An exit 1 can accompany a successfully generated
HTML report of a deployment failure. Rendering success must not turn a failed
CI gate green. Invalid input instead produces a JSON error envelope/exit 3,
even for `--format html`; it does not produce a valid HTML page.

To save a report in a Bash CI job and retain its gate:

```sh
set +e
mlc report --input report.json --format html > report.html
verdict=$?
set -e
exit "$verdict"
```

The concise summary is one JSON value with summary schema 1, source report
schema 2, source kind, status/exit code, consumer count, finding count, diagnostic
code counts and change-classification counts. Comparison finding counts refer
to the **after** views; changes also retain earlier/resolved findings. It is a
derived CI summary, not an input accepted by `report` or `explain`.

## Read the evidence in order

1. Check the saved status, analyzer/rule version, snapshot digest, checked scope
   and not_checked list. A static pass does not certify application behavior.
2. For a finding, read the subject, requirement/version, provider and dependency
   chain. Its saved explanation/action is kept separately from the general guide.
3. Expand dependency selection to see the ordered search source, candidate path,
   rejection/selection outcome and final selected object. Loaded objects and
   startup symbol lookup order remain separately visible.
4. Expand version and symbol evidence for the requested/defined versions, lookup
   policy, startup/lazy phase, relocation offsets/types and optional COPY sizes.
5. For a comparison, inspect each consumer's before/after status and
   introduced/existing/resolved/indeterminate changes. An incomplete baseline
   cannot prove a newly introduced regression. Application/snapshot change flags
   are saved metadata, not proof that only the environment caused the failure.
6. Repair the actual target or missing evidence, recapture it, rerun the same
   consumer checks and application tests, and save a new comparison report.

All byte names show both JSON-quoted lossy `display` text and authoritative
`hex`. Offsets/sizes remain decimal strings, including UInt64 values beyond
JavaScript's exact number range. Unknown future diagnostic codes keep their
saved severity and get an explicit unfamiliar-code guide.

## Diagnostic guide

| Code | Investigate | Next step and confirmation |
| --- | --- | --- |
| MLC001 | PT_INTERP path, loader presence and identity | Stage the intended target loader/runtime or rebuild for that target; recapture and check the closure. An arbitrary loader symlink is not a verified fix. |
| MLC002 | Dependency chain and ordered candidate trace | Correct missing/wrong libraries or the declaring object's search path; then check symbols and versions as well as paths. |
| MLC003 | Entry, interpreter and object ELF machine values | Rebuild/select a matching architecture set; renaming a file does not change architecture. |
| MLC004 | Requested version node and named provider | Use the matching exported version or rebuild for the supported baseline; compare the same consumer after repair. Do not patch version names to force acceptance. |
| MLC005 | Referenced symbol/version, provider, visibility, lookup policy and offsets | Restore a compatible definition or rebuild; check actual consumers and run application tests. Symbol availability does not prove type/layout ABI compatibility. |
| MLC006 | Malformed input, path/digest/offset evidence | Recapture quiescent verified input or replace corrupt data; resolve input errors before interpreting compatibility. |
| MLC007 | Missing search facts, provider identity or scope | Measure facts on the target, capture missing evidence and rerun; do not infer values from the analysis host. |
| MLC008 | Unsupported loader, binding or runtime behavior | Keep uncertainty explicit; use a genuinely supported condition or independent investigation. Relabeling a profile does not add support. |
| MLC009 | Parser/namespace/traversal resource cap | Reduce irrelevant input or review bounded implementation changes with resource tests; do not omit required dependencies to pass. |

These are general investigation steps. The actual saved finding and the
[supported deployment model](SUPPORTED_PROFILE.md) determine the boundary.
Text-mode `check`/`diff` includes the same guide. `explain` retains its existing
unchanged finding JSON contract.

## Validation and trust boundary

Check reports use the existing saved-report validation. Comparisons use
`analysis.read_impact_report`: it checks schema, nested verdicts, consumer
identities, duplicate entries, snapshot-change flags and the complete ordered
changes against the same classification rules as `compare`. Conflicting
statuses, omitted/forged changes and inconsistent saved finding evidence are
rejected. This is consistency validation, **not authentication or ELF analysis**.
It cannot independently prove the saved application-change flag without blobs.
Derived `FromJson` decoding alone bypasses semantic validation.

Presentation rejects duplicate JSON keys and ambiguous shapes, and limits input
to 4,194,304 UTF-16 code units and output to 33,554,432. These checks happen after
reading/constructing strings; they are not file-byte or peak-memory guarantees.
The regular saved-report readers retain their larger documented bound.
Unknown optional fields are accepted but not shown after typed decoding;
decoded JSON panels preserve known schema fields, not original formatting.

The HTML has no scripts, event handlers, input-derived links/attributes or
external resources. Dynamic strings are escaped as text, and a restrictive CSP
provides an additional boundary. Verification exercises hostile markup in path,
symbol, version, ID, explanation and error fields, repeated delimiters, legacy
optional fields and full UInt64 strings, with identical native/JS output.
Browser verification supplements the structural checks; this is not a formal
proof against every browser implementation defect.

HTML includes paths, symbols and report metadata; it does not embed ELF blobs,
runtime roots or QEMU. Keep generated files under ignored `artifacts/` by default.
Review report contents before sharing. No CI artifact upload is configured.

After the existing deployment verifier has run, reproduce the presentation
checks with:

```sh
python3 tools/verify_reports.py \
  --native _build/native/debug/build/cmd/main/main.exe \
  --js _build/js/debug/build/cmd/main/main.js
```

`artifacts/presentation/result.json` records the local run directory and page
hashes. Tests cover both architectures' real deployment reports, multi-consumer
regressions/repairs, all four exits, unknown baselines, command errors, the nine
guide codes, hostile text and inconsistent saved comparisons. No generated
report is added to the source distribution.
