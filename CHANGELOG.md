# Changelog

## 0.3.0 — 2026-11-12

- Read-only dependency preflight identifies missing explicit environment facts.
- Multi-target deployment orchestration freezes configuration inputs and retains
  target errors. MoonBit validates nested checks, derives verdicts and renders
  a local matrix with program identity and expandable evidence.
- Add a fixed amd64 libc6 2.35-0ubuntu3.15 identity and a reproducible external
  zstd dynamic-library source build. Record application version-policy rejection
  independently of static compatibility and loader success.
- No root facade or existing snapshot/check/comparison schema change. Existing
  published packages and tags remain immutable.

## 0.2.0 — 2026-11-11

- Add MoonBit diagnostic guidance and offline HTML/CI-summary rendering for
  saved check, comparison and command-error evidence, preserving verdict exits.
- Validate saved comparisons with the existing classification rules; reject
  contradictory nested evidence, forged changes and duplicate consumers.
- Escape report text, retain raw byte/UInt64 evidence and provide script-free
  expandable dependency, symbol/version and before/after views.

- Add four explicit Jammy/Noble x86-64/AArch64 target identities, verified
  against locked runtime sources; retain caller-supplied environment facts.
- Cross-build and actually execute the independent MoonBit native/FFI app on
  AArch64 under pinned QEMU, alongside x86-64, with missing/version/architecture
  failures, repairs, report comparisons and business-output checks.

- Add readable deployment configuration and a capture/check CI adapter that
  preserves the MoonBit analyzer's pass/fail/inconclusive/input-error semantics.
- Add an independent MoonBit native/FFI sensor-report application and
  deployment verification for missing libraries, symbol versions and repairs.
- Document project onboarding, output provenance, controlled target facts and
  CI integration; correct an obsolete prepublication snapshot-schema note.

- Add version-specific registry verification, an external saved-comparison API
  test, and HTML/summary CLI checks built from verified registry source bytes.

Snapshot schema 1, report schema 2 and all seven root facade signatures remain
unchanged. `analysis.read_impact_report` is additive. The 0.1.0 registry archive
and tag are unchanged. Published as
[Xpeng/moonloadcheck@0.2.0](https://mooncakes.io/docs/Xpeng/moonloadcheck@0.2.0)
from tag `v0.2.0`; see the [release record](docs/RELEASE_0.2.0.md).

## 0.1.0 — 2026-11-07

- Offline Linux dependency selection, symbol/version availability and explicit
  consumer impact comparison through a MoonBit library and CLI.
- Portable snapshot schema 1, report schema 2, byte-preserving identities,
  stable finding IDs, JSON/text output and saved-report explanations.
- Controlled ELF64 little-endian x86-64/AArch64 profiles, pinned Jammy/Noble
  runtime evidence, ordinary COPY/TLS checks, exact GNU version requirements
  and explicit unknown results for unvalidated behavior.
- Reference-driven corrections for SysV hash order, literal RPATH semicolons,
  TLS first-provider selection and overflowing virtual-memory ranges.
- Strict CLI argument handling, detailed command errors, saved-report validation
  and an exported SnapshotError facade type.
- Fresh README execution, package-content audit and isolated ZIP consumption.
  Package metadata and new reports both identify version 0.1.0.

Published as [Xpeng/moonloadcheck@0.1.0](https://mooncakes.io/docs/Xpeng/moonloadcheck@0.1.0).
Tag `v0.1.0` identifies the reviewed source commit; the
[release record](docs/RELEASE_0.1.0.md) retains the actual registry checksum and
independent consumer results. The immutable archive contains the prepublication
documentation from that commit; publication records were added afterward.
Support boundaries and finite resource guarantees are documented in
[SUPPORTED_PROFILE.md](docs/SUPPORTED_PROFILE.md); full C++ ABI, arbitrary loader
versions, application behavior and runtime dlopen remain outside the result.
