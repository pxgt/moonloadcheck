# 0.1.0 candidate verification and release sequence

Status: **unpublished candidate**. A local ZIP, successful CI, or a `0.1.0`
version string is not evidence that a Mooncakes release exists.

## Candidate gate

After the README setup (which generates the U3 before/after snapshots), use the
pinned Linux toolchain and run:

```sh
export PATH="$PWD/.tools/moon-0.10.16/bin:$PATH"
moon package --frozen
python3 tools/verify_archive.py --target js,native
```

This toolchain's `moon package --list` also creates a local ZIP. Neither command
publishes it. The default candidate is
`_build/publish/Xpeng-moonloadcheck-0.1.0.zip`.

The verifier checks:

- Archive metadata matches `moon.mod`; the name, version, repository and license
  are present. Actual check reports must identify that same version.
- All packaged file bytes match the current source directory. The primary
  license, third-party record and upstream lock are included; all 17 preserved
  parser sources and their license match the lock's hashes.
- No generated snapshots, downloaded tools/packages, caches, compiled ELF/PE
  artifacts or nested package archives are included. Duplicate/case-colliding
  names, path escapes and symlinks are rejected before extraction.
- A separate temporary workspace contains only the extracted candidate and an
  independent consumer. The original project is not a workspace member. Two
  portable snapshots are copied as explicit test inputs, outside the package;
  they are not redistributed in the ZIP.
- Three consumer tests per backend exercise all seven facade functions and
  exported errors. The extracted CLI is built independently and runs seven
  cases per backend: pass, symbol failure, dependency-only pass, selective diff,
  offline explain, help and argument error. Dual-backend reports must agree.

`artifacts/archive/result.json` records the ZIP SHA-256, metadata, input manifest
hashes, backend results and isolated directory. ZIP hashes identify concrete
builds; reproducible ZIP bytes across hosts/timestamps are not claimed. Run Python
without `-O`, because the verification assertions must remain enabled.

This gate initially caught an actual mismatch: the package declared `0.1.0`
while its reports emitted `0.1.0-dev`. Reports now use `0.1.0`; the older synthetic
saved-report sample deliberately retains its old tool version to test decoding.
There is no report schema or public signature change.

## Release record to finish

| Record | Required evidence |
| --- | --- |
| Source | Clean final commit on the default branch, matching reviewed release tag |
| Validation | Green full CI, fresh README job and archive-consumer gate for that commit |
| Payload | Candidate filename, SHA-256, version and provenance audit result |
| Registry | Actual successful publication and exact package/version page |
| C09 | A new consumer resolves the published version without a local workspace override |
| Submission | Confirmed November rules, entrant-authored material and actual submission receipt |

The first three can be prepared locally. The registry and C09 rows remain open
until publication happens. Do not change them to complete based on source or ZIP
workspace tests. November registration and support questions are tracked in the
private planning workspace; project release readiness is not contest approval.

## Execution order after the candidate is approved for release

1. Recheck clean source, metadata/version, exact candidate and final CI. Retain
   the [changelog](../CHANGELOG.md), [scope](SUPPORTED_PROFILE.md) and archive audit.
2. Confirm the intended Mooncakes namespace/account through the normal tool
   workflow without copying credentials into scripts, logs or documentation.
3. Publish the reviewed version using the installed toolchain's documented
   command. Record the result before claiming publication. If the tool repackages
   source, compare the downloaded registry payload with the reviewed payload.
4. Associate the reviewed source commit with the matching release tag and
   release notes. Do not move an already published release tag to different code.
5. Create an unrelated consumer with a versioned registry dependency and no
   `moon.work` or local overrides. Resolve it from the registry, check the actual
   resolved version, compile/test the facade and retain the evidence for C09.
6. Complete the entrant's submission and acceptance materials under the
   confirmed November procedure. Keep receipts and final evidence links.

This document is a preparation checklist. It does not initiate publication,
create tags, submit a form or send messages to organizers.
