# Check your own staged deployment

Use `tools/check_deployment.py` to capture an explicitly configured Linux root
and check one or more entry programs. This is a Python I/O adapter around the
MoonBit analyzer: all ELF, dependency, symbol and version decisions stay in
MoonLoadCheck. It does not execute the captured programs, use your host's
libraries, select a profile automatically or install missing libraries.

The helper is available from the source repository after 0.1.0; it is **not**
part of the immutable 0.1.0 Mooncakes archive. Build the matching CLI with the
[documented pinned compiler](../README.md#build-from-a-fresh-checkout):

```sh
moon update
moon build --target native,js
```

## Describe the target

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
- `summary.json`: each entry's result and the aggregate CI verdict.

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

The verifier records its run directory in `artifacts/deployment/result.json`.
That directory contains readable configs and reports for `good`,
`missing-library`, `old-library`, `fixed`, and `noble`. The executable digest
stays identical. Its real `SENSOR_2.0` requirement fails against `SENSOR_1.0`;
restoring the current library fixes it. Both CLI backends must agree with actual
loader outcomes and application output. `diff` records introduced/resolved
failures; `explain` reproduces the saved version finding. Additional checks cover
unknown target profiles, loader digest mismatch, mixed entry errors, invalid
configuration and output-directory reuse. A valid deployment with invalid
business input still exits 2 from the application, illustrating the static
check's boundary.

Only x86-64 native application execution is claimed here. Existing AArch64
analyzer corpus coverage is separate; AArch64 execution of this application is
future work.
