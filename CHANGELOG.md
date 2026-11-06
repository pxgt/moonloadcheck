# Changelog

## 0.1.0 — unreleased candidate

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

No Mooncakes release or release tag has been created for this candidate.
Support boundaries and finite resource guarantees are documented in
[SUPPORTED_PROFILE.md](docs/SUPPORTED_PROFILE.md); full C++ ABI, arbitrary loader
versions, application behavior and runtime dlopen remain outside the result.
