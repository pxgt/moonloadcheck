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

The controlled U2/U3 implementation is available; the complete S/E/R matrices,
protected/SYMBOLIC/COPY/GNU_UNIQUE combinations, two full distribution baselines,
real application corpora, stress/performance checks and release acceptance remain
unfinished. Unsupported combinations retain unknown findings. No Mooncakes
publication or contest registration has occurred.
