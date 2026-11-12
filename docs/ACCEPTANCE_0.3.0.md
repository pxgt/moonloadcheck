# MoonLoadCheck 0.3.0 acceptance evidence guide

This guide covers the complete 0.3.0 scope. It is engineering evidence, not an
organizer's acceptance decision. Check the [release record](RELEASE_0.3.0.md)
for publication status and the immutable archive identity. The 0.2.0 and 0.1.0
records remain historical evidence for those exact packages.

## User tasks

| Task | Operation and observable result | Reproduction |
| --- | --- | --- |
| Diagnose a staged deployment | Capture an explicit target; see failed dependency candidates, correct the layout and recheck | [README workflows](../README.md#try-the-three-workflows), [integration](INTEGRATION.md) |
| Check symbol/version compatibility | Find the requesting object, missing/versioned symbol and selected provider; verify an updated library repairs the finding | README U2 and independent sensor_report cases |
| Review a library change | Compare explicitly listed consumers; distinguish introduced/resolved/persistent findings while retaining unknown coverage | README U3, [saved reports](DIAGNOSTICS.md) |
| Compare application deployments across targets | Preflight missing environment facts, run multiple independent targets/applications and inspect one offline matrix | [deployment matrices](DEPLOYMENT_MATRIX.md) |

The independent `examples/sensor_report` application is original MoonBit/C and
does not import MoonLoadCheck. It runs natively on amd64 and via pinned QEMU
user-mode on AArch64 against four exact Jammy/Noble runtime identities. It is
an integration example, not an external adopter.

The external zstd recipe builds locked upstream sources and checks three exact
amd64 runtimes, including the added Jammy update. Static checks, loader success
and program behavior are recorded separately: old libzstd can satisfy symbol
checks while zstd's application version policy rejects it.

## Reproduce the evidence

Start with README's clean-checkout setup, including prerequisite installation,
pinned toolchain and fixture/runtime generation. Then use the commands below;
the CI workflow runs the complete baseline and all increments on a clean runner.

```sh
python3 tools/verify_targets.py
python3 tools/verify_deployment.py --native _build/native/debug/build/cmd/main/main.exe --js _build/js/debug/build/cmd/main/main.js
python3 tools/verify_reports.py --native _build/native/debug/build/cmd/main/main.exe --js _build/js/debug/build/cmd/main/main.js
python3 tools/verify_matrix.py --native _build/native/debug/build/cmd/main/main.exe --js _build/js/debug/build/cmd/main/main.js
python3 tools/external_example.py --native _build/native/debug/build/cmd/main/main.exe --js _build/js/debug/build/cmd/main/main.js
moon package --frozen
python3 tools/verify_archive.py --target js,native
```

The source tests cover 95 cases per backend, plus 1,070 baseline CLI checks,
fault injection and bounded resource experiments. Integration has 77 gates and
20 loader/application cases; presentation has 226 CLI checks; preflight/matrix
has 33 checks. The external recipe has 24 analyzer checks, 12 loader lists,
12 application probes, six compression roundtrips and a 12-cell matrix.
Counts overlap or measure different things; they are not summed into a single
number of independent test cases. The [73-row map](ACCEPTANCE_STATUS.md) is an
internal requirements inventory, not an official checklist.

Candidate consumption verifies four API tests per backend and 26 CLI checks.
Published 0.3.0 independently passes the same Linux JS/native consumer coverage,
plus four API tests and 13 CLI checks on Windows JS. Every run verifies all 222
installed files and normal registry dependency resolution. The
[release record](RELEASE_0.3.0.md) provides the lock and reproduction command.

## Delivery and limits

Provide source/tag, versioned Mooncakes link, CI, the README workflows, this
guide and [third-party provenance](../THIRD_PARTY.md). Keep downloaded upstream
sources, runtime roots, generated binaries and snapshots local; do not attach
those trees to a submission or CI upload. Original fixture sources and recipes
make the evidence reproducible without distributing those binaries.

Preserve the [supported-profile limits](SUPPORTED_PROFILE.md). This is not a
general Linux/C++ ABI or application-correctness certification. Preconditions
such as preload/audit/cwd are caller declarations; unsupported cases remain
inconclusive. Official forms, exact deadlines and final acceptance are governed
by the applicable November organizer notices, not this project guide.
