# MoonLoadCheck

MoonLoadCheck is a MoonBit project for offline Linux binary deployment analysis. It will explain dependency selection, check symbol/version requirements against a target environment, and identify consumers affected by shared-library upgrades.

**Status: M0 feasibility work. No compatibility verdict is implemented yet.** This is a new project; existing ELF libraries are dependencies and references, not claimed as new work.

The first release targets ELF64 little-endian x86-64 and AArch64 under documented glibc loading conditions. Its three acceptance scenarios are application relocation, deployment to a different runtime environment, and library-upgrade impact analysis.

The intended outputs are a reusable Mooncakes library, a CLI, deterministic JSON diagnostics, and reproducible examples. A successful static check will describe its checked scope; it will not guarantee application behavior or full C++ ABI compatibility.

Development starts by validating `moonbit-community/elf`, sectionless ELF inputs, GNU symbol versions, environment-cache metadata, and independent loader comparisons. See [development evidence](docs/PROGRESS.md) and [references](THIRD_PARTY.md).

## Development

Initial toolchain: MoonBit `0.1.20261012` / compiler `0.10.15`. Commands will be documented alongside working features. No Mooncakes release has been published.

## License

Apache-2.0. Test sources created here use the same license unless explicitly stated otherwise. Third-party binaries will be generated or obtained from recorded recipes rather than silently bundled.
