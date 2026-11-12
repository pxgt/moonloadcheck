# Check your own staged deployment

Use `tools/check_deployment.py` to capture an explicitly configured Linux root
and check one or more entry programs. This is a Python I/O adapter around the
MoonBit analyzer: all ELF, dependency, symbol and version decisions stay in
MoonLoadCheck. It does not execute the captured programs, use your host's
libraries, select a profile automatically or install missing libraries.

The helper is included in 0.2.0 and the current published 0.3.0 package; it is **not**
part of the immutable 0.1.0 Mooncakes archive. Build the matching CLI with the
[documented pinned compiler](../README.md#build-from-a-fresh-checkout):

```sh
moon update
moon build --target native,js
```

## Describe the target

For read-only readiness checks, multiple targets and the additional pinned
amd64 Jammy update, see [preflight and matrices](DEPLOYMENT_MATRIX.md).
Those features are included in published 0.3.0.

Capture a quiescent staged root containing the application, its loader and
runtime libraries. Relative `root` paths resolve against the configuration
file's directory, not the shell's working directory. This UTF-8 configuration
uses readable paths; the adapter converts them to the snapshot's byte encoding.
For non-UTF-8 configuration paths use the existing raw profile and collector.

```json
{
  "schema_version": 1,
  "root": "./stage",
  "entries": ["/opt/sensor-report/bin/sensor-report"],
  "scope": "compatibility",
  "profile": {
    "rule_revision": "glibc-2.35-controlled-v2",
    "loader_family": "glibc",
    "machine": 62,
    "loader_path": "/lib64/ld-linux-x86-64.so.2",
    "loader_sha256": "REPLACE_WITH_VERIFIED_TARGET_LOADER_SHA256",
    "cwd": "/",
    "default_dirs": [],
    "library_path": ["/runtime"],
    "cache_mode": "disabled",
    "hwcaps_policy": "none",
    "secure_execution": false,
    "preload": [],
    "audit": []
  }
}
```

This example describes the controlled integration deployment below, **not an
arbitrary Linux host**. Set facts from the actual target and match the
[supported profile](SUPPORTED_PROFILE.md). The loader digest is required and
checked against captured bytes; a matching digest alone does not prove that all
environment assumptions hold. Do not infer the target's defaults, architecture,
`LIB` or `PLATFORM` values from the analysis host. Supply optional `lib_token`
and `platform_token` only when measured; omit unknown values. Missing required
fields, null values, duplicate JSON keys and unknown/typo fields are errors.
An unknown rule revision is passed to the analyzer and produces inconclusive.

`default_dirs`, `library_path`, `preload`, and `audit` are explicit arrays; `[]`
means known empty. Library path elements retain literal `:`/`;` bytes and empty
elements (cwd); do not pass a colon-joined string. `scope` can be `dependencies`
or `compatibility`. At most 128 distinct absolute entry paths are accepted.
Configuration and individual JSON reports are limited to 4 MiB by this adapter;
larger reports can be produced and consumed through the CLI directly.

## Select a verified target identity

Instead of `profile`, you can supply `target`. Exactly one is required. The
catalog fixes the loader's identity; search and environment facts still have
to be supplied explicitly:

```json
{
  "schema_version": 1,
  "root": "./stage",
  "entries": ["/opt/sensor-report/bin/sensor-report"],
  "scope": "compatibility",
  "target": {
    "id": "ubuntu-jammy-arm64",
    "cwd": "/",
    "default_dirs": [],
    "library_path": ["/runtime"],
    "cache_mode": "disabled",
    "hwcaps_policy": "none",
    "secure_execution": false,
    "preload": [],
    "audit": []
  }
}
```

| Target ID | Architecture | Exact Ubuntu libc6 package |
| --- | --- | --- |
| `ubuntu-jammy-amd64` | x86-64 | 2.35-0ubuntu3 |
| `ubuntu-jammy-arm64` | AArch64 | 2.35-0ubuntu3 |
| `ubuntu-noble-amd64` | x86-64 | 2.39-0ubuntu8 |
| `ubuntu-noble-arm64` | AArch64 | 2.39-0ubuntu8 |

These are historical regression identities, not recommended OS versions or
aliases for all patched Jammy/Noble systems. [targets.json](../tools/targets.json)
records the exact package hash, loader hash/path, ELF machine and rule revision;
the [corpus lock](../tools/corpus/ubuntu.lock.json) supplies source/download
provenance. After extracting the locked roots, `python3 tools/verify_targets.py`
checks the catalog against the lock and actual loaders. `--write` is only for
an intentional, reviewed catalog update, never routine CI verification.

The helper does not detect the host or learn an expected digest from the staged
loader. A preset cannot override its identity fields. Unknown IDs, omitted
facts or simultaneous `profile`/`target` are input errors. Selecting the wrong
fixed loader also fails instead of silently changing the profile. Use raw
`profile` for other explicitly established facts; unsupported rules remain
inconclusive. A known loader identity does not certify the rest of a root, its
runtime libraries, CPU, kernel or loader environment.

## Capture and check

```sh
python3 tools/check_deployment.py --config /path/to/deployment.json \
  --out /path/to/new-check-run \
  --native "$PWD/_build/native/debug/build/cmd/main/main.exe"
```

Alternatively supply `--js "$PWD/_build/js/debug/build/cmd/main/main.js"`
with Node installed. Capture requires Linux. For analyzing an already captured
portable snapshot on Windows, use the original JS CLI directly.

The output must be a **new directory outside the staged root**. The helper
never overwrites an earlier run. It prints a JSON summary and writes:

- `profile.json`: the exact encoded target facts;
- `snapshot/`: captured inputs, for private local analysis;
- `report-000.json`, etc.: unchanged MoonBit reports, in entry order;
- `report-000.stderr`, etc.: analyzer diagnostics;
- `summary.json`: each entry's result and the aggregate CI verdict, plus
  `target_id` when a preset is selected.

Configuration failures before creating the output directory only print the
error summary. Capture/process/protocol errors after creation also leave an
input-error summary. A missing/old CLI or malformed output cannot become a pass.
Keep the generated snapshot and roots private: they may contain third-party
binaries. Review reports for internal paths before sharing them separately.

| Exit | Meaning | CI action |
| --- | --- | --- |
| 0 | Every entry passes the declared static checks | Continue |
| 1 | A confirmed deployment failure exists | Block and fix the identified requirement/path |
| 2 | A result is inconclusive | Block; supply facts or investigate the unsupported behavior |
| 3 | Configuration, snapshot, input or analyzer error | Block and repair the input/tool invocation |

For multiple entries, input errors dominate, then confirmed failures, then
inconclusive, then pass. Reports retain individual statuses and uncertainty.
Never use `|| true` or `continue-on-error` to turn a failed gate into success.

For a local visual report, pass a numbered `report-000.json` to the
[MoonBit HTML renderer](DIAGNOSTICS.md). Saved `diff --format json` output is
also accepted. The deployment helper's aggregate `summary.json` is a different
schema and is not a renderer input. Rendered HTML/CI summaries preserve the
saved verdict and do not rerun analysis.

## Add the check to an existing CI job

After your normal build/staging step has created `stage/` and a verified
`deployment.json`, check out a reviewed MoonLoadCheck revision at `.mlc`.
Install its pinned compiler, build its CLI, then run:

```yaml
- name: Check the staged deployment
  shell: bash
  run: |
    set -euo pipefail
    python3 .mlc/tools/check_deployment.py \
      --config "$GITHUB_WORKSPACE/deployment.json" \
      --out "$RUNNER_TEMP/deployment-$GITHUB_RUN_ID-$GITHUB_RUN_ATTEMPT" \
      --native "$GITHUB_WORKSPACE/.mlc/_build/native/debug/build/cmd/main/main.exe"
```

No output upload is needed. If an artifact is later desired, separately review
the selected files and licenses; do not upload the entire output directory.

## Reproduce the independent native/FFI application

The original [sensor-report application](../examples/sensor_report/README.md)
has its own module, does not import MoonLoadCheck, and is copied outside this
repository before building. It produces temperature summaries through a
separately versioned C calibration library. This is an integration example,
not an external adopter or a production device driver.

From a checkout with the README prerequisites and pinned compiler in PATH:

```sh
python3 tools/oracle/bootstrap_reference.py
python3 tools/corpus/build_roots.py
python3 tools/verify_targets.py
moon build --target native,js
python3 tools/verify_deployment.py \
  --native _build/native/debug/build/cmd/main/main.exe \
  --js _build/js/debug/build/cmd/main/main.js
```

The reference recipes require the documented Ubuntu 22.04 environment, including
privileged `chroot` execution for the independent oracle. The reusable checking
helper itself does not require privilege. Downloaded files are pinned by the
existing Ubuntu corpus lock, extracted only to ignored directories, and are not
included in the repository or Mooncakes package.

The verifier builds separate x86-64 and AArch64 copies, including each target's
MoonBit runtime and original C library. It records compiler targets/versions,
ELF machine values, program/loader/catalog hashes and QEMU identity in
`artifacts/deployment/result.json`. The run directory holds configs and reports
under `<architecture>/<suite>/<case>`.

Each architecture runs against both fixed Jammy and Noble runtime sets. Each
combination exercises `good`, `missing-library`, `old-library`, `fixed` and
`wrong-architecture`: 20 actual loader/application cases. Within an architecture
the executable digest stays identical. Its real `SENSOR_2.0` requirement fails
against `SENSOR_1.0`; restoring the current library fixes it. A library built
for the other architecture is rejected. Both analysis backends agree with
actual loading outcomes and the successful application's exact JSON values.

The complete verifier covers 77 deployment gates, 16 before/after comparisons,
eight saved-finding explanations and eight preset/raw-profile equivalence
checks (included in the gates). Sixteen separately executed business checks
cover malformed/out-of-range input and boundary/1000-reading batches on all
four targets. These distinguish application rejection from deployment failure.
Negative configuration checks retain unknown profiles, digest mismatch, mixed
entry errors, invalid/ambiguous preset selection and output-directory reuse.

x86-64 applications execute natively; **AArch64 applications actually execute
under the pinned QEMU user-mode emulator** with the target's real loader and
libraries in a controlled chroot. This is not physical ARM hardware or a full
ARM kernel/OS test. The analyzer CLI itself still runs on the x86-64 host
(native and JS). CPU features, kernel behavior, runtime `dlopen`, device I/O
and general C ABI layout remain outside the static claim.
