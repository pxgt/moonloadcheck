# MoonLoadCheck 0.2.0 acceptance evidence guide

This is a technical evidence index, not an organizer's acceptance decision.
The published 0.2.0 release consolidates project onboarding, target presets, an
independent MoonBit native/FFI example, diagnostic guidance and offline reports.
The 73-item [internal matrix](ACCEPTANCE_STATUS.md) retains the baseline scope;
it is not a list of official contest requirements.

## User scenarios and observable results

| Need | Reproduction and expected evidence |
| --- | --- |
| Move an application with private shared libraries | README U1: indirect RUNPATH lookup fails, corrected deployment passes; inspect dependency chain and searched paths. |
| Deploy against a different runtime baseline | README U2 and locked real-program corpus: unchanged application, exact missing symbol/version, explicit inconclusive outcome outside the profile. |
| Review a shared-library update for known consumers | README U3: introduced failure for one consumer, unchanged pass for the other; reverse comparison resolves the failure. |
| Integrate a real MoonBit native/FFI application into CI | Independent sensor-report app: business output and actual loader behavior agree with good/missing/old/fixed/wrong-architecture cases across four target identities. |
| Review saved diagnostics without the original target | Saved check/diff JSON becomes local HTML and a concise CI summary with the same verdict. Expand evidence and compare consumers without scripts or network requests. |

## What changed since 0.1.0

- Original `tools/check_deployment.py` adapter and explicit UTF-8 project config;
  MoonBit remains responsible for all ELF, dependency and compatibility decisions.
- Four source-locked Jammy/Noble amd64/arm64 presets. Caller-supplied loader
  environment facts remain mandatory; preset names do not establish those facts.
- `examples/sensor_report`: an independent module with MoonBit business logic,
  original C FFI library and version maps. It does not depend on MoonLoadCheck.
- MoonBit diagnostic guidance for MLC001–009 and script-free HTML/CI summaries.
  Saved comparisons are validated using the same classification rules as live
  comparisons, including nested verdicts and ordered changes.
- Additive `analysis.read_impact_report`; seven root API signatures and snapshot
  schema 1/report schema 2 remain unchanged.

## Reproduce the evidence

Use Ubuntu 22.04, the prerequisites and pinned compiler in the [README](../README.md).
Run the README sequence first. The full ordered source of commands is the
[CI workflow](../.github/workflows/ci.yml); it builds original samples and
downloads locked runtime inputs locally, without uploading generated payloads.

| Gate | Evidence and count |
| --- | --- |
| Unit tests | 95 tests per JS/native backend; preserve this count separately from CLI cases. |
| Existing analysis regression | 1,070 CLI checks, seven fault-injection classes, 24 resource-baseline and 16 stress measurements. These are finite observed cases, not exhaustive ELF correctness. |
| Independent deployment | `verify_deployment.py`: 20 actual loader executions, 77 gates, 16 comparisons, eight explanations, 16 business-output checks; counts overlap and must not be summed as unique tests. |
| Presentation | `verify_reports.py`: 226 CLI checks, valid/invalid saved inputs, escaping, raw evidence, unknown diagnostics, backend parity and verdict preservation. |
| Candidate package | `moon package --frozen`; `verify_archive.py --target js,native`: actual payload/provenance audit, four external API tests per backend and 22 CLI checks. |
| Published package | After publication, `verify_registry.py --version 0.2.0 --target js,native`: exact registry dependency, no workspace override, every installed file compared with the official ZIP, four API tests per backend and 22 CLI checks from a verified registry-source copy. |

The published-package command uses the [release lock](../tools/releases/0.2.0.json).
The [release record](RELEASE_0.2.0.md) distinguishes the source commit, final CI,
candidate ZIP and actual registry ZIP. The immutable source tag is `v0.2.0`;
run the post-publication verifier from current main, where the lock is recorded.

For the incremental demonstration, after the full CI setup/build steps:

```sh
python3 tools/verify_targets.py
python3 tools/verify_deployment.py --native _build/native/debug/build/cmd/main/main.exe --js _build/js/debug/build/cmd/main/main.js
python3 tools/verify_reports.py --native _build/native/debug/build/cmd/main/main.exe --js _build/js/debug/build/cmd/main/main.js
```

See [INTEGRATION.md](INTEGRATION.md) for a single-app config and capture/check
command, [DIAGNOSTICS.md](DIAGNOSTICS.md) for HTML generation, and
[DEMO.md](DEMO.md) for the baseline review sequence. Expected failure exit 1
and inconclusive exit 2 are part of the demonstration, not harness failures.

## Claims and distribution boundaries

- x86-64 application runs are native. AArch64 application instructions run under
  pinned QEMU user emulation/chroot. This does not establish physical ARM device
  or ARM-kernel behavior. Analyzer backends are host native and JS.
- Static pass covers the declared controlled ELF64/glibc profile. Full C++ ABI,
  runtime `dlopen`, arbitrary loaders and application correctness remain outside
  the result. An unsupported case can be inconclusive even if a program runs.
- The independent example is our original example, not a third-party adopter.
- The 17 vendored Apache-2.0 parser sources are identified separately from
  original work, preserved byte-for-byte with their license and provenance lock.
- No third-party executable/runtime root, generated snapshot, compiled example
  or encoded binary fixture is intended for distribution. Local downloads retain
  their package notices; recipes and hashes are distributed. See
  [THIRD_PARTY.md](../THIRD_PARTY.md) for the exact boundary and any later
  redistribution obligations. Archive checks do not establish universal license
  compliance beyond the specific provenance conditions reviewed.

## Submission handoff

Provide the public source/tag, package page, final green CI, README, this index,
demo instructions and release record. Keep generated runtime roots and snapshots
out of attachments. If an organizer requests a video or additional form fields,
prepare those against that request; this guide does not invent a format or claim
that a video, submission receipt or final approval already exists.
