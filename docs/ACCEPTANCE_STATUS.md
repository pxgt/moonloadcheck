# Internal acceptance evidence map

This maps the 73 project quality cases from the planning workspace. It is not an
official contest checklist. **Covered** means the listed scenario has repeatable
evidence under the declared profile, not universal loader support. **Partial**
means a named portion still lacks a focused check. **Open** has no sufficient
record yet. Results are reproduced by the CI workflow; limits remain in
[SUPPORTED_PROFILE.md](SUPPORTED_PROFILE.md).

| ID | Status | Current evidence and remaining work |
| --- | --- | --- |
| E01 | Covered | [Readelf comparisons][readelf] check all exposed runtime object fields across 120 PIE/ET_EXEC/DSO inputs. |
| E02 | Covered | [Linkage reader][reader], runtime and actual loader fixtures on x86-64/AArch64. |
| E03 | Covered | Runtime/linkage readers compare ordinary and stripped fixtures. |
| E04 | Covered | Runtime/linkage readers use sectionless fixtures on both architectures. |
| E05 | Covered | GNU/SysV/both fixtures plus exact mapped table ends, final-symbol assertions, truncated final words and a missing GNU terminator. |
| E06 | Covered | Dynamic/string truncation and [exact table ends][readelf] reject incomplete Verneed/Verdef/Versym records. Errors identify the relevant virtual address, file offset or string-table offset. |
| E07 | Partial | Bad version offsets/symbol indices and [budgets][budgets]; exhaustive range/overflow and allocation stress remain. |
| E08 | Covered | Input boundaries reject unterminated names and non-advancing/self-loop version chains on both architectures. |
| E09 | Covered | [Raw symbol fixtures][edgecases] distinguish two byte names with identical lossy displays; loader outcome, lookup hex and saved reports agree. Path bytes remain separately tested. |
| E10 | Covered | Readelf-verified ET_REL/ELF32/big-endian objects return Unsupported; non-ELF/truncated headers return Malformed. |
| E11 | Covered | An isolated strong undefined dynsym without active relocations executes successfully and creates no symbol requirement. |
| E12 | Covered | Unknown symbol-bearing and symbol-free types retain MLC008/unknown; NONE/RELATIVE do not generate external lookups. Metadata mutants are never executed. |
| P01 | Covered | CLI verifiers compare exact saved reports across Windows JS/Linux native. |
| P02 | Covered | [Path tests][paths] and Linux path oracle cover target-root links. |
| P03 | Covered | Broken links, cycles and hop limits in path tests. |
| P04 | Covered | Link expansion before dotdot, with Linux oracle. |
| P05 | Covered | Case distinctions and raw non-UTF-8 path bytes in path tests. |
| P06 | Covered | Manifest tests reject tampering; missing-blob CLI case and callback-error digest diagnostics are checked across hosts. |
| P07 | Covered | [Graph cases][pathgraph] distinguish equal-byte files from hardlinked aliases using actual constructor counts. |
| P08 | Covered | Real host-only decoy cannot repair the captured target; deliberate host-fallback mutation is caught. |
| P09 | Partial | [Dependency][dependencies]/token tests distinguish unsupported/absent facts; full empty-versus-unknown field table remains. |
| P10 | Covered | Declared cwd/relative paths in unit tests; real empty library-path element selects cwd library. |
| R01 | Covered | U1 dependency closure, parent edges and real execution. |
| R02 | Covered | U1 indirect missing-library chain plus direct-missing path/graph execution and edge checks. |
| R03 | Covered | Missing interpreter and wrong-machine dependency tests. |
| R04 | Covered | Absolute and relative slash-containing DT_NEEDED bypass directory search in both fixed environments. |
| R05 | Covered | U1 inherited RPATH versus direct-only RUNPATH, both fixes. |
| R06 | Covered | Competing RPATH/library-path/RUNPATH providers return distinguishable values; selected paths match. |
| R07 | Partial | DSO load-path/symlink ORIGIN tested; more main-versus-DSO competition cases remain. |
| R08 | Partial | [Tokens][tokens] measure LIB/PLATFORM and missing facts; all braced spellings need explicit cases. |
| R09 | Covered | [Cache tests][cache] verify candidate order, disabled cache and stale first match. |
| R10 | Covered | NODEFLIB cache/default filtering compared with both architecture loaders. |
| R11 | Covered | Foreign architecture, directory/PIE and short corrupt first candidates compared; corrupt evidence stops search. |
| R12 | Covered | Different path aliases with identical bytes/SONAME map separately unless file identity is shared; constructor counts verify it. |
| R13 | Covered | Cycle retains its back edge and terminates; diamond maps its leaf once, both checked against actual execution. |
| R14 | Partial | Conditional cache records retain unknown; more real hwcap/OS-condition cases remain. |
| R15 | Covered | [Acceptance contracts][contracts] check secure, preload, audit, hwcaps, loader-family and rule-revision exclusions. |
| S01 | Covered | U2 referenced strong exports, absent definitions, offsets and scope. |
| S02 | Covered | Weak-reference U2 cases and weak-missing COPY execution. |
| S03 | Covered | Missing version nodes and wrong-version exports, including COPY. |
| S04 | Covered | Reader verifies equal local indices with different names; U2 rejects mismatch. |
| S05 | Covered | Same EDGE_1 name/hash with provider index forced to 17 and a different consumer-local index passes all four loader contexts. |
| S06 | Covered | Symbol fixtures exercise oldest/default/explicit nondefault versions. |
| S07 | Covered | U2 detached symbol reference still checks the declared version node. |
| S08 | Covered | Weak version-node and weak symbol fixtures treated separately. |
| S09 | Covered | LOCAL/INTERNAL/HIDDEN first candidates remain hash-visible but cannot satisfy the external reference; the selected second provider returns its distinct value. |
| S10 | Covered | Weak/strong order, main interposition and COPY/ordinary provider separation. |
| S11 | Covered | Eight hash-order/version fallback executions against the exact locked loaders. |
| S12 | Partial | 38 COPY executions plus two GOT controls; GNU_UNIQUE, broader protected/SYMBOLIC/TLS combinations remain unknown. |
| S13 | Covered | Dedicated IFUNC definitions pass existence checks with both correct and wrong application results; resolver behavior remains outside the result. |
| S14 | Covered | One unchanged lazy executable passes without calling, fails on first call or LD_BIND_NOW; static failure retains startup-or-first-call phase. |
| S15 | Partial | Actual GLIBC_2.38 mismatch in hello/jq; focused GLIBCXX missing-version case remains. |
| D01 | Covered | [Impact tests][impact] identify removed used export. |
| D02 | Covered | Stable U3 consumer passes after removal of an unused export. |
| D03 | Covered | [Corpus downgrade][corpus] reports newly introduced version requirements with unchanged applications. |
| D04 | Covered | Only search-order changes select a different versioned provider; unchanged application acquires explained failures. |
| D05 | Covered | Impact tests classify unchanged failure as existing. |
| D06 | Covered | Both unknown-to-fail and unknown-to-pass retain indeterminate attribution. |
| D07 | Covered | Reverse U3 comparison records resolved failure. |
| D08 | Covered | U3 two-consumer and real three-consumer downgrade examples. |
| D09 | Covered | Application-change digest and indeterminate baseline tests. |
| C01 | Covered | Reversed namespace order yields identical semantic reports; only exact raw manifest digest changes. |
| C02 | Covered | Repeated exact reports in U1 tests and process resource baseline. |
| C03 | Covered | CLI verifier exercises all four exit categories. |
| C04 | Covered | CLI reports parsed through pipes, including >64 KiB output regression. |
| C05 | Covered | Multi-consumer U3 and real downgrade preserve unaffected consumers. |
| C06 | Covered | Offline explain, unsupported schema, old additive-field compatibility and duplicate-ID rejection. |
| C07 | Covered | Parser budgets plus [real 16,384-step exhaustion][limits] retain earlier failure and explicit unknown; large CLI JSON stays complete. |
| C08 | Covered | Repeated original/changed-rule/original snapshot checks retain stable results; full comparisons recompute both views. |
| C09 | Open | Standalone local-source consumer passes; published Mooncakes version validation awaits release. |
| C10 | Covered | JS/native suites plus exact Windows/Linux snapshot report comparison. |
| C11 | Partial | Clean CI reconstructs recipes; separate human-facing README walkthrough remains. |
| C12 | Covered | All five planned faults trigger dedicated assertions after a passing control; two COPY faults remain separately checked. |

Priorities after this increment: expand malformed-input/resource stress, profile
field and token/path/cache cases, special bindings and a focused GLIBCXX case;
review API/report freeze and the user walkthrough. C09 belongs to the authorized release stage and cannot be replaced by a
source-workspace test. Completion of this map is not completion of all its rows.

[runtime]: ../internal/elf_adapter/runtime_test.mbt
[reader]: ../internal/elf_adapter/linkage_test.mbt
[malformed]: ../internal/elf_adapter/linkage_wbtest.mbt
[budgets]: ../internal/elf_adapter/budget_wbtest.mbt
[paths]: ../snapshot/path_test.mbt
[manifest]: ../snapshot/manifest_test.mbt
[dependencies]: ../analysis/dependencies_test.mbt
[tokens]: ../analysis/tokens_test.mbt
[cache]: ../analysis/cache_test.mbt
[symbols]: ../analysis/symbols_test.mbt
[fallback]: ../analysis/fallback_test.mbt
[linkage]: ../analysis/linkage_test.mbt
[impact]: ../analysis/impact_test.mbt
[corpus]: ../analysis/corpus_test.mbt
[copy]: ../analysis/copy_test.mbt
[reports]: ../analysis/report_wbtest.mbt
[inputs]: ../internal/elf_adapter/input_wbtest.mbt
[pathgraph]: ../analysis/paths_test.mbt
[contracts]: ../analysis/acceptance_test.mbt
[limits]: ../analysis/limits_test.mbt
[readelf]: ../internal/elf_adapter/readelf_test.mbt
[edgecases]: ../analysis/linkage_edges_test.mbt
