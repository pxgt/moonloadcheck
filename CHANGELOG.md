# Changelog

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
