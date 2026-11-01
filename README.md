# MoonLoadCheck

MoonLoadCheck is a MoonBit project for offline Linux binary deployment analysis. It will explain dependency selection, check symbol/version requirements against a target environment, and identify consumers affected by shared-library upgrades.

**Status: M1 has a working dependency-analysis CLI and portable library. Symbol/version compatibility and upgrade impact remain under development.** This is a new project; existing ELF libraries are dependencies and references, not claimed as new work.

The first release targets ELF64 little-endian x86-64 and AArch64 under documented glibc loading conditions. Its three acceptance scenarios are application relocation, deployment to a different runtime environment, and library-upgrade impact analysis.

The intended outputs are a reusable Mooncakes library, a CLI, deterministic JSON diagnostics, and reproducible examples. A successful static check will describe its checked scope; it will not guarantee application behavior or full C++ ABI compatibility.

M0 has exercised sectionless ELF inputs, GNU symbol versions and independent loader comparisons on x86-64/AArch64. The parser from `moonbit-community/elf@0.0.1` is preserved as a hash-locked internal dependency to avoid its obsolete published manifest. See [development evidence](docs/PROGRESS.md), [reproduction commands](tools/oracle/README.md) and [references](THIRD_PARTY.md).

## Development

The current workflow reads a captured target root, verifies content hashes, checks the interpreter and architecture, and explains the dependency search in a controlled glibc profile. It never executes analyzed files. The real-loader tests execute only fixtures built from our own C sources.

For example, an executable's RUNPATH locates `libmiddle.so.1` but does not apply to that library's indirect dependency `libleaf.so.1`. The report shows the consumer chain and every attempted path. Adding an appropriate RUNPATH to the middle library fixes the reproduced case on x86-64 and AArch64.

After [building the reference fixtures and snapshots](tools/oracle/README.md), run:

```sh
moon run cmd/main --target js -- check --snapshot fixtures/generated/u1/x86_64/runpath/snapshot --entry /opt/relocated-demo/app --scope dependencies --format text
# Expected exit 1: the indirect dependency is missing from the search path.

moon run cmd/main --target js -- check --snapshot fixtures/generated/u1/x86_64/fixed/snapshot --entry /opt/relocated-demo/app --scope dependencies --format json
# Expected exit 0: the declared dependency checks pass.
```

`--scope dependencies` is required. `pass_static` applies only to the reported checks; symbol versions, symbol resolution, relocations, CPU requirements, permissions and application behavior have not been checked. Unsupported loading configurations produce `inconclusive`, not an empty passing graph. See the [supported profile](docs/SUPPORTED_PROFILE.md) and [snapshot schema](docs/SNAPSHOT_SCHEMA.md).

Public library entry points are `read_elf`, `load_snapshot`, and `check_dependencies`. The [namespace example](README.mbt.md) is checked by the compiler; [generated API](pkg.generated.mbti) lists the current signatures. No Mooncakes release has been published.

Windows JS development uses moon `0.1.20261012` / compiler `0.10.15`. The isolated CI archive is pinned by SHA-256 and contains moon `0.1.20261020` / compiler `0.10.16+b1a0e846e`; it does not upgrade the user's existing installation.

## License

Apache-2.0. Test sources created here use the same license unless explicitly stated otherwise. Third-party binaries will be generated or obtained from recorded recipes rather than silently bundled.
