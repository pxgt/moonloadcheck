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

The CLI requires `--scope dependencies`. Symbol/version checking, upgrade impact,
cache selection, wider environment validation and the full acceptance matrix
are not complete. This is a reproducible U1 implementation under a controlled
profile, not completion of all M1/M2/M3 requirements. A pinned CI workflow has
been prepared; its remote run is recorded separately once verified.
