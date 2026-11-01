# Current dependency model

This document describes implemented M1 behavior, not the complete planned product.

`glibc-2.35-controlled-v1` models one ordinary startup loading scope for ELF64
little-endian x86-64 or AArch64. Inputs must explicitly declare a glibc loader
path and digest, cwd, library path and default directories. Cache use is disabled,
hardware-capability directory selection is absent, secure execution is false,
and preload/audit lists are empty. This is a controlled deployment profile; it
must not be assigned to an arbitrary captured host without verifying those facts.

Implemented checks:

- An indexed interpreter matches the declared digest; interpreter absence and
  architecture mismatch have separate findings.
- Ordered DT_NEEDED closure, name/SONAME reuse and file-identity reuse. Original
  declaration order is retained and cycles do not recurse indefinitely.
- Direct dependency paths, inherited RPATH, explicit library path, direct-only
  RUNPATH and declared defaults; DF_1_NODEFLIB suppresses default directories.
- ORIGIN is expanded on the object that declares the path. A DSO's load pathname
  determines its ORIGIN while its resolved file identity remains separate.
- Missing candidates and wrong-machine candidates do not terminate ordinary
  name search. A directory or executable occupying a library candidate stops
  that dependency search. Malformed ELF evidence is input_error.
- Every edge retains its consumer, requested name, selected object and ordered
  candidate trace. Linux names are compared as bytes, not display strings.

The current independent U1 corpus has seven cases on each architecture: broken
indirect RUNPATH, inherited RPATH, fixed RUNPATH, wrong-machine first candidate,
directory first candidate, PIE first candidate, and symlink-dependent ORIGIN.
Both native x86-64 and AArch64 under QEMU execute our fixtures with explicit
loader options. The snapshot has the same application/library layout relocated
to a target namespace; JSON results are host independent.

The rule model follows the [Linux loader documentation](https://man7.org/linux/man-pages/man8/ld.so.8.html)
and checks subtle behavior against [glibc 2.35's loader](https://github.com/bminor/glibc/blob/release/2.35/master/elf/dl-load.c).
Those sources are references; no glibc implementation source is copied here.

## Coverage gaps

Nonempty cache/preload/audit, secure execution, other loader families or rule
revisions produce inconclusive. Dynamic audit/filter/auxiliary loading and
unmodeled DF_1 flags also retain explicit unknown findings. Only ORIGIN tokens
are currently expanded; LIB, PLATFORM and unknown tokens are inconclusive.
Exceptional search-group behavior after ELOOP/ENOTDIR remains inconclusive.
Static executables and standalone shared-object entry modes are not modeled.

The loader is not fully emulated. Relocations, symbol resolution, GNU symbol
versions, kernel ABI and hardware feature notes, permissions/ACLs, runtime
dlopen, application behavior and upgrade impact are outside this dependency
result. AArch64 libraries in the reference profile are cross-toolchain runtime
files, not evidence that a general AArch64 distribution image has been validated.

Two complete distribution environments, cache selection, the broader planned
test matrix, and U2/U3 remain acceptance work. The earlier glibc 2.39 smoke test
does not make it a supported production profile.

## Results and limits

`pass_static` / exit 0 means the declared checks found no problem; `fail` / 1
contains a proven mismatch; `inconclusive` / 2 contains a coverage gap; and
`input_error` / 3 rejects invalid evidence. Priority is input_error, fail,
inconclusive, pass_static; lower-priority findings remain in the report.

Limits currently include 128 MiB per ELF/blob, 256 MiB unique snapshot content,
4 MiB manifest, 20,000 namespace entries, 4,096 program headers, 65,536 dynamic
entries, 2,048 loaded objects and 16,384 combined dependency/search steps.
Paths have a 1 MiB bound and a resolution budget; reaching an analysis limit
must not produce pass_static. Snapshot size violations are rejected before
analysis. The content callback should also bound reads before allocating data.

The CLI's entry argument uses UTF-8; byte-valued entry paths remain available
through the MoonBit API. Text paths are JSON-quoted to escape control characters.
