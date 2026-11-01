# MoonLoadCheck

MoonLoadCheck is a MoonBit library and CLI for offline Linux binary deployment analysis. It explains dependency selection, checks symbol/version requirements against a captured target, and identifies explicit consumers affected by shared-library changes.

**Status: U1 dependency checks, U2 symbol/version checks and U3 consumer comparisons work under controlled glibc profiles.** Real hello, jq and zstd binaries are checked against pinned Ubuntu Jammy and Noble runtime roots on x86-64 and AArch64. This is a development version, not a general Linux compatibility certificate. The broader acceptance matrix and stress testing remain in progress. No Mooncakes package has been published.

The initial target is ELF64 little-endian x86-64 and AArch64. Analysis verifies snapshot content and never executes analyzed files or falls back to host libraries. Independent reference tests execute our own fixtures and hash-verified Ubuntu packages in disposable project-owned roots.

## Try the three workflows

First follow the [reference setup and fixture recipes](tools/oracle/README.md). They generate portable snapshots; binary fixtures are not checked into Git. Use a recent MoonBit toolchain and Node for JS, or the pinned Linux compiler and a C toolchain for native.

**U1: relocate an application.** RUNPATH on an executable does not propagate to a library's indirect dependency. Inspect the search chain, then compare the corrected layout:

```sh
moon run cmd/main --target js -- check --snapshot fixtures/generated/u1/x86_64/runpath/snapshot --entry /opt/relocated-demo/app --scope dependencies --format text
# Exit 1: missing indirect dependency.
moon run cmd/main --target js -- check --snapshot fixtures/generated/u1/x86_64/fixed/snapshot --entry /opt/relocated-demo/app --scope dependencies --format json
# Exit 0.
```

**U2: deploy the same program against a different library baseline.** The first environment supplies DEMO_2; the second supplies only DEMO_1. These are our test library's versions, not invented GLIBC versions.

```sh
moon run cmd/main --target js -- check --snapshot fixtures/generated/u2/x86_64/new-environment/snapshot --entry /opt/demo/app --scope compatibility --format json
# Exit 0.
moon run cmd/main --target js -- check --snapshot fixtures/generated/u2/x86_64/old-environment/snapshot --entry /opt/demo/app --scope compatibility --format json
# Exit 1: required version/symbol unavailable.
```

**U3: change a library shared by two consumers.** Removing the api export breaks app; stable-app uses the unchanged stable export and passes. Both complete views are recomputed, including dependency selection.

```sh
moon run cmd/main --target js -- diff --before fixtures/generated/u3/x86_64/before/snapshot --after fixtures/generated/u3/x86_64/after/snapshot --entries fixtures/generated/u3/entries.json --format text
# Exit 1, introduced failure only for /opt/demo/app.
# Swap --before and --after to demonstrate a resolved failure, exit 0.
```

All examples also have AArch64 snapshots. CLI options currently use the fixed order shown. Exit codes are 0 pass_static, 1 fail, 2 inconclusive, 3 input_error. The [supported profile](docs/SUPPORTED_PROFILE.md) defines exactly what a pass covers.

Save a JSON check report to explain a finding later, without the snapshot:

```sh
moon build --target js
node _build/js/debug/build/cmd/main/main.js check --snapshot fixtures/generated/u2/x86_64/used-export-removed/snapshot --entry /opt/demo/app --scope compatibility --format json > report.json
# Replace ID with a findings[].id from report.json.
node _build/js/debug/build/cmd/main/main.js explain --report report.json --finding ID
```

For a real staged deployment, supply an explicit target profile to the [Linux snapshot collector](docs/SNAPSHOT_SCHEMA.md). Target LIB/PLATFORM values, loader digest, search paths and cache policy must come from that target.

The [real-program corpus](docs/CORPUS.md) reproduces a concrete migration failure: Noble's hello and jq fail on the Jammy runtime with GLIBC_2.38 requirements; jq also needs jq_set_stderr_cb from a newer libjq. The unchanged zstd executable passes this migration. The same matrix checks both successful deployments and failures against actual loader executions.

## Library and evidence

The public facade offers read_elf, read_linkage, load_snapshot, check_dependencies, check_compatibility, compare and read_report. Public data types live in model, snapshot and analysis; internal parser types do not leak through the facade. See the [compiler-checked library example](README.mbt.md), [generated API](pkg.generated.mbti), [report schema](docs/REPORT_SCHEMA.md) and [development evidence](docs/PROGRESS.md).

The ELF parser from moonbit-community/elf 0.0.1 is preserved as a hash-locked dependency with its license. New runtime-table readers and deployment analysis are separate original implementation; this is a new project. See [references and provenance](THIRD_PARTY.md).

Windows JS development uses compiler 0.10.15. CI and Linux native use the isolated, hash-pinned archive containing moon 0.1.20261020 / compiler 0.10.16+b1a0e846e. It does not upgrade other projects' toolchains.

## License

Apache-2.0. Reference binaries are generated or obtained through recorded recipes and are not silently redistributed.
