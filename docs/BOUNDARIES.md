# Path, input and resource boundary evidence

This increment turns specific open acceptance rows into reproducible cases. It
does not broaden the controlled loader profiles or claim general Linux support.

## Independent path/graph executions

tools/corpus/build_paths.py builds our graph_app.c and graph_library.c against
the locked Jammy and Noble runtimes on both architectures. Fourteen cases in
each context give **56 actual executions**:

| Cases | Observed behavior and analyzer requirement |
| --- | --- |
| Absolute/relative slash-containing DT_NEEDED | Resolve the named target path directly, without a directory search |
| Empty library-path element | Select the library in the declared cwd |
| RPATH versus library path | Old-style executable RPATH wins in this tested arrangement |
| RUNPATH versus library path | Library path wins over executable RUNPATH |
| Direct missing dependency | Loader rejects; report identifies the failed direct edge |
| Cycle | Maps each object once, terminates and retains the back edge |
| Diamond | Two parents share one mapped leaf |
| Two hardlinked paths | One mapping and one constructor invocation |
| Two independent files with equal bytes/SONAME | Two mappings and two constructor invocations |
| Short corrupt first candidate | Loader stops; analyzer reports invalid evidence and does not try a later usable candidate |
| Good/bad provider selected by path order | Same application and export name, different required version availability; diff detects introduced failures |
| Host-only usable library | Exists in .tools/corpus/host-decoys, outside the captured root; isolated execution and analysis still report missing target dependency |

AArch64 uses the pinned QEMU helper. Host decoys persist in the ignored workspace
rather than temporary OS storage so independent later mutation runs can verify
that the host file really exists. No host system library directory is modified.
Oracle records contain compiler versions, build/run commands, controlled
environment, loader/program hashes and actual diagnostics. Hardlink fixtures
are rebuilt in a checked project-owned directory to avoid state from prior runs.

## Unsupported and malformed ELF inputs

tools/corpus/build_inputs.py produces real relocatable ELF64, ELF32 and big-endian
objects, checks their headers using readelf, and never executes them. They must
return Unsupported, while non-ELF bytes and truncated headers return Malformed.
Additional byte mutations cover missing dynamic-table termination, a truncated
dynamic string table, unterminated names, non-advancing version chains and
unmapped version-table addresses on both architectures. These are targeted
negative tests, not an exhaustive parser fuzzing result.

## Production resource limit

tools/corpus/build_limits.py creates a sectionless own-source ELF with an appended
file-backed PT_DYNAMIC and 17,001 DT_NEEDED entries. readelf independently counts
the entries. The first dependency is missing; subsequent entries repeatedly
reuse libc. The file is only a few hundred KiB and is **never executed**.

Analysis reaches the unchanged production limit of 16,384 dependency/search
steps. The report must retain the earlier MLC002 failure and add an MLC009 unknown
coverage diagnostic, with final fail status/exit 1. Both backends parse the whole
large piped JSON report and produce matching evidence. No test-only lower limit
is substituted. Other allocator and input-limit extremes remain future stress
work.

## Five planned wrong-rule experiments

tools/verify_acceptance_mutations.py first runs seven acceptance tests unchanged
in a disposable source copy, then introduces each fault separately:

1. Inherit RUNPATH into indirect dependencies.
2. Ignore GNU version-node checks and requested symbol versions.
3. Read an absent target library from the real analysis host filesystem.
4. Turn unknown into pass_static.
5. Treat removal from the flat export set as breakage for every consumer, including one that never uses it.

Each fault must fail its dedicated assertion. A compiler error, absent host decoy,
missing fixture or failing unmodified control is a harness failure, not a
detected semantic fault. The real source checkout remains unmodified. The host
fallback import and implementation exist only inside the disposable mutant.
The two earlier COPY mutations remain separate regression checks.

Additional contracts cover reversed namespace enumeration (semantic reports
match, while the raw manifest digest changes), unknown-to-pass comparison,
excluded loader modes, changed-rule analysis followed by the original snapshot,
and missing blob files. Blob callback errors are wrapped as InvalidSnapshot with
the validated digest, yielding stable CLI evidence across hosts. Callback
exceptions are no longer propagated verbatim; content hash and size checks still
run after successful reads.

## Reproduce

After the existing reference/corpus setup:

```sh
python3 tools/corpus/build_paths.py
python3 tools/corpus/build_inputs.py
python3 tools/corpus/build_limits.py
moon build --target js,native
moon test --target js,native
python3 tools/corpus/verify_paths.py --js _build/js/debug/build/cmd/main/main.js --native _build/native/debug/build/cmd/main/main.exe
python3 tools/verify_acceptance_mutations.py
```

The verifier runs the 56 path/graph cases plus one resource-limit case on each
backend. --compare-dir accepts saved reports from another host. See the
[73-case evidence map](ACCEPTANCE_STATUS.md) for the remaining parser, symbol,
special-binding, stress and release requirements.
