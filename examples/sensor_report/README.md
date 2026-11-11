# Sensor report: independent MoonBit native/FFI application

This small application summarizes a batch of temperature readings. MoonBit
parses and bounds the input, calls a C calibration API, and produces a JSON
report in fixed-point milli-Celsius. The original C shared library supplies a
250 milli-Celsius offset. It models an application deployed with a separately
versioned device/calibration library; it is not a production sensor driver.

The application has its own `moon.mod` and **does not import MoonLoadCheck**.
It is an original integration example, not a claim of external adoption.
All source in this directory is Apache-2.0; see `LICENSE`. No compiled
application, library or runtime snapshot is distributed here.

## Build and use on Linux x86-64

Use the pinned MoonBit compiler described in the parent repository and GCC.
These commands are run in this directory; they also work when this directory
is copied outside the repository:

```sh
python3 build.py
moon check --target native --deny-warn
LD_LIBRARY_PATH="$PWD/_build/ffi" moon test --target native --deny-warn
LD_LIBRARY_PATH="$PWD/_build/ffi" \
  _build/native/debug/build/sensor_report.exe 19500,22000,24500
```

Expected JSON values (property order is not significant):

```json
{"samples":3,"min_milli_c":19750,"max_milli_c":24750,"mean_milli_c":22250}
```

Input is 1..1000 integer readings in -50000..100000, separated by commas.
Invalid input exits 2; the mean uses integer division. A single 100000 reading
has calibrated minimum and maximum 100250. Business-input rejection is distinct
from a deployment incompatibility: a static pass does not validate application
inputs or behavior.

## Cross-build and execute AArch64

Use a separate copy of this module for each architecture. Install the documented
`gcc-aarch64-linux-gnu` prerequisites, then run in the ARM copy:

```sh
python3 build.py --arch arm64
```

The build script selects `aarch64-linux-gnu-gcc` through `MOON_CC`. The pinned
Moon toolchain generates C and recompiles its runtime for that compiler, along
with the app's C shared library. `_build/build.json` records the compiler target
and version; the verifier checks ELF machine 183. `--arch amd64` is the default.
Both modes use the same output paths, so keep architecture builds separate.

The AArch64 executable requires an ARM loader and libraries. Do not run it as
a host x86-64 executable or link it against host libraries. From the parent
repository, follow [the integration reproduction commands](../../docs/INTEGRATION.md#reproduce-the-independent-nativeffi-application)
to execute both builds against the locked target runtimes. The verifier uses
pinned QEMU user-mode plus chroot for AArch64, and native execution for x86-64.
It runs actual application instructions and checks JSON output, input errors,
boundary values and 1000-reading batches on both Jammy and Noble.
This is not physical ARM hardware or kernel/device validation.

## Deployment layout

```text
/opt/sensor-report/bin/sensor-report
/opt/sensor-report/lib/libsensorcal.so.1
```

The executable's RUNPATH is `$ORIGIN/../lib`. It requires the real version node
`SENSOR_2.0` from our library; `native/legacy.map` deliberately supplies only
`SENSOR_1.0` to reproduce a deployment mistake. Both maps and implementations are
our own sources. They are not versions of any third-party API.

The [integration verifier](../../tools/verify_deployment.py) builds a copy of
this module in a separate temporary directory, deploys the same executable to
locked Jammy/Noble runtime roots, and compares MoonLoadCheck with actual loader
executions on x86-64 and AArch64. It demonstrates a good deployment, omitted
library, older library, restored library and a library for the wrong architecture.
See [project onboarding](../../docs/INTEGRATION.md) for
the reusable workflow, configuration and report locations.
