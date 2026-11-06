# Binding, GLIBCXX and resource-boundary evidence

This increment adds 44 real loader observations and 68 non-executed parser
inputs. It fixes two demonstrated gaps: skipping a wrong-type TLS provider,
and accepting an overflowing PT_LOAD virtual memory range. It does not expand
the supported profiles to arbitrary GNU_UNIQUE, protected binding or full C++ ABI.

## Special bindings and TLS

`tools/corpus/build_bindings.py` builds our C fixtures in both pinned runtime
versions on x86-64 and AArch64. It records commands, object/loader hashes,
readelf metadata, program exits and focused loader binding traces.

| Case | Actual program result | Required static result |
| --- | --- | --- |
| Ordinary first-definition interposition | Reads first provider's distinct value | pass_static with that provider |
| Ordinary TLS provider | Reads expected thread-local value | pass_static for symbol availability; TLS layout remains outside scope |
| Missing TLS definition | Undefined-symbol failure | fail with no provider |
| Protected definition | Runs successfully | inconclusive for the unvalidated binding |
| SYMBOLIC self binding | Reads the DSO's own value despite an earlier provider | inconclusive |
| GNU_UNIQUE data definition | Runs successfully | inconclusive |
| TLS reference, ordinary first definition, valid TLS definition later | Binds first definition, then faults | inconclusive with the actual first provider retained |
| Ordinary data reference, TLS definition | Reads the wrong application value | inconclusive with the selected provider retained |

The last two cases deliberately replace a library after successful linking.
They are inconsistent type combinations in our own fixtures, with core dumps
disabled and execution time bounded. The GNU_UNIQUE case changes an ordinary
data definition to STB_GNU_UNIQUE and the GNU OS ABI identifier; readelf verifies
that metadata. These are controlled experiments, not claims about normal
compiler output or every combination of visibility, versioning and TLS models.

For the first TLS collision, the previous analyzer skipped the ordinary
definition and reported pass_static using the later TLS provider. Real loader
binding traces selected the first provider on all four contexts. Lookup now
retains name/version order. A mismatch between relocation class and requested
or selected symbol type, or mixed TLS/ordinary references, retains unknown.
It cannot manufacture a successful lookup by skipping the mismatched provider.
Known missing TLS definitions still fail; supported TLS availability still passes.

The independent reference is glibc's
[name/version matching](https://github.com/bminor/glibc/blob/glibc-2.35/elf/dl-lookup.c).
Actual runtime behavior, TLS allocation/offset arithmetic and application
correctness remain outside static symbol availability checks.

## Real C++ runtime versions

`tools/corpus/build_glibcxx.py` uses libstdc++ already frozen in the signed
[Ubuntu package lock](../tools/corpus/ubuntu.lock.json). The loader, libc, libm
and libgcc remain Noble in every view. Only libstdc++.so.6 changes. Both ABI
probes retain identical bytes across these views, on both architectures:

- `stable` calls real operator new/delete exports requiring the old GLIBCXX
  interface. It executes successfully with both runtime versions.
- `modern` additionally calls the real `std::ios_base_library_init()` export
  requiring GLIBCXX_3.4.32. It executes with Noble, then fails with that exact
  missing version when only libstdc++ is replaced by Jammy's library.
- A controlled copy of Noble's provider retains GLIBCXX_3.4.33 but redirects the
  3.4.32 version-definition label and parent labels to another existing string,
  updating the definition hash. Dynamic symbol names and their GNU hashes stay
  unchanged. The modern probe fails; the stable probe still runs. Even the old
  name string remains present in dynsym, so neither a highest-version comparison
  nor searching raw strings can substitute for reading actual version nodes.

These small C fixtures call explicit C++ ABI symbols, avoiding a dependency on
the analysis host's C++ headers. They are ABI probes, not general C++ application
benchmarks. The initialization interface is documented in the GCC
[runtime implementation](https://github.com/gcc-mirror/gcc/blob/releases/gcc-13.2.0/libstdc%2B%2B-v3/src/c%2B%2B98/ios_init.cc);
the [GCC ABI manual](https://gcc.gnu.org/onlinedocs/libstdc%2B%2B/manual/abi.html)
explains symbol-version requirements. No GCC implementation source is copied.

There are 12 actual outcomes. The analyzer finds the precise missing
GLIBCXX_3.4.32 node and reports fail for both negative modern probes. Successful
executions still have an overall inconclusive static result because the real
libstdc++ contains unvalidated bindings. Those findings are retained; this
experiment does not convert a successful invocation into a complete ABI proof.

## Range and allocation boundaries

`tools/corpus/build_stress.py` generates 34 inputs per architecture, all marked
`executed: false`. They are never sent to a target loader. Cases include:

- Large file offsets, table addresses and sizes around signed-32-bit and
  unsigned-64-bit boundaries; invalid string/symbol indices and auxiliary links.
- A PT_LOAD with zero file size and a virtual memory range that wraps UInt64.
  The old parser admitted it. It now returns Malformed before mapping lookup.
  A non-overflowing arithmetic control is accepted; this is not evidence that
  the kernel could map that address or execute that artificial input.
- Actual 4,096/4,097 program-header, 65,536/65,537 dynamic-entry and
  500,000/500,001 relocation boundaries. The allowed sizes parse; excess counts
  return ResourceLimit. Production caps are not lowered for the tests.
- Oversized SysV symbol/version counts that stop before corresponding allocation.

The large relocation tables contain NONE records and are metadata-only
controls. The largest fixture is about 12 MB. API tests distinguish Malformed
from ResourceLimit; CLI tests retain MLC006/input_error versus MLC009/unknown.

On Linux, the verifier measures four selected cases on each architecture and
backend, including both sides of the 500,000-relocation boundary. Every measured
process has a 60-second timeout and a checked 512-MiB peak-RSS ceiling. Measurements
are written to `artifacts/stress-performance.json`. These finite regression
observations do not prove a worst-case bound for all inputs or exercise every
configured size ceiling. Existing per-name/aggregate string budgets and the
real dependency-step exhaustion case remain separate checks.

## Reproduction

After the standard bootstrap and earlier fixture builders:

```sh
python3 tools/corpus/build_glibcxx.py
python3 tools/corpus/build_bindings.py
python3 tools/corpus/build_stress.py
moon test --target js,native
python3 tools/corpus/verify_maturity.py --js _build/js/debug/build/cmd/main/main.js --native _build/native/debug/build/cmd/main/main.exe --measure
```

The verifier runs 112 CLI checks per backend, compares exact reports, and accepts
`--compare-dir` for cross-host comparison. With both backends, it records 16
additional stress measurements. CI rebuilds all source/package-derived inputs.
