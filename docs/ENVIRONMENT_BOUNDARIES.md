# Environment facts and search-path evidence

These checks use the existing pinned Jammy 2.35/Noble 2.39 profiles on x86-64
and AArch64. They do not add a loader family or implement conditional cache
selection. AArch64 programs run under the pinned QEMU helper. The analyzer
never executes a target program.

## Independent observations

`tools/corpus/build_environment_edges.py` records 78 actual program outcomes,
their commands, input/loader hashes, compiler versions, measured LIB/PLATFORM
values and separate loader listings. Every root is project-owned and isolated
with chroot. There is no host library fallback or linker-cache modification.

| Matrix | Executions | Evidence |
| --- | ---: | --- |
| Eight plain/braced combinations of ORIGIN, LIB and PLATFORM | 32 | The target loader measures both optional tokens; its selected path and successful program result agree with analysis |
| DSO RUNPATH, ancestor RPATH, main environment ORIGIN | 12 | Correct and wrong-origin libraries return different values; the declaring object's context wins |
| Empty RUNPATH versus colon-separated empty components | 8 | Empty entire RUNPATH is disabled; `:` searches cwd and finds the library |
| Literal semicolon in RPATH/RUNPATH, present and missing | 16 | Literal directory is selected; removing it fails even with a usable library before the semicolon |
| Conditional and irrelevant cache records, Jammy only | 10 | Actual accepted/skipped conditions and conservative static uncertainty are recorded separately |

The semicolon cases reproduced a false pass in the previous analyzer: with
`RPATH=/good;/decoy`, it searched `/good` and `/decoy` separately. The loader
instead searches the literal directory `/good;/decoy`. The corrected analyzer
retains the semicolon and reports failure when that directory's provider is
missing. Both RPATH and RUNPATH have positive and negative cases in all four
runtime/architecture contexts.

ORIGIN evidence distinguishes a DSO's own RUNPATH from the main executable's
directory, expands inherited RPATH relative to the ancestor declaring it, and
expands environment library paths relative to the main executable even while
resolving a DSO dependency. Earlier load-path/symlink cases remain separate.

## Cache conditions

The controlled cache 1.1 files have duplicate-name records in explicit order.
They are generated test inputs, not claims about every ldconfig output. The
real pinned loaders consume them, select a provider visible in `--list`, and
call a function with a distinguishable value. No machine-dependent result is
inferred from the analysis host.

| First matching record | Actual Jammy loader | Static result |
| --- | --- | --- |
| Legacy TLS hwcap bit 63 | Chooses preferred provider | inconclusive; matching conditional record has no modeled condition facts |
| OS version 1 | Chooses preferred provider | inconclusive |
| OS version `0xffffffff` | Skips to fallback provider | inconclusive; no guessed fallback |
| Foreign architecture plus conditional flag | Ignores it, chooses ordinary fallback | pass_static with fallback path |
| Ordinary exact-architecture record before a conditional record | Chooses first ordinary provider | pass_static with that path |

The fallback returns 9 when the application expects 7, so those executions exit
1 even when static linkage passes. Function behavior is outside compatibility
checks. An eligible conditional record leaves the dependency unselected with
`cache_unknown` and MLC007; a later ordinary provider does not erase uncertainty.
Noble cache support remains excluded.

## Empty versus missing facts

`tools/corpus/build_profile_facts.py` generates 50 declared-fact variants from
one captured root. **These variants are not actual loader executions.** They
test schema admission and explicit modeling contracts without inventing target
measurements. The two real measured token values above remain nonempty.

| Fields | Known empty/default form | Missing or JSON null |
| --- | --- | --- |
| `default_dirs_hex`, `library_path_hex` | `[]` means no directories in that source | input_error; unknown lists cannot be silently defaulted |
| `preload`, `audit` | `[]` means known inactive | input_error |
| `secure_execution` | `false` means known inactive | input_error |
| `rule_revision`, `loader_family`, `cache_mode`, `hwcaps_policy` | Empty string is an unsupported explicit mode, inconclusive | input_error |
| `machine`, `loader_path_hex`, `loader_sha256`, `cwd_hex` | Zero/empty identity is invalid, input_error | input_error |
| `lib_token_hex`, `platform_token_hex` | `""` is invalid; supported profiles require nonempty measured substitutions | Omitted is unknown; null is invalid |

An omitted token does not obstruct a check that never uses it. Using it retains
inconclusive. An originally empty library-path component means cwd. Empty
token values remain input errors whether used or unused; they cannot create
a cwd search or be confused with unknown facts. Tests cover both tokens.
All 50 variants run through both the public snapshot API and the CLI.

Schema 1 represents required facts explicitly. If a caller does not know one
of them, it cannot submit a valid complete profile by omitting it. This is
intentional rejection of incomplete evidence, not evidence of an empty target.

## Reproduction and sources

After the standard pinned-root bootstrap:

```sh
python3 tools/corpus/build_environment_edges.py
python3 tools/corpus/build_profile_facts.py
moon test --target js,native
python3 tools/corpus/verify_environment_edges.py --js _build/js/debug/build/cmd/main/main.js --native _build/native/debug/build/cmd/main/main.exe
```

The verifier checks 128 reports per backend, including selected paths and
conditional-cache traces. It can compare exact reports across hosts with
`--compare-dir`. The CI workflow rebuilds every reference input from source.

Reference behavior is specified in glibc's
[path decomposition and token expansion](https://github.com/bminor/glibc/blob/glibc-2.35/elf/dl-load.c)
(`decompose_rpath`, `fillin_rpath`, `_dl_init_paths`) and
[cache search](https://github.com/bminor/glibc/blob/glibc-2.35/elf/dl-cache.c)
(`search_cache`). RPATH/RUNPATH split on colon; the raw environment path splits
on colon or semicolon. Snapshot `library_path_hex` is already a list of
components. No glibc implementation source is copied into the project.
