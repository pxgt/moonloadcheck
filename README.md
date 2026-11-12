# MoonLoadCheck

MoonLoadCheck is a MoonBit library and CLI for offline Linux binary deployment analysis. It explains dependency selection, checks symbol/version requirements against a captured target, and identifies explicit consumers affected by shared-library changes.

**Published: [Xpeng/moonloadcheck 0.2.0](https://mooncakes.io/docs/Xpeng/moonloadcheck@0.2.0).** U1 dependency checks, U2 symbol/version checks and U3 consumer comparisons work under controlled glibc profiles. Real hello, jq and zstd binaries are checked against pinned Ubuntu Jammy and Noble runtime roots on x86-64 and AArch64. A static pass covers the declared checks; it does not certify general Linux or full C++ ABI compatibility. See the [acceptance evidence](docs/ACCEPTANCE_STATUS.md), [API contract](docs/API_CONTRACT.md) and [release record](docs/RELEASE_0.2.0.md).

The initial target is ELF64 little-endian x86-64 and AArch64. Analysis verifies snapshot content and never executes analyzed files or falls back to host libraries. Independent reference tests execute our own fixtures and hash-verified Ubuntu packages in disposable project-owned roots.

**Checking your own application:** the [deployment onboarding guide](docs/INTEGRATION.md)
provides readable target configuration, a capture-and-check command, CI exit
handling, and an independent MoonBit native/FFI sensor-report application with
failure/fix verification across four fixed Jammy/Noble target identities.
The application executes natively on x86-64 and under pinned QEMU on AArch64.
These additions are included in the **published 0.2.0 package**;
they are not included in the immutable 0.1.0 registry archive. See the
[0.2.0 acceptance guide](docs/ACCEPTANCE_0.2.0.md) for scope and reproduction.

**Reading the result:** the [diagnostic and local HTML guide](docs/DIAGNOSTICS.md)
shows how to turn saved check/diff JSON into an offline, script-free page or a
concise CI summary. Both retain the recorded verdict and uncertainty.

**0.3.0 release candidate:** [target preflight and deployment matrices](docs/DEPLOYMENT_MATRIX.md)
check missing environment facts, combine multiple targets/applications into one
offline report, and demonstrate an external zstd source-build integration with
an additional pinned Jammy runtime. These additions are not in published 0.2.0.
See the [0.3.0 acceptance guide](docs/ACCEPTANCE_0.3.0.md) and
[release record](docs/RELEASE_0.3.0.md) for the candidate/publication distinction.

## Build from a fresh checkout

The reproducible quickstart uses **Ubuntu 22.04 x86-64**, including that WSL
distribution. It needs Python 3.10+, Git, GCC, binutils, an AArch64 cross compiler,
tar and dpkg-deb, plus network access for hash-checked downloads. These commands
install the OS prerequisites if they are missing:

```sh
sudo apt-get update
sudo apt-get install -y python3 git build-essential gcc-aarch64-linux-gnu binutils-aarch64-linux-gnu
git clone https://github.com/pxgt/moonloadcheck.git
cd moonloadcheck
```

In that checkout, run this setup in Bash. The MoonBit compiler is installed only
under `.tools`; generated target snapshots stay under `fixtures/generated`.
No preinstalled MoonBit compiler or registry release of this project is needed.
The `mlc` shell function invokes the Linux native CLI.

<!-- walkthrough:setup exit=0 -->
```sh
python3 tools/bootstrap_moon.py
export PATH="$PWD/.tools/moon-0.10.16/bin:$PATH"
moon update
python3 tools/oracle/bootstrap_reference.py
python3 tools/oracle/build_fixtures.py
python3 tools/oracle/build_u1_snapshots.py
python3 tools/oracle/build_u2_snapshots.py
python3 tools/oracle/build_u3_snapshots.py
moon build --target native,js
mlc() { "$PWD/_build/native/debug/build/cmd/main/main.exe" "$@"; }
mkdir -p artifacts/walkthrough
```

## Try the three workflows

Expected failures below return **exit 1**. Run these commands interactively, or
handle that exit explicitly in CI; a shell using `set -e` would otherwise stop.
`mlc --help` prints the accepted command forms. Options use the shown fixed order;
unknown, duplicate, leading or trailing extra arguments are rejected.

**U1: relocate an application.** RUNPATH on an executable does not propagate to a library's indirect dependency. Inspect the search chain, then compare the corrected layout:

<!-- walkthrough:u1-failure exit=1 -->
```sh
mlc check --snapshot fixtures/generated/u1/x86_64/runpath/snapshot --entry /opt/relocated-demo/app --scope dependencies --format json
```

Exit 1 identifies the missing indirect dependency and includes its search trace.
The corrected layout passes:

<!-- walkthrough:u1-fixed exit=0 -->
```sh
mlc check --snapshot fixtures/generated/u1/x86_64/fixed/snapshot --entry /opt/relocated-demo/app --scope dependencies --format json
```

**U2: deploy the same program against a different library baseline.** The first environment supplies DEMO_2; the second supplies only DEMO_1. These are our test library's versions, not invented GLIBC versions.

<!-- walkthrough:u2-new exit=0 -->
```sh
mlc check --snapshot fixtures/generated/u2/x86_64/new-environment/snapshot --entry /opt/demo/app --scope compatibility --format json
```

The unchanged program fails in the older view with the precise requirement:

<!-- walkthrough:u2-old exit=1 -->
```sh
mlc check --snapshot fixtures/generated/u2/x86_64/old-environment/snapshot --entry /opt/demo/app --scope compatibility --format json
```

**U3: change a library shared by two consumers.** Removing the api export breaks app; stable-app uses the unchanged stable export and passes. Both complete views are recomputed, including dependency selection.

<!-- walkthrough:u3-introduced exit=1 -->
```sh
mlc diff --before fixtures/generated/u3/x86_64/before/snapshot --after fixtures/generated/u3/x86_64/after/snapshot --entries fixtures/generated/u3/entries.json --format json
```

This returns exit 1 with an introduced failure only for `/opt/demo/app`.
Restoring the earlier library resolves that failure and returns exit 0:

<!-- walkthrough:u3-resolved exit=0 -->
```sh
mlc diff --before fixtures/generated/u3/x86_64/after/snapshot --after fixtures/generated/u3/x86_64/before/snapshot --entries fixtures/generated/u3/entries.json --format json
```

All examples also have AArch64 snapshots. Exit codes are 0 pass_static,
1 fail, 2 inconclusive, 3 input_error. Replace `--format json` with
`--format text` for a readable summary. The [supported profile](docs/SUPPORTED_PROFILE.md)
defines exactly what a pass covers.

Save a JSON check report to explain a finding later, without the snapshot:

<!-- walkthrough:save-report exit=1 -->
```sh
mlc check --snapshot fixtures/generated/u2/x86_64/used-export-removed/snapshot --entry /opt/demo/app --scope compatibility --format json > artifacts/walkthrough/report.json
```

The saved check returns exit 1. Select its actual finding ID, then explain it:

<!-- walkthrough:explain exit=0 -->
```sh
finding_id=$(python3 -c 'import json; print(json.load(open("artifacts/walkthrough/report.json"))["findings"][0]["id"])')
mlc explain --report artifacts/walkthrough/report.json --finding "$finding_id"
```

For a real staged deployment, supply an explicit target profile to the [Linux snapshot collector](docs/SNAPSHOT_SCHEMA.md). Target LIB/PLATFORM values, loader digest, search paths and cache policy must come from that target.

The [real-program corpus](docs/CORPUS.md) reproduces a concrete migration failure: Noble's hello and jq fail on the Jammy runtime with GLIBC_2.38 requirements; jq also needs jq_set_stderr_cb from a newer libjq. The unchanged zstd executable passes this migration. The same matrix checks both successful deployments and failures against actual loader executions.

## Library and evidence

Compile and test an independent consumer against this checkout without publishing:

<!-- walkthrough:consumer exit=0 -->
```sh
python3 tools/verify_consumer.py
```

That test uses only the public facade from a separate temporary Moon workspace.
The [published-release consumer](docs/RELEASE_0.2.0.md) instead resolves
`"Xpeng/moonloadcheck@0.2.0"` through the registry with no workspace override,
tests all seven facade functions and checks the installed bytes against the
published archive. It also runs in CI.
The [candidate release checklist](docs/RELEASE_CHECKLIST.md) additionally audits
the actual packaged ZIP and builds a consumer against its extracted contents.
The [reviewer demo](docs/DEMO.md) provides a short evidence-led presentation.
For the full test suite, first run **all** fixture recipes and then the test
commands in [Rebuilding reference cases](tools/oracle/README.md). The quickstart
above generates the three user workflows; the full suite also requires the
cache, real-program, binding and resource fixtures. Full JS tests require Node
in PATH; CI tests both JS and native. A separate fresh CI job executes the actual
README command blocks using `python3 tools/verify_walkthrough.py --require-clean`.

To analyze portable snapshots on Windows, build the JS CLI with your installed
MoonBit toolchain (`moon build --target js`) and invoke
`node _build/js/debug/build/cmd/main/main.js` in place of `mlc`. Capture or generate
the target snapshots on Linux first; copied snapshots do not require Linux
libraries on the Windows host. Linux native binaries cannot run on Windows.

The public facade offers read_elf, read_linkage, load_snapshot, check_dependencies, check_compatibility, compare and read_report. Public data types live in model, snapshot and analysis; internal parser types do not leak through the facade. See the [compiler-checked library example](README.mbt.md), [generated API](pkg.generated.mbti), [report schema](docs/REPORT_SCHEMA.md), [COPY validation and resource baseline](docs/COPY.md), [path/input boundaries and fault detection](docs/BOUNDARIES.md), [symbol and parser boundary evidence](docs/LINKAGE_BOUNDARIES.md), [73-case acceptance evidence map](docs/ACCEPTANCE_STATUS.md) and [development evidence](docs/PROGRESS.md).

The ELF parser from moonbit-community/elf 0.0.1 is preserved as a hash-locked dependency with its license. New runtime-table readers and deployment analysis are separate original implementation; this is a new project. See [references and provenance](THIRD_PARTY.md).

[Environment boundary evidence](docs/ENVIRONMENT_BOUNDARIES.md) covers competing
ORIGIN contexts, all token spellings, literal semicolons in RPATH/RUNPATH,
conditional cache records, and the distinction between empty and missing facts.

[Binding and resource evidence](docs/MATURITY_BOUNDARIES.md) adds real TLS type
collisions, GLIBCXX runtime version failures and production-count boundary tests.

Windows JS development uses compiler 0.10.15. CI and Linux native use the isolated, hash-pinned archive containing moon 0.1.20261020 / compiler 0.10.16+b1a0e846e. It does not upgrade other projects' toolchains.

## Troubleshooting

- An input error has exit 3 and a JSON `error_kind`/`message`, even with text
  output requested. A missing file names the read operation and path; a missing
  blob names its digest. Restore or recapture the evidence before retrying.
- An inconclusive result has exit 2. Read `not_checked` and unknown findings;
  supply measured target facts or use a supported profile where applicable.
- Use `read_report`/`explain` only for schema-2 check reports. Diff reports and
  command-error envelopes are different shapes. Schema 1 is explicitly rejected.
- Quickstart reference runs depend on the stated Ubuntu environment. A failed
  reference assertion on another distribution is not a supported setup. Use the
  specified environment or the pinned corpus recipe; do not change expected exits.

## License

Apache-2.0. Reference binaries are generated or obtained through recorded recipes and are not silently redistributed.
