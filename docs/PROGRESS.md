# Development evidence

## 2026-11-01 Project foundation

- Started a separate MoonBit module for MoonLoadCheck.
- Confirmed the proposed GitHub repository and Mooncakes module name did not already exist.
- Recorded MoonBit 0.1.20261012 / moonc 0.10.15 as the initial toolchain.
- Available reference environment: Ubuntu WSL, glibc 2.35, GCC, readelf, AArch64 cross compiler.
- Parser, snapshot format, loader model and architecture runtime validation are pending.

The initial scaffold is not an implementation or an acceptance result. Subsequent entries record reproducible commands and actual outcomes.

## 2026-11-01 Loader and parser experiments

- Built reproducible x86-64 and AArch64 ELF fixtures from the repository's C sources.
- Nine expected loader outcomes matched per architecture; AArch64 ran under hash-pinned Ubuntu QEMU 6.2.
- Ran the x86-64 baseline with a separately extracted glibc 2.39 loader and libraries as well as the host glibc 2.35. This is a second loader smoke test, not a complete second environment validation.
- Six MoonBit tests passed on Windows JS (toolchain 0.1.20261012) and Linux native (0.1.20261016).
- Confirmed upstream `dynamic_symbol_table` and `symbol_version_table` return no table for sectionless inputs.
- A bounded segment adapter experiment recovers needed libraries, referenced/hashed symbol span and version requirements on both architectures, using upstream header/segment/string readers.
- The upstream low-level ParseAt implementations are not exposed to consumers. The adapter therefore supplies small checked runtime-table readers instead of copying an entire ELF parser.
- An empty AArch64 GNU hash omits trailing undefined symbols. Relocation references are needed to cover the requested symbols. The experiment explicitly marks whether its symbol extent is exact.
- The published ELF manifest required local migration in the initial experiment. The temporary bridge was tested in a separate clean directory and then replaced with a hash-locked internal parser dependency, preserving upstream source and license without source modifications.
- Windows native tests require unavailable MSVC tools. Linux native validation is available in WSL; no global compiler installation was performed.

- Decoded all 428 records of the host glibc cache and matched them against read-only `ldconfig -p` output. Flags and original order are retained. This host cache had no nonzero hwcap entries; hardware-capability ranking remains outside the verified result.

An isolated Git archive with no dependency cache passed `moon check --target js` without a migration step, and all preserved upstream hashes matched. See the [M0 decision](M0_DECISION.md). Full environment compatibility and acceptance readiness are not established.

## 2026-11-01 M1 target namespace

- Added the first public library API for a byte-preserving Linux file namespace.
- Target-relative/absolute links, dotdot ordering, broken/cyclic links, file identities, case sensitivity and non-UTF8 names have black-box tests.
- Seven independent Linux filesystem outcomes matched the expected semantics.
- Snapshot serialization, environment collection, dependency search, production diagnostics and the U1 end-to-end scenario are still pending.

## 2026-11-01 M1 controlled dependency workflow

The items pending in the previous entry now have a first implementation:

- Added a bounded production adapter for runtime dependency metadata using program headers, including sectionless inputs.
- Added schema-1 portable snapshots, SHA-256 verification, loader identity checks and a Linux fact collector. File identity remains separate from content identity.
- Implemented ordered dependency analysis and explanatory reports for the explicit glibc profile. Root-library RUNPATH non-propagation, two fixes and exceptional candidates have independent loader evidence.
- Fourteen U1 loader outcomes matched across x86-64 and AArch64, in addition to the eighteen M0 reference cases. A symlink-origin case verifies that a DSO's lookup pathname and resolved identity must stay separate.
- Twenty-five MoonBit tests passed on Windows JS and Linux native. Native validation also passed with an isolated hash-pinned official compiler archive: moon 0.1.20261020, compiler 0.10.16+b1a0e846e.
- Seventeen CLI cases passed per backend, including all four exit categories, missing entry, unsupported cache configuration and tampered content. Native JSON reports matched the Windows JS reports for identical snapshots.
- Upstream source hashes remain unchanged. No compiler installation used by another project was changed.
- A final boundary test rejects unverified OS ABI identifiers/revisions; the current test count is 26 passing on each backend.

The CLI requires `--scope dependencies`. Symbol/version checking, upgrade impact,
cache selection, wider environment validation and the full acceptance matrix
are not complete. This is a reproducible U1 implementation under a controlled
profile, not completion of all M1/M2/M3 requirements.

[Clean-runner CI passed](https://github.com/pxgt/moonloadcheck/actions/runs/41283233960)
for commit `12638e0`: check/build/test on native and JS, 26 tests per backend,
34 CLI checks, 32 loader reference outcomes, preserved vendor hashes, canonical
interfaces and first-party formatting. CI setup revealed and fixed missing
toolchain executable bits, an uninitialized package registry and compiler-specific
Int/Int32 interface spelling. Generated interfaces now use the pinned compiler.

## 2026-11-01 Controlled compatibility and consumer impact

- Added cache 1.1 selection for the v2 profile: exact architecture flags, ordered one-path selection, stale entries and NODEFLIB filtering. Ten independent chroot outcomes match across both architectures; matching hwcap/OS-version conditions remain unknown.
- Added explicitly measured LIB/PLATFORM tokens, with one successful real-loader case per architecture and negative tests for missing target facts.
- Added production Verneed/Verdef/Versym, GNU/SysV lookup metadata and relocation-reference readers. Sectionless inputs work; corrupt chain offsets, revisions, symbol indices and bloom filters are rejected.
- Version-node checks are independent of symbol checks. Tests distinguish weak nodes from weak symbols, unused version-node needs, missing versioned exports and named providers lacking VERSYM.
- Added breadth-first startup lookup scope, requested/selected version evidence and actual relocation offsets. Sixteen loader outcomes cover weak/strong order, hidden definitions, main interposition, oldest/default/nondefault versions and SysV-only hashing.
- U2 contributes 24 loader outcomes using our versioned test library. U3 contributes 8 outcomes: two unchanged consumers before/after an export removal, including the unaffected consumer.
- check now accepts dependencies or compatibility scope. diff recomputes both complete views for 1..64 explicit consumers, preserving introduced/existing/resolved/indeterminate classifications and application-change evidence. explain reads a saved schema-2 report without a snapshot.
- The current suite contains 39 MoonBit tests after adding the public facade example. All 39 pass on Windows JS and pinned Linux native.
- Eighty-five CLI checks passed on each backend, with identical same-snapshot JSON across Windows JS and Linux native. All four exit categories, offline explain, comparison directions and malformed input/report requests are covered.
- The full recipe now records 92 loader outcomes (18 M0 + 14 U1 + 10 cache + 24 U2 + 8 U3 + 2 tokens + 16 symbols), plus the separate seven filesystem-path outcomes.
- The clean Linux CI reproduced all 92 loader outcomes and passed 39 tests per backend, then exposed truncated JS diff output in a pipe. The CLI now sets Node's exitCode and lets pending stdout writes finish instead of calling process.exit immediately. The CLI verifier explicitly keeps diff output above 64 KiB so this regression remains exercised.

At that milestone, the controlled U2/U3 implementation was available; the complete S/E/R matrices,
protected/SYMBOLIC/COPY/GNU_UNIQUE combinations, two full distribution baselines,
real application corpora, stress/performance checks and release acceptance remain
unfinished. Unsupported combinations retain unknown findings. No Mooncakes
publication or contest registration has occurred.

## 2026-11-01 Pinned real-program corpus and lookup correction

- Froze 44 official Ubuntu release-pocket packages after checking InRelease signatures and package-index hashes. CI downloads each exact .deb by its recorded hash; no package installation or maintainer scripts are involved.
- Added Jammy libc6 2.35-0ubuntu3 and Noble libc6 2.39-0ubuntu8 startup runtime roots for amd64 and arm64. These are complete startup dependencies for the selected programs, not full OS images.
- Tested GNU hello, jq and zstd from both releases against both runtimes: 24 actual deployment outcomes, with identical executable hashes across the two target views. Four Noble-to-Jammy hello/jq cases fail with GLIBC_2.38 requirements; 20 cases pass, including zstd on the older runtime. Analysis additionally locates the missing jq_set_stderr_cb export.
- The real downgrade comparison keeps all three executables unchanged and identifies hello/jq as affected while zstd is unaffected.
- Added eight independent hash-order cases across both loaders and architectures. They exposed a SysV ordering bug: dynsym index order is not necessarily bucket-chain order. The parser now records Linkage.lookup_order, and lookup follows it. Each case checks actual execution and the selected definition version.
- The new Noble profile names the exact Ubuntu package revision. Inspection of a moving glibc 2.39 maintenance branch initially suggested different fallback semantics; the original release source and the pinned loader agree on the implemented behavior. No generic claim for all 2.39 patch levels is made.
- Added explicit ResourceLimit results for configured table-count limits, a 64 KiB dynamic-name limit, an 8 MiB aggregate name budget with repeated-offset storage sharing, and a bounded version-definition auxiliary walk. Regressions distinguish limit rejection from malformed input.
- The project's own MoonBit native/FFI CLI executes normally in both x86-64 roots. readelf confirms COPY relocations for stdout, stderr and __environ; analysis correctly retains these three unknown findings. These are coverage-gap cases, not static passes.
- A standalone module outside the repository compiles and tests the public facade through a temporary Moon workspace with warnings denied. It verifies local source consumption, not a published Mooncakes package.
- Local Windows JS and pinned Linux native pass 43 MoonBit tests each. The CLI suites cover 85 existing and 24 real-program cases per backend; same-snapshot JSON is compared across the two hosts. Recipes now produce 124 loader outcomes (92 previous + 24 corpus + 8 hash order), plus two normal self-host executions with explicit coverage gaps and the seven earlier filesystem outcomes.

Commands, exact inputs, matrix and remaining limitations are recorded in
[CORPUS.md](CORPUS.md) and the CI workflow. T18's fixed real-program corpus is
established; the complete T19–T22 acceptance, stress/memory budgets, special
relocations and API/report freeze remain open. No Mooncakes publication or
contest registration has occurred.

## 2026-11-01 COPY support and acceptance evidence audit

- Added 40 independently executed cases under the locked Jammy/Noble runtimes: 38 COPY cases plus two AArch64 PIE/GOT controls. Cases cover plain/versioned/weak sources, provider order, missing/wrong-version sources, both directions of size change and protected visibility.
- Implemented ordinary object COPY lookup excluding the executable. Ordinary references to the same symbol retain their separate lookup scope. Same-sized sources pass; unresolved strong sources fail; unresolved weak sources pass. Size mismatches and unvalidated protected/SYMBOLIC/GNU_UNIQUE combinations retain unknown.
- Native MoonBit self-host checks now execute and pass static analysis in both x86-64 roots. COPY sources are libc's eight-byte objects; ordinary stdout/stderr references bind to the executable's copies.
- Added optional COPY source/destination sizes to schema 2 and checked backward decoding without the new fields. Multiple reference diagnostics merge offsets/explanations under one finding ID; saved duplicate-ID reports are rejected. Contract tests retain known failures alongside resource-limit uncertainty.
- Both wrong-rule experiments (COPY binding to the executable, and ignoring size differences) are caught by assertion failures in a disposable source copy after an unmodified passing control.
- Added process time/RSS measurement of four commands, three repetitions per backend, with 60-second and 512-MiB regression ceilings. Local native measurements on WSL2 x86-64 observed 0.18–2.24-second median command times and 6,048–28,896 KiB peak RSS. These are observations for the fixed corpus, not worst-case input guarantees. CI measures both backends independently.
- Local JS/native each pass 47 tests. Each backend passes 85 existing, 24 real-program and 40 COPY CLI checks, with identical saved JSON across Windows JS/Linux native. Third-party source hashes and pinned compiler formatting/interfaces remain verified.
- Published an [evidence map](ACCEPTANCE_STATUS.md) for every one of the 73 internal quality cases, distinguishing covered, partial and open scenarios. This exposes outstanding requirements instead of treating the raw test count as completion.

See [COPY.md](COPY.md) for rules, references, recipes and limits. Remaining work
includes the explicitly listed ELF/path/graph gaps, the five original C12 fault
classes, end-to-end resource exhaustion and broader unusual binding combinations.
API freeze, Mooncakes publication and contest submission remain pending.

## 2026-11-01 Path, input and resource boundaries

- Added 56 independent loader executions: 14 path/graph cases across both locked runtimes and architectures. Return values distinguish RPATH/library-path/RUNPATH precedence; constructor counts distinguish hardlinked aliases from independent equal-byte files. Cycles terminate, diamonds share a leaf, and an actual host-only library cannot repair a missing target dependency.
- Added a search-order-only upgrade comparison with an unchanged application. The selected provider loses its required version, producing an introduced failure without an export-name removal.
- Built readelf-verified ELF32, big-endian and relocatable objects that return Unsupported. Targeted malformed inputs cover truncated headers/dynamic strings, missing terminators, non-advancing version chains and unmapped version addresses. These inputs are never executed.
- Reached the unchanged 16,384 dependency/search-step limit with a small, non-executed ELF containing 17,001 DT_NEEDED records. Both known missing-library failure and resource-limit uncertainty survive in the report; final status remains fail.
- Five planned wrong-rule experiments now fail dedicated assertions after an unmodified passing control: inherited RUNPATH, ignored GNU versions, actual host fallback, unknown converted to pass, and flat export-removal comparison. The two earlier COPY mutations remain separate checks.
- Added semantic determinism under namespace reordering, excluded-mode and repeated changed-profile contracts. Exact raw manifest hashes intentionally differ after reserialization. Missing content callbacks now become InvalidSnapshot errors naming the validated digest, producing stable diagnostics without platform-specific exception text; the public signatures remain unchanged.
- Windows JS and pinned Linux native each pass 64 MoonBit tests and 207 CLI checks (86 existing + 24 corpus + 40 COPY + 57 path/limit). Saved JSON reports match exactly across the two hosts for identical snapshots. Vendor hashes, first-party formatting and unchanged public signatures are verified.

Recipes and precise boundaries are in [BOUNDARIES.md](BOUNDARIES.md). The full
reference recipe now contains 220 loader outcomes (164 earlier + 56 new), plus
two successful self-host executions and the separate seven filesystem cases.
Remaining work includes the partial ELF/symbol rows, broader unusual binding
combinations, stress beyond the dependency-step cap, API/report review and a
fresh user-facing walkthrough. This increment does not complete all M3 or
authorize release/registration.

## 2026-11-02 Symbol lookup and exact parser boundaries

- Added 60 deployment snapshots across both pinned runtimes and architectures, with 56 actual executions. Raw non-UTF-8 names match by bytes, including a failure where two different byte names have the same lossy display. An unused strong undefined dynsym creates no requirement; a deliberately remapped provider version index still matches by name/hash.
- LOCAL/INTERNAL/HIDDEN first candidates remain visible in the runtime hash but are excluded from external lookup. Actual return values confirm selection of the second provider. The controlled byte edits and their noncanonical table layout are documented.
- A single lazy executable succeeds without calling its missing symbol, fails on first call, and fails with LD_BIND_NOW. Static checks retain fail and startup-or-first-call phase. IFUNC existence passes for implementations returning both correct and wrong application values, with resolver results explicitly excluded from the report's checked scope.
- Unknown symbol-bearing and symbol-free relocation inputs retain uncertainty only in the affected checks; NONE and ordinary RELATIVE records create no external lookup. These metadata variants are never executed.
- Added 120 readelf object-field comparisons and 36 non-executed table-boundary inputs. Twelve intact tables at an exact PT_LOAD end remain readable, including the final hashed symbol; 24 truncation/termination variants are rejected. Verneed/Verdef headers, auxiliaries, Versym, dynsym and both hash formats are covered.
- Improved malformed-input diagnostics with the requested virtual range, PT_DYNAMIC file offset or dynamic-string offset/size. Focused tests verify the positions; public signatures and error categories remain unchanged.
- Windows JS and pinned Linux native each pass 74 MoonBit tests and 267 CLI checks (86 existing + 24 corpus + 40 COPY + 57 path/limit + 60 linkage edges). Same-snapshot JSON reports match exactly across the two hosts; preserved vendor hashes and public interfaces remain unchanged.
- The first clean-runner attempt exposed sudo filtering LD_BIND_NOW before the target loader started. The oracle now assigns explicit loader switches after sudo. Local sudo invocations reproduce the original unexpected success and the corrected missing-symbol failure on both pinned x86-64 runtimes; expected loader outcomes are unchanged.

See [LINKAGE_BOUNDARIES.md](LINKAGE_BOUNDARIES.md) for commands, exact observations
and limits. The full recipe now records 276 loader outcomes, plus two self-host
executions and seven filesystem cases. The evidence map has 64 covered, eight
partial and one open row. Remaining work concerns broader malformed/resource
stress, target-profile field distinctions, token/path/cache cases, special
bindings, a GLIBCXX case and the user walkthrough. API/report freeze and release
acceptance remain pending.

## 2026-11-05 Environment facts and path separators

- Reproduced and fixed a false pass: RPATH/RUNPATH semicolons are literal filename bytes, not separators. With the literal provider removed, the previous analyzer selected a different usable directory while every pinned loader failed. Positive and negative cases now verify the exact selected path or failure on all four architecture/runtime contexts.
- Added 78 actual loader outcomes: 32 plain/braced token combinations with measured target values, 12 main/DSO/ancestor ORIGIN competitions, eight empty/colon RUNPATH cases, 16 semicolon cases and 10 Jammy cache-condition cases. Conditional TLS/OS records retain inconclusive even when the actual loader has enough information to choose; irrelevant records do not block an ordinary match.
- Added 50 non-executed profile variants through both the public API and CLI. Required missing/null fields are invalid; explicit empty lists are known empty. Optional tokens can be omitted as unknown, which matters only when used. Empty token values remain invalid in this profile, now with an explicit InvalidSnapshot reason. No previously invalid token value was admitted as a new target fact.
- Windows JS and pinned Linux native each pass 80 MoonBit tests and all 128 new CLI checks. Same-snapshot reports match exactly across hosts. Strict checking, first-party formatting, generated public interfaces, Python syntax and preserved upstream hashes are verified. The new cases are included in the full CI recipe alongside the existing 267 CLI checks per backend.

See [ENVIRONMENT_BOUNDARIES.md](ENVIRONMENT_BOUNDARIES.md) for commands and exact
scope. The full reference recipe now has 354 loader outcomes (276 previous +
78 new), plus two self-host executions and seven filesystem cases. The 73-row
map has 68 covered, four partial and one open row. Remaining work is E07
resource/malformed stress, S12 unusual bindings, S15 GLIBCXX evidence, C11 user
walkthrough, and C09 the published-package consumer. API/report review and
release acceptance remain pending; there is no Mooncakes release or contest
submission in this increment.

Cloud verification initially stalled before project tests while downloading
cross-compiler packages from azure.archive.ubuntu.com. The first run spent ten
minutes transferring packages and retrying a 9 MB archive; a fresh runner also
stalled at installation. CI now keeps the runner's signed official Ubuntu
archive/security fallback mirrors, bounds acquisition retries/inactivity and
limits the compiler-install step to six minutes. Pinned reference runtime
versions/hashes and all project test expectations are unchanged.

## 2026-11-06 Special bindings, GLIBCXX and resource boundaries

- Reproduced and fixed a false pass when a TLS reference encounters an ordinary definition before a valid TLS definition. All four pinned architecture/runtime contexts bind the first provider and then fault. The analyzer now retains that provider and reports unknown for TLS type mismatches or mixed reference classes. Ordinary interposition/TLS still pass and a missing TLS definition still fails.
- Added 32 real binding observations, including GNU_UNIQUE, protected and SYMBOLIC controls that retain explicit unknown. Deliberately inconsistent type fixtures are original project inputs, with timeouts and core dumps disabled; their binding traces establish provider selection independently of static analysis.
- Added 12 real GLIBCXX probes using the already locked libstdc++ packages. Keeping consumers, loader and other runtime libraries unchanged, a library-only downgrade loses GLIBCXX_3.4.32. A version-node mutation still fails despite retaining 3.4.33 and the old name bytes. The unaffected consumer continues to run. Successful executions retain unvalidated C++ binding findings, so this is exact version evidence rather than a complete C++ ABI claim.
- Added 68 non-executed parser inputs covering wide offsets, sizes, indices and actual production header/dynamic/relocation caps. A zero-file-size PT_LOAD exposed an unchecked UInt64 virtual-memory overflow; it now returns Malformed. Allowed counts parse and excess counts return ResourceLimit, including 500,000/500,001 relocation records without lowering the production cap.
- Windows JS and pinned Linux native each pass 86 MoonBit tests and 112 new CLI checks; same-snapshot reports match exactly across hosts. Eight local native stress measurements stay below 0.98 seconds and 45,472 KiB peak RSS on these fixed inputs. CI also measures the JS backend. Strict checking, pinned generated interfaces/formatting, Python/Bash/YAML checks and preserved upstream hashes pass; public interfaces are unchanged.

See [MATURITY_BOUNDARIES.md](MATURITY_BOUNDARIES.md) for commands, references and
scope. The complete reference recipe now has 398 loader observations (354
previous + 44 new), plus two self-host executions and seven filesystem cases.
The 73-row map has 71 covered, one partial (C11 walkthrough) and one open (C09
published consumer). Covered resource cases are finite regression evidence,
not a universal memory/time bound. API/report review and the user walkthrough
remain next; no Mooncakes release or contest submission occurred.

## 2026-11-06 API/report contract and fresh README walkthrough

- Reviewed the seven facade functions, public data packages, raised errors versus findings, CLI grammar and saved-report compatibility. Added the missing SnapshotError facade alias; pinned interface generation shows this is the only public signature-file change. No existing function or type was removed.
- Fixed the CLI accepting arbitrary leading arguments. It now removes only the backend's executable prefix, requires the documented argument sequence and supports --help. Command error envelopes retain concrete reasons, JSON field information, read paths or blob digests, plus an additive error_kind field. Unknown-command output no longer loses its usage text through generic Error interpolation.
- The report reader checks schema before current fields, rejects empty/duplicate finding IDs and invalid finding statuses, and rejects aggregate verdicts inconsistent with their findings. A checked-in synthetic schema-2 serialization sample preserves missing COPY optional fields and decimal UInt64 offsets. Unknown optional fields are tolerated without claiming lossless roundtripping or authentication.
- Corrected JSON text limit descriptions and diagnostics: manifest/report/entry-list limits count UTF-16 code units, while ELF/blob limits count bytes. The implementation thresholds are unchanged.
- Rebuilt the README around an explicit Ubuntu 22.04 setup, local pinned compiler, three failure/fix workflows, offline explanation, standalone library use, complete-test prerequisites and troubleshooting. Its verifier extracts and runs the actual marked command blocks, not a separate hand-maintained command list.
- A fresh source export with no .tools, .mooncakes, _build or generated fixtures passed all 10 README blocks, eight CLI outcomes and the standalone native consumer. This was a fresh project directory on the existing WSL Ubuntu host with documented OS prerequisites, not a claim of a newly installed OS. Moon's dependency download could use the local version cache; independent fresh-runner CI repeats the workflow.
- Windows JS passes all 89 MoonBit tests. Pinned native passes the three new report tests. Each backend passes 28 new CLI contract cases and 86 existing CLI cases; the 86 saved reports compare exactly across Windows JS/Linux native. Python syntax, Bash/YAML, locked source hashes, pinned interfaces and formatting pass. Full dual-backend regression remains in the CI workflow.

The [API contract](API_CONTRACT.md) records source/schema compatibility and
explicit trust boundaries. The 73-case map now has 72 covered rows and one open
row, C09: consuming the published Mooncakes package. Publication packaging,
release authorization and unresolved November rule details remain separate
release work. No package was published and no registration was submitted.

## 2026-11-07 Actual archive consumers and release evidence

- Added an archive gate that audits the output of `moon package --frozen`,
  including module metadata, current source bytes, licenses and all 18 locked
  vendor files. It rejects excluded build/download/generated inputs, path
  escapes, case-colliding names and symlinks before extraction.
- Each isolated workspace contains the extracted package and a new consumer;
  the original source repository is not a workspace member. Explicit U3
  snapshots are copied as test inputs outside the package. Three consumer
  tests exercise the seven public facade functions and exported errors.
- The extracted CLI is built independently and runs seven cases per backend:
  compatibility pass/fail, dependency-only pass, selective diff, saved-report
  explain, help and an argument error. The verifier distinguishes a successful
  explain command from the failed finding that it successfully returns.
- The initial consumer exposed a real version mismatch: package metadata said
  0.1.0 while analysis reports said 0.1.0-dev. Reports now match 0.1.0; no public
  interface or schema changed. The frozen old-report compatibility fixture
  intentionally retains its historical tool version.
- The same 182-entry local ZIP passed all three consumer tests and seven CLI
  checks on both Windows JS and pinned Linux native. License/source hashes,
  Python/YAML syntax, local documentation links and pinned check/info/fmt pass.
  The CI walkthrough job now rebuilds and verifies the committed candidate on
  both backends, comparing its report JSON exactly. Local ZIP hashes identify
  individual builds; byte-identical ZIP reproduction is not claimed.
- Added an unreleased changelog, a candidate/release checklist and a 6–8 minute
  reviewer demonstration. Updated the corpus's historical remaining-work text
  to point to the current boundary evidence and acceptance map.

This closes the local packaging/provenance preparation, not publication.
The internal map remains 72 Covered / 1 Open: C09 still requires resolving and
testing a real published Mooncakes version without any workspace override.
There is no release tag, Mooncakes publication or contest submission in this
increment. Formal contest-rule questions remain in the planning workspace.

## 2026-11-07 Mooncakes publication and independent registry consumers

- Published Xpeng/moonloadcheck 0.1.0 from the previously approved source
  eb1393d8f15b7ecf4ba68c15b629955c00334fdd. The normal publishing command checked
  both source and extracted payload and returned 200 OK; live registry metadata
  confirms the exact version and checksum. The annotated v0.1.0 tag points to
  that source commit and is pushed without moving an existing tag.
- Downloaded the public ZIP and matched all 182 file payloads against the
  reviewed candidate. Its SHA-256 is
  ef23c9f42b99cd81feb5f1107fbc6fbefc034c68698abb2a1f3f41d5e3eae69a,
  also reported by registry metadata. No generated binary corpus is distributed.
- New temporary consumers declare the ordinary versioned registry dependency,
  with no moon.work, ancestor workspace or local source override. Dependency
  graphs explicitly identify registry source and version 0.1.0. Windows JS and
  pinned Linux native each pass three tests covering all seven facade functions
  and exported errors; every installed package file matches the published ZIP.
  The initial run on each host downloaded the version; later reruns may use
  Moon's version cache without introducing any local source substitution.
- Added the release lock, reusable registry verifier and a fresh CI step for
  both backends. The verifier compares the resolved graph and installed bytes,
  so a local source-workspace success cannot satisfy it. Registry-download and
  metadata-query retries retain TLS verification and checksum enforcement.
- Recorded publication details, source/tag, checksum, reproduction commands
  and the distinction between the immutable release and subsequent main-branch
  documentation. The archive's prepublication text is historical; the published
  payload and release tag were not changed to rewrite it.

See [RELEASE_0.1.0.md](RELEASE_0.1.0.md). C09 is now Covered and all 73 internal
quality rows have evidence under their declared limits. This does not establish
official contest acceptance. No registration or organizer message was sent.

## 2026-11-11 Independent project onboarding

- Added a readable UTF-8 deployment configuration and capture/check adapter.
  Relative roots resolve against the configuration file; target facts remain
  explicit, and all compatibility decisions stay in the MoonBit CLI. Unknown
  fields, missing facts, duplicate keys, inconsistent analyzer output and
  reused output directories cannot silently pass a CI gate.
- Added an original temperature-summary application in its own MoonBit module.
  It imports core packages only and calls our separately versioned C
  calibration library. The verifier copies its source outside the repository,
  builds/tests it there and checks the generated interface and formatting.
  This is an independent example, not a claim of third-party adoption.
- The same executable is checked and actually run in good, missing-library,
  legacy-library, restored-library and Noble deployments. Both CLI backends
  agree with the five loader outcomes (0, 127, 1, 0, 0), including the precise
  SENSOR_2.0 requirement. The normal application returns three samples with
  minimum 19750, maximum 24750 and mean 22250 milli-Celsius.
- Added 26 gate checks including inconclusive/input-error and configuration
  cases, four introduced/resolved comparisons, two saved-report explanations
  and an application-input error after a static pass. Integrated the verifier
  into CI and documented the reusable workflow in INTEGRATION.md.
- Original application/C sources and their license are distributed; compiled
  inputs, runtime roots and snapshots remain ignored. The locked ELF vendor
  files and public analyzer APIs are unchanged. These are unreleased source
  additions; the 0.1.0 package and tag retain their published contents.

## 2026-11-11 Target identities and AArch64 application execution

- Added four explicit target identity presets for the locked Jammy/Noble
  x86-64/AArch64 loaders. Catalog entries bind package provenance, ELF machine,
  rule revision and loader digest; CI verifies them against the corpus lock
  and extracted files. Search/environment facts are still explicit. Unknown
  presets, missing facts, identity overrides, ambiguous configurations and
  actual loader mismatches fail closed; raw-profile support is preserved.
- The independent sensor application now cross-builds with the existing pinned
  Moon toolchain and `MOON_CC=aarch64-linux-gnu-gcc`, including its runtime C
  and our versioned calibration library. Separate temporary modules prevent
  mixing architecture outputs. ELF machine values are checked as 62 and 183.
- Executed both builds against both locked runtime sets, with good, missing,
  old-version, restored and wrong-architecture library cases. All 20 outcomes
  agree with native/JS analysis; each group has static exits 0/1/1/0/1 and real
  loader exits 0/127/1/0/127. Program identity is constant within each
  architecture, including across the two runtime suites.
- The expanded verifier passes 77 gates, 16 diffs, eight explanations and eight
  preset/raw equivalence checks (included in the gates), plus 16 application
  business executions. These replace the earlier integration totals; they
  are not added again to the original 73-row internal acceptance map.
- AArch64 instructions run under QEMU 6.2.0 from the existing hash-locked
  Ubuntu package, with real target loaders in chroots. This is not physical
  ARM hardware, an ARM kernel or device validation. The result records compiler
  targets/versions, program and loader digests, catalog digest and QEMU digest.
  Analysis itself remains on the x86-64 host using native and JS CLIs.
- No analyzer API or vendored source was changed. The new public payload is
  original code, metadata, recipes and documentation. Generated application,
  QEMU/runtime binaries and snapshots stay ignored; no CI artifact upload was
  added. These remain unreleased source additions after immutable 0.1.0.
