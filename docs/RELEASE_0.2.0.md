# MoonLoadCheck 0.2.0 release record

Published on 2026-11-11 as
[Xpeng/moonloadcheck@0.2.0](https://mooncakes.io/docs/Xpeng/moonloadcheck@0.2.0).
The server returned HTTP 200; registry metadata identifies the version as
non-yanked and its checksum matches the independently downloaded archive.

| Item | Evidence |
| --- | --- |
| Reviewed source/tag | [6aff458a500a839e47c09f80bb3798307634600f / v0.2.0](https://github.com/pxgt/moonloadcheck/tree/v0.2.0) |
| Source CI | [43027907601](https://github.com/pxgt/moonloadcheck/actions/runs/43027907601), both jobs successful |
| Registry creation | 2026-11-11 13:26:54.241278 UTC / 21:26:54.241278 Asia/Shanghai |
| Official archive | [0.2.0.zip](https://download.mooncakes.io/user/Xpeng/moonloadcheck/0.2.0.zip), 362,662 bytes, 211 files |
| SHA-256 | `8753cb907e7efa9f1a71a9517b0d8a7033e8e3503a8a0273ed921a43bca098d2` |
| Version/provenance lock | [tools/releases/0.2.0.json](../tools/releases/0.2.0.json) |

## Increment and compatibility

This version packages the deployment config/adapter, four target identities,
independent MoonBit native/FFI example and AArch64 QEMU verification, diagnostic
guidance, saved-comparison validation and local HTML/CI summaries. See the
[changelog](../CHANGELOG.md) and [acceptance guide](ACCEPTANCE_0.2.0.md).
Seven root facade signatures, snapshot schema 1 and report schema 2 stay
unchanged. `analysis.read_impact_report` is an additive public API.

The archive is the reviewed prepublication source. Its README/changelog identify
0.2.0 as a candidate because publication had not happened at that commit. This
record, the release lock and the post-publication CI gate are added afterward;
they do not silently replace the archive or move the source tag. The 0.1.0
archive, lock and tag remain unchanged.

## Actual distribution review

The downloaded official ZIP matches every reviewed candidate file; in this
release the complete ZIP digest also matches. No general reproducible-ZIP-byte
guarantee is inferred from that observation. The archive audit checks paths,
types, file content against source, and all 18 locked vendor files including
the original license. There are no distributed runtime roots, generated ELF
fixtures, snapshots, toolchain archives or nested package archives.

Before publication, review covered 217 working source files and 438 reachable
Git blobs, plus actual package contents. The binary-signature, UTF-8, long
encoded-payload and LFS-pointer scans found no candidates. These are heuristic
checks. Manual delta review identified original MoonBit/C/Python/CSS sources,
original tests and metadata; hostile HTML strings and short byte identities
are test inputs, not third-party executables. The 17 unchanged parser sources
are third-party Apache-2.0 material with their own license and exact provenance,
as described in [THIRD_PARTY.md](../THIRD_PARTY.md). No new third-party source
was copied in this increment. GitHub had no Release assets at review time;
this release adds a tag and registry package, not generated binary attachments.

## Toolchains and verification

Source CI and Linux consumer checks use pinned MoonBit 0.10.16+b1a0e846e with
moon 0.1.20261020. Windows uses the same compiler/core version; its official
toolchain ZIP has SHA-256
`50183a36dacdfb47919dffa5f06b9340b343506236940832215604e277d3f001`.
The 0.10.15 core lacks the strict JSON parser parameter required by this version.

The 20261020 Windows publication client twice failed during HTTP request upload.
The previously working moon/mooncake 20261012 client, paired locally with the
same 0.10.16 compiler/core, passed both normal source and extracted-package
checks. Its dry-run returned 202 Accepted with an explicit no-change response
(the client maps 202 to a nonzero exit); actual publication returned 200 OK.
No compiler check was skipped, no credentials were printed or copied into this
repository, and no global toolchain installation was modified.

The source CI passed 95 unit tests per backend, the existing 1,070 CLI checks,
fault-injection/resource gates, the full independent deployment matrix and
226 presentation checks. Its fresh-checkout job executed README, audited the
candidate ZIP, passed four consumer tests per backend and 22 packaged CLI
checks, and revalidated the old 0.1.0 registry dependency.

## Post-publication consumer

The new release is tested with:

```sh
python3 tools/verify_registry.py --version 0.2.0 --target js,native
```

Run this after the documented README setup from post-publication main, which
contains the release lock. Each run creates a new directory outside the
repository and any ancestor workspace, declares the normal versioned import,
and verifies `moon tree --json` selects registry version 0.2.0. All 211 installed
files must match the official ZIP exactly before any CLI build.

Four API tests per backend exercise all seven facade functions, exported errors,
the saved-comparison reader and rejection of a forged classification. The CLI
is built from a separate copy of those verified installed registry sources;
that copy never becomes a dependency override. Eleven CLI cases per backend
cover pass/fail/dependency/diff/explain/help/error, and saved check/diff HTML and
summaries. HTML decoded evidence, verdict exits and JS/native outputs agree.
The consumer dependency graph must remain unchanged after the CLI checks.

Local post-publication results are recorded separately by version/backend under
`artifacts/registry/0.2.0/`; generated snapshots, copied third-party inputs and
compiled outputs remain ignored and are not uploaded as CI artifacts.
Observed local results: Linux JS/native each passed four API tests, plus 22 CLI
checks across the two backends; Windows JS passed four API tests and 11 CLI
checks. Every run verified all 211 installed files against the same official ZIP.
The final post-publication CI repeats both 0.1.0 and 0.2.0 consumption.

Release engineering evidence is not official contest acceptance. The entrant
submits acceptance materials through the organizer's confirmed procedure.
