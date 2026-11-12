# MoonLoadCheck 0.3.0 release record

This source is the 0.3.0 release candidate. Publication and registry-only
consumer evidence will be recorded here after those steps actually complete.
The published baseline is [0.2.0](RELEASE_0.2.0.md); no old archive or tag moves.

## Increment

This release consolidates dependency preflight, multi-target/application
matrices, an additional exact Jammy amd64 runtime and the external zstd
source-build verification. MoonBit owns ELF decisions, nested-report validation,
verdict aggregation and offline HTML rendering. Python handles input capture,
configuration and test orchestration.

The seven root facade functions and existing snapshot/check/comparison schemas
are unchanged. Matrix evidence uses its own schema 1. A static pass remains
limited to declared checks; an application may reject a loadable library.
See the [acceptance guide](ACCEPTANCE_0.3.0.md) and [changelog](../CHANGELOG.md).

## Verification gates

Use the pinned compiler 0.10.16+b1a0e846e (moon 0.1.20261020). The source CI
checks both JS/native backends, the independent x86-64/AArch64 FFI application,
the external zstd cases, README from a fresh checkout, actual candidate ZIP
contents and separate package consumers. AArch64 execution uses QEMU, not
physical ARM hardware.

After publication, post-release main will contain `tools/releases/0.3.0.json`
for this exact command:

```sh
python3 tools/verify_registry.py --version 0.3.0 --target js,native
```

It must resolve a normal registry dependency outside any parent workspace,
verify installed bytes against the registry archive, pass four API tests per
backend, and exercise thirteen CLI cases per backend including matrix summary
and HTML. A local candidate workspace cannot close the registry gate.

## Distribution

Only source, original fixture source, recipes, metadata and license material
are distributed. Third-party runtimes, downloaded sources, built programs and
snapshots remain ignored. The unchanged ELF parser sources retain their own
Apache-2.0 license and exact provenance in [THIRD_PARTY.md](../THIRD_PARTY.md).
The actual archive audit must pass before upload. Release engineering evidence
does not constitute official contest acceptance.
