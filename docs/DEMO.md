# Reviewer demonstration

Allow about 6–8 minutes after setup. Follow the [README](../README.md) in Ubuntu
22.04 first. Its `mlc` function invokes the native CLI. The README verifier covers
the three controlled workflows and saved-report explanation. Exit 1 is an expected demonstrated
failure; do not run the sequence under an unhandled `set -e`.

## 1. Explain a deployment-path failure (about 90 seconds)

```sh
mlc check --snapshot fixtures/generated/u1/x86_64/runpath/snapshot --entry /opt/relocated-demo/app --scope dependencies --format text
mlc check --snapshot fixtures/generated/u1/x86_64/fixed/snapshot --entry /opt/relocated-demo/app --scope dependencies --format text
```

Show the missing indirect library, dependency chain and searched candidates.
The executable's RUNPATH does not propagate to that indirect lookup. The second
layout supplies the required path on the relevant DSO and passes. The analyzer
reads the snapshot; the separate oracle recorded actual loader behavior.

## 2. Compare an unchanged program across targets (about 90 seconds)

```sh
mlc check --snapshot fixtures/generated/u2/x86_64/new-environment/snapshot --entry /opt/demo/app --scope compatibility --format json
mlc check --snapshot fixtures/generated/u2/x86_64/old-environment/snapshot --entry /opt/demo/app --scope compatibility --format json
```

Point to the equal program SHA-256 in `objects`, then the exact missing DEMO_2
version in `version_checks`. These are our controlled library's version names.
The project does not label invented symbols as GLIBC release evidence.

For the independently recorded real migration, after generating the full corpus:

```sh
mlc check --snapshot fixtures/generated/corpus/amd64/noble-on-jammy/snapshot --entry /usr/bin/hello --scope compatibility --format json
mlc check --snapshot fixtures/generated/corpus/amd64/noble-on-jammy/snapshot --entry /usr/bin/zstd --scope compatibility --format json
```

The pinned Noble hello fails with a GLIBC_2.38 requirement; the unchanged zstd
passes the same downgrade. [CORPUS.md](CORPUS.md) contains the two-architecture
matrix, exact package versions and reference-execution limitations.

## 3. Attribute a library change to explicit consumers (about 90 seconds)

```sh
mlc diff --before fixtures/generated/u3/x86_64/before/snapshot --after fixtures/generated/u3/x86_64/after/snapshot --entries fixtures/generated/u3/entries.json --format json
mlc diff --before fixtures/generated/u3/x86_64/after/snapshot --after fixtures/generated/u3/x86_64/before/snapshot --entries fixtures/generated/u3/entries.json --format json
```

Show `introduced` for `/opt/demo/app`, an unaffected `/opt/demo/stable-app`, and
`application_changed: false`. Reversing the views demonstrates `resolved`.
This is consumer analysis, not a list of all removed exports or a claim about
unlisted applications and runtime dlopen callers.

## 4. Explain and consume the result (about 90 seconds)

Use README's saved-report and `explain` commands to show the finding ID, raw-byte
identity, explanation and suggested action without reopening a snapshot. Then
show the independent registry-consumer result from
`artifacts/registry/<version>/js-native/result.json` in CI, or the local
`js`/`native` subdirectories, and its matching CI step. Point to the registry
source, exact version and installed files matching the published checksum.

State the four outcomes: static pass, proven failure, inconclusive, and invalid
input. Show [scope](SUPPORTED_PROFILE.md), [evidence map](ACCEPTANCE_STATUS.md)
and [API contract](API_CONTRACT.md). Ordinary COPY/TLS combinations have focused
evidence; unsupported binding combinations and full C++ ABI remain outside the
claim. Successful real libstdc++ executions can still be statically inconclusive.

## Evidence to retain

- Final source commit and CI URL; no guessed publication date or package URL.
- README command outputs under `artifacts/walkthrough`, actual reference
  `oracle.json` records and the full corpus verification results.
- Published ZIP digest, source tag and registry-consumer record from the
  [release record](RELEASE_0.2.0.md). Keep local candidate checks separately.
- A screen recording, if requested by the final rules, showing actual commands
  and expected exits. This runbook does not claim a recording already exists.
