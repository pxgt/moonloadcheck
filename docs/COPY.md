# COPY relocation validation

Ordinary relocations can resolve a data symbol to the main executable's copy.
The COPY relocation itself must find an initialization source elsewhere in the
startup scope. Grouping those relocations together can report the wrong provider,
including in MoonLoadCheck's own native executable. They are now analyzed as
separate reference classes with independent provider and size evidence.

## Independent matrix

tools/corpus/build_copy.py compiles our copy_app.c/copy_data.c sources and runs
them against both locked Ubuntu runtimes, on x86-64 and AArch64. It records
compiler versions, program/library/loader digests, readelf relocations and actual
execution errors. References are [glibc's executable exclusion](https://github.com/bminor/glibc/blob/glibc-2.39/elf/dl-lookup.c),
[x86-64 copy behavior](https://github.com/bminor/glibc/blob/glibc-2.39/sysdeps/x86_64/dl-machine.h)
and [AArch64 copy behavior](https://github.com/bminor/glibc/blob/glibc-2.39/sysdeps/aarch64/dl-machine.h).
No implementation source is copied from glibc.

| Case | Actual execution | Static result |
| --- | --- | --- |
| Equal-size versioned object | Correct initial value; DSO references see main copy | pass_static; library supplies COPY, executable supplies ordinary reference |
| PIE | Correct value | pass_static; x86-64 has COPY, AArch64 compiler emits GLOB_DAT instead |
| Missing strong source | Undefined data symbol; exit 127 | fail |
| Missing weak source | Continues with zero-initialized destination | pass_static, no source selected |
| Smaller source (8 vs 16 bytes) | Continues with observed prefix/zero tail | inconclusive, both sizes recorded |
| Larger source (32 vs 16 bytes) | Size warning, continues | inconclusive, both sizes recorded |
| Weak provider first | Uses value 7; DSO references use main copy | pass_static, first library selected |
| Strong provider first | Uses value 9 | pass_static, second library selected |
| Version node exists, data has wrong version | Undefined versioned data symbol; exit 127 | fail |
| Provider changed to protected visibility | This minimal patched fixture runs | inconclusive; protected combinations remain outside the model |

Each case runs on both architectures and both runtimes: **40 actual executions**,
including 38 COPY cases and two AArch64 PIE/GOT controls. Protected visibility is
changed only after linking, because ordinary linkers may reject direct COPY
references to protected definitions. These results do not generalize to every
protected symbol/property combination. Small/large providers demonstrate why
process exit alone cannot certify data-layout compatibility.

The native MoonBit CLI adds two x86-64 deployment checks. Its stdout, stderr and
__environ COPY sources resolve to libc with matching eight-byte sizes. Its
ordinary stdout/stderr references bind separately to its own copies. Both actual
invocations and static checks now pass under the declared model. Native AArch64
self-hosting is still unverified.

## Contract and remaining scope

Support is limited to the ordinary object cases stated in
[SUPPORTED_PROFILE.md](SUPPORTED_PROFILE.md). Nonstandard destinations, zero-size
objects, non-object providers, COPY in DSOs, repeated COPY relocations for a
symbol, GNU_UNIQUE and protected/SYMBOLIC combinations remain inconclusive.
The analyzer does not certify actual copied contents, relocation arithmetic,
writable mappings or C/C++ layouts.

Schema 2 gains optional source/destination size strings; old schema-2 reports
without them still decode. Multiple unknown checks for one requirement merge
into one finding identity while retaining offsets and explanations. Saved
reports with duplicate identities are rejected. A report-contract regression
also preserves known failures when an unknown resource-limit diagnostic exists;
this is a contract test, not an end-to-end exhaustion benchmark.

## Resource baseline and fault injection

tools/corpus/measure.py runs jq on Noble, jq on Jammy, the three-program downgrade
diff, and the COPY size-gap check three times per backend. It records process wall
time, peak RSS (GNU time, including the Node process for JS), report size, kernel,
architecture, CPU count and revision in artifacts/performance.json. Repeated
reports must match. Each process has a 60-second deadline with process-group
termination and a 512-MiB measured peak-RSS ceiling. These generous regression
ceilings are not a heap sandbox or evidence for worst-case hostile inputs.

tools/verify_copy_mutations.py makes a disposable source copy outside the checkout,
runs the unchanged tests, then introduces two wrong rules separately: allowing
COPY to bind the executable, and ignoring differing sizes. Both must cause an
assertion failure; compilation errors or missing inputs do not count. Original
working sources are never edited by the mutation experiment. The five broader
fault classes in the planned C12 acceptance item remain to be completed.

```sh
python3 tools/corpus/build_copy.py
moon build --target js,native
moon test --target js,native
python3 tools/corpus/verify_copy.py --js _build/js/debug/build/cmd/main/main.js --native _build/native/debug/build/cmd/main/main.exe
python3 tools/corpus/self_host.py --js _build/js/debug/build/cmd/main/main.js --native _build/native/debug/build/cmd/main/main.exe
python3 tools/corpus/measure.py --js _build/js/debug/build/cmd/main/main.js --native _build/native/debug/build/cmd/main/main.exe
python3 tools/verify_copy_mutations.py
```

Run the existing toolchain and corpus prerequisites first. Generated inputs,
oracles, reports and measurements are ignored artifacts; CI regenerates them.
