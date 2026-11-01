# MoonLoadCheck

MoonLoadCheck is a MoonBit project for offline Linux binary deployment analysis. It will explain dependency selection, check symbol/version requirements against a target environment, and identify consumers affected by shared-library upgrades.

**Status: M0 feasibility verified; M1 deployment analysis in progress. No compatibility verdict is implemented yet.** This is a new project; existing ELF libraries are dependencies and references, not claimed as new work.

The first release targets ELF64 little-endian x86-64 and AArch64 under documented glibc loading conditions. Its three acceptance scenarios are application relocation, deployment to a different runtime environment, and library-upgrade impact analysis.

The intended outputs are a reusable Mooncakes library, a CLI, deterministic JSON diagnostics, and reproducible examples. A successful static check will describe its checked scope; it will not guarantee application behavior or full C++ ABI compatibility.

M0 has exercised sectionless ELF inputs, GNU symbol versions and independent loader comparisons on x86-64/AArch64. The parser from `moonbit-community/elf@0.0.1` is preserved as a hash-locked internal dependency to avoid its obsolete published manifest. See [development evidence](docs/PROGRESS.md), [reproduction commands](tools/oracle/README.md) and [references](THIRD_PARTY.md).

## Development

Tested toolchains: Windows JS `0.1.20261012` / compiler `0.10.15`, Linux native `0.1.20261016` / compiler `0.10.16`. The first public API is the [target namespace library example](README.mbt.md). No Mooncakes release has been published.

## License

Apache-2.0. Test sources created here use the same license unless explicitly stated otherwise. Third-party binaries will be generated or obtained from recorded recipes rather than silently bundled.
