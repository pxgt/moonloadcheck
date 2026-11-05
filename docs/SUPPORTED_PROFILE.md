# Supported deployment model

This describes implemented behavior, not all planned acceptance requirements.

## Target facts and dependency search

glibc-2.35-controlled-v1, glibc-2.35-controlled-v2 and ubuntu-noble-2.39-0ubuntu8-v1 model one ordinary startup scope for ELF64 little-endian x86-64 or AArch64. Inputs declare the loader path/digest, cwd, library path and default directories. Hardware-capability directory selection is absent, secure execution is false and preload/audit lists are empty. Do not assign a profile to an arbitrary host without verifying those facts. The Noble profile refers specifically to Ubuntu libc6 2.39-0ubuntu8, not every glibc 2.39 patch level; its cache must be disabled. The [corpus lock and recipes](CORPUS.md) record the exact package and loader identities used for validation.

These controlled revisions assume LD_DYNAMIC_WEAK is unset, retaining ordinary first-match weak lookup. The reference invocations construct their environment explicitly. A target using different loader environment switches must not be relabeled as this controlled profile.

Dependency checks cover the interpreter, architecture, ordered DT_NEEDED closure, alias/SONAME reuse, file identity, direct paths, inherited RPATH, library path, direct-only RUNPATH and defaults. ORIGIN uses the declaring object's load pathname. Missing/wrong-machine candidates continue search; directory and executable candidates stop that dependency search. Corrupt ELF evidence is input_error. Every edge records ordered candidate evidence.

RPATH/RUNPATH split only on colon; semicolons remain literal directory bytes.
An empty entire RPATH/RUNPATH is disabled, while empty colon components denote
cwd. Empty token substitutions are invalid in these profiles. Environment
paths are explicit components, with ORIGIN anchored to the main object.
[Independent environment cases](ENVIRONMENT_BOUNDARIES.md) cover competing
origins, all braced token spellings, empty/missing facts and conditional caches.

LIB and PLATFORM require explicit lib_token_hex/platform_token_hex values. Missing values are unknown when those tokens are needed. Our fixtures measure them using the actual target loader's --list-diagnostics. The analyzer never substitutes its host's architecture or directory names.

Version 1 requires disabled cache use. Version 2 additionally accepts cache_mode=glibc-cache-v1 for little-endian glibc cache 1.1 (including a compatible old/new wrapper). Lookup retains record order, architecture flags and numeric name comparison. A selected stale path does not trigger a search of the next cache record; search proceeds to defaults. NODEFLIB filters a selected cache path in a default directory and suppresses defaults. A matching record needing nonzero OS-version/hwcap conditions produces unknown. Cache tests use disposable project-owned chroots and do not change the host cache.

These decisions are tested against [glibc dependency loading](https://github.com/bminor/glibc/blob/release/2.35/master/elf/dl-load.c) and [cache selection](https://github.com/bminor/glibc/blob/release/2.35/master/elf/dl-cache.c). No implementation code from glibc is copied.

## Symbol and version scope

The compatibility scope adds bounded readers for dynamic symbols, GNU/SysV hashes, REL/RELA/JMPREL, Verneed, Verdef and Versym. Runtime program headers are authoritative; section headers are unnecessary. Hash membership is checked, including bucket/chain bounds and GNU bloom bits. Dynamic relocation references determine which symbols require lookup; an unused dynsym entry alone is not a required reference.

Version-node validation and symbol lookup are separate. Version indices are local to an object; names and hashes are matched across objects. Missing strong version nodes fail even without a corresponding symbol call. Weak version-node requirements and weak symbol references are independent. A provider without VERDEF can pass the node check, while a named provider without VERSYM can still fail a versioned symbol lookup.

The startup global lookup scope is breadth-first and is recorded separately from mapping order. Within an object, lookup follows the selected runtime hash chain; SysV order can differ from dynsym index order. The public Linkage.lookup_order exposes this validated order. Lookup respects visible definitions, first-match weak definitions, main-program interposition, versioned requests, oldest-version compatibility and the tested default/nondefault cases. Each symbol result records its consumer, requested and selected version, selected provider, lookup policy, offsets and relocation types. Lazy PLT references are checked but are labeled startup-or-first-call.

The reference rules are [glibc version validation](https://github.com/bminor/glibc/blob/release/2.35/master/elf/dl-version.c) and [symbol lookup](https://github.com/bminor/glibc/blob/release/2.35/master/elf/dl-lookup.c). Independent fixtures cover both architectures, three hash configurations, version mismatch, used/unused removed exports, weak requirements, hidden definitions, main interposition and dependency-order changes.

Additional [lookup boundary experiments](LINKAGE_BOUNDARIES.md) distinguish raw
symbol names whose lossy UTF-8 displays are identical, unused strong undefined
symbols, LOCAL/INTERNAL/HIDDEN candidates and unequal object-local version
indices. A missing lazy reference remains a static failure even when one
invocation never calls it. IFUNC definition availability can pass while the
resolved function returns an incorrect application value; resolver results
remain explicitly listed in not_checked.

## Coverage gaps

Other loader families, unknown rule revisions, preload/audit, secure execution, cache hardware conditions, filter/auxiliary loading and unmodeled DF_1 behavior remain inconclusive. Exceptional path-search behavior after ELOOP/ENOTDIR is also inconclusive. Static executables and standalone DSO entry modes are not modeled. OS ABI identifiers outside System V/GNU and nonzero ABI revisions are not verified.

COPY source lookup is supported for one RELA reference at a main executable's ordinary, nonzero-sized STT_OBJECT definition, with GLOBAL/WEAK binding, default visibility and matching symbol/destination addresses. It excludes the executable from the source scope; ordinary references to the same symbol are checked separately and can bind to the executable's copy. A missing strong source fails; a missing weak source can pass. A selected ordinary data source must have the same declared size. Size changes remain unknown because glibc can copy the smaller size and continue, leaving application compatibility unproved. The [COPY matrix](COPY.md) defines the independently exercised cases. This does not verify memory contents, destination mapping/permissions, relocation arithmetic, structure layout or all possible COPY combinations.

GNU_UNIQUE, protected/DT_SYMBOLIC combinations and COPY cases outside those conditions retain explicit unknown findings. Known symbol-free relative/TLS/IRELATIVE relocations require no external symbol lookup; unknown kinds stay unknown. Symbol existence does not validate relocation values, TLS layout or IFUNC execution. Architecture-specific reference behavior follows the fixed release's [x86-64](https://github.com/bminor/glibc/blob/glibc-2.35/sysdeps/x86_64/dl-machine.h) and [AArch64](https://github.com/bminor/glibc/blob/glibc-2.35/sysdeps/aarch64/dl-machine.h) loader references.

CPU/kernel feature requirements, permissions/ACLs, runtime dlopen, application behavior and C/C++ type/layout ABI remain outside the result. AArch64 tests run under pinned QEMU with cross-toolchain files or the locked Ubuntu runtime files. The two corpus environments contain complete startup library sets for their test programs, not full operating-system images. They do not establish compatibility with arbitrary distribution images, later patched loaders or hardware.

## Results and bounds

pass_static / exit 0 means no problem in the declared checks; fail / 1 proves a mismatch; inconclusive / 2 retains a coverage gap; input_error / 3 rejects invalid evidence. Priority is input_error, fail, inconclusive, pass_static. Lower-priority findings remain visible.

Limits include 128 MiB per ELF/blob, 256 MiB unique snapshot content, 4 MiB manifest, 20,000 namespace entries, 4,096 program headers, 65,536 dynamic entries, 2,048 loaded objects and 16,384 dependency/search steps. A cache is bounded to 16 MiB / 100,000 records. Dynamic tables are bounded to 100,000 symbols and 500,000 relocation records per object; a scope has a 200,000-symbol / 1,000,000-reference budget and a 1,000,000-step lookup budget. A dynamic string is bounded to 64 KiB, with 8 MiB of distinct string-offset data per object; repeated offsets share storage. Version-definition auxiliary traversal is bounded to 65,536 steps. Configured count/name limits return ResourceLimit separately from malformed file ranges. A comparison accepts 1..64 distinct explicit consumers. Limit failures cannot return pass_static.

These are implementation caps, not completed stress acceptance. A process-level [resource baseline](COPY.md#resource-baseline-and-fault-injection) exercises four representative commands three times per backend, with 60-second/512-MiB regression ceilings. It does not establish behavior at every parser limit. CLI file reads happen before decoded-size checks; callers handling untrusted very large files should bound the read callback before allocation. CLI entry arguments use UTF-8; the API supports byte-valued paths. Text paths are JSON-quoted.
