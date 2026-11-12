# MoonLoadCheck 0.3.0 release record

Published on 2026-11-12 as
[Xpeng/moonloadcheck@0.3.0](https://mooncakes.io/docs/Xpeng/moonloadcheck@0.3.0).
The upload returned HTTP 200. Registry metadata marks it non-yanked, and the
independently downloaded ZIP matches the reviewed candidate exactly.

| Item | Evidence |
| --- | --- |
| Reviewed source/tag | [32be7586e1851b435604753c6150c18ec7a9d215 / v0.3.0](https://github.com/pxgt/moonloadcheck/tree/v0.3.0) |
| Source CI | [43149501150](https://github.com/pxgt/moonloadcheck/actions/runs/43149501150), both jobs successful |
| Registry creation | 2026-11-12 03:47:01.802443 UTC / 11:47:01.802443 Asia/Shanghai |
| Official archive | [0.3.0.zip](https://download.mooncakes.io/user/Xpeng/moonloadcheck/0.3.0.zip), 389,079 bytes, 222 files |
| SHA-256 | `769c60fd9666f2f0a2c785985827f00b1b7ebeccf3137c5332295bc359fbf2b3` |
| Exact release lock | [tools/releases/0.3.0.json](../tools/releases/0.3.0.json) |

The immutable archive contains the reviewed prepublication documentation,
which calls 0.3.0 a candidate and identifies 0.2.0 as the then-published baseline.
This post-publication record and the registry lock are added afterward. They do
not replace the archive or move its source tag; 0.1.0 and 0.2.0 stay unchanged.

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

Post-release main contains the version lock for this exact command:

```sh
python3 tools/verify_registry.py --version 0.3.0 --target js,native
```

The completed Linux JS/native run passed four API tests per backend and 26 CLI
checks. Windows JS passed four API tests and 13 CLI checks. Every run resolved a
normal registry dependency outside any parent workspace, verified all 222
installed files byte-for-byte against the official ZIP, and preserved the
dependency graph after building a separate copy of the installed CLI sources.
Matrix summary and HTML are included. No source workspace overrides or original
repository dependency were used. CI retains all three immutable registry
versions. Local records are under `artifacts/registry/0.3.0/` and
`artifacts/release-0.3.0/`; these directories are not uploaded.

The same compiler/core passed source checks and isolated extracted-package
checks before upload. The older publication client was rejected locally for an
unsupported internal check flag; no upload occurred in those attempts. The
project's current 20261020 client then received HTTP 202 with explicit dry-run
success/no change (reported as nonzero by the client) and HTTP 200 for actual
publication. No global toolchain or credentials were changed.

## Distribution

Only source, original fixture source, recipes, metadata and license material
are distributed. Third-party runtimes, downloaded sources, built programs and
snapshots remain ignored. The unchanged ELF parser sources retain their own
Apache-2.0 license and exact provenance in [THIRD_PARTY.md](../THIRD_PARTY.md).
The archive audit verified all 18 locked upstream files including their own
license, metadata, paths, file types and every packaged file against the source.
Current-source/history checks covered 228 working files and 487 visible Git
blobs. Binary signatures, nested archives, non-UTF-8 content, long encoded
payload candidates and LFS pointers were not found. These scans are heuristic;
manual delta review identified only original release metadata/documentation,
version changes and consumer-verifier changes. No new third-party code or
binary payload was added. Runtime/download trees stay excluded, and old
releases/tags are preserved. Release engineering evidence does not constitute
official contest acceptance.
