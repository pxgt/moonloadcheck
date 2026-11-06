# MoonLoadCheck 0.1.0 release record

Published on **2026-11-07 Asia/Shanghai** (2026-11-06 17:08:48 UTC) as
[Xpeng/moonloadcheck@0.1.0](https://mooncakes.io/docs/Xpeng/moonloadcheck@0.1.0).
This is a package release, not contest registration or official acceptance.

| Evidence | Value |
| --- | --- |
| Reviewed source / tag | [eb1393d8f15b7ecf4ba68c15b629955c00334fdd / v0.1.0](https://github.com/pxgt/moonloadcheck/tree/v0.1.0) |
| Source validation | [Both CI jobs passed](https://github.com/pxgt/moonloadcheck/actions/runs/42256299828): 89 tests/backend, 1,070 existing CLI checks, fresh README and actual ZIP consumers |
| Public archive | [0.1.0.zip](https://download.mooncakes.io/user/Xpeng/moonloadcheck/0.1.0.zip), 300,999 bytes, 182 files |
| Registry SHA-256 | `ef23c9f42b99cd81feb5f1107fbc6fbefc034c68698abb2a1f3f41d5e3eae69a` |
| License / repository | Apache-2.0 / https://github.com/pxgt/moonloadcheck |
| Repeatable release lock | [tools/releases/0.1.0.json](../tools/releases/0.1.0.json) |

The Windows tool reported `Logged in as Xpeng`. Its normal `moon publish`
checked the project and independently extracted/checked the packaged module;
the publication response was `200 OK`. Live `moon view` reports this exact
version, checksum, repository, license and non-yanked state. No credentials were
copied into scripts or records. The compiler used for publication was 0.10.15;
the approved source also passed the pinned Linux 0.10.16 compiler in CI.

The downloaded public archive's SHA-256 equals the registry metadata checksum.
Every packaged file's bytes also equal those in the reviewed local candidate
(`338d2f6592049623b35dd20d1c154163b4281ff479ab6ecd9e6403274ac19c47`).
ZIP container bytes differ; identical ZIP reproduction is not claimed.

The immutable release archive retains the prepublication status text at its
source commit. This record and README status updates were added after successful
publication; they do not silently alter 0.1.0 or move its source tag. Later main
branch documentation/verification commits are not a new registry release.

## Independent published-package verification (C09)

After generating README's U3 inputs, run:

```sh
export PATH="$PWD/.tools/moon-0.10.16/bin:$PATH"
python3 tools/verify_registry.py --target js,native
```

Both targets require Node and a working native compiler. For Windows JS use
`python tools/verify_registry.py --target js`; for a Linux host without Node use
`python3 tools/verify_registry.py --target native` with the pinned compiler.

The verifier creates an unrelated temporary directory and declares the normal
versioned module dependency `"Xpeng/moonloadcheck@0.1.0"`. There is no `moon.work`,
ancestor workspace or local dependency override. Two portable before/after
snapshots are copied as explicit data inputs; the original repository is not a
dependency. `moon update`, `moon tree --json` and `moon test` resolve, install and
test the published package. The tree must say `source.kind: registry` and exactly
version 0.1.0. Each of the 182 installed files must match the independently
downloaded, checksum-pinned public ZIP.

Three tests exercise the seven public facade functions: ELF reading, linkage
reading, snapshot loading, dependency checking, compatibility checking,
consumer comparison and saved-report reading/explanation. They also check the
exported malformed-ELF and snapshot-limit error types, unchanged consumers and
the expected report version.

Windows JS and pinned Linux native each passed all three tests. The first
consumer on each host actually downloaded the new registry version; reruns may
use Moon's verified version cache. A fresh CI runner repeats both targets in
the **Consume the published Mooncakes release** step. No local workspace
substitution is used, including when a package cache is available.

Results, live metadata and dependency graphs are stored under
`artifacts/registry/<target>/` (`js-native` for the combined run). The script
requires Python assertions and bounded network access; run without `-O`.
The shared test template is [archive_consumer.mbt.txt](../tools/archive_consumer.mbt.txt),
but module resolution differs from the local archive gate.

C09 is now Covered and the internal map has 73 Covered rows. The declared
[support limits](SUPPORTED_PROFILE.md) remain unchanged. Formal contest dates,
submission materials and acceptance are separate work.
