# Internal acceptance evidence map

This maps the 73 project quality cases from the planning workspace. It is not an
official contest checklist. **Covered** means the listed scenario has repeatable
evidence under the declared profile, not universal loader support. **Partial**
means a named portion still lacks a focused check. **Open** has no sufficient
record yet. Results are reproduced by the CI workflow; limits remain in
[SUPPORTED_PROFILE.md](SUPPORTED_PROFILE.md).

| ID | Status | Current evidence and remaining work |
| --- | --- | --- |
| E01 | Partial | [Runtime reader][runtime], [COPY][copy] exercise PIE/ET_EXEC/DSO; comprehensive readelf field-by-field assertions remain. |
| E02 | Covered | [Linkage reader][reader], runtime and actual loader fixtures on x86-64/AArch64. |
| E03 | Covered | Runtime/linkage readers compare ordinary and stripped fixtures. |
| E04 | Covered | Runtime/linkage readers use sectionless fixtures on both architectures. |
| E05 | Partial | [Symbol][symbols] and [hash-order][fallback] cases cover GNU/SysV/both; explicit final-entry boundary cases need expansion. |
| E06 | Partial | [Malformed metadata][malformed] and truncated objects; more separate table truncation positions remain. |
| E07 | Partial | Bad version offsets/symbol indices and [budgets][budgets]; exhaustive range/overflow and allocation stress remain. |
| E08 | Partial | Invalid chains are rejected; explicit cyclic-chain and unterminated-name cases remain. |
| E09 | Partial | [Path bytes][paths] are tested; non-UTF-8 dynamic symbol names need a dedicated fixture. |
| E10 | Open | Reader rejects unsupported classes/types; a complete ET_REL/ELF32/big-endian/non-ELF test table remains. |
| E11 | Partial | [U2][linkage] uses actual references and used/unused exports; isolated unreferenced undefined dynsym entry remains. |
| E12 | Partial | Real corpus exercises relative relocations; targeted unknown and symbol-free relocation mutations remain. |
| P01 | Covered | CLI verifiers compare exact saved reports across Windows JS/Linux native. |
| P02 | Covered | [Path tests][paths] and Linux path oracle cover target-root links. |
| P03 | Covered | Broken links, cycles and hop limits in path tests. |
| P04 | Covered | Link expansion before dotdot, with Linux oracle. |
| P05 | Covered | Case distinctions and raw non-UTF-8 path bytes in path tests. |
| P06 | Partial | [Manifest tests][manifest] reject tampering; add a dedicated missing-blob CLI case. |
| P07 | Partial | Manifest tests separate equal content/hardlink identities; more runtime alias/reuse combinations remain. |
| P08 | Partial | Snapshot-only reads and chroot corpus; deliberate host-library fallback fault injection remains. |
| P09 | Partial | [Dependency][dependencies]/token tests distinguish unsupported/absent facts; full empty-versus-unknown field table remains. |
| P10 | Partial | Declared cwd and relative paths in path tests; explicit empty search elements in real loader tests remain. |
| R01 | Covered | U1 dependency closure, parent edges and real execution. |
| R02 | Partial | U1 diagnoses indirect missing library with chain; expand direct-versus-indirect missing cases. |
| R03 | Covered | Missing interpreter and wrong-machine dependency tests. |
| R04 | Open | Dedicated slash-containing DT_NEEDED fixture remains. |
| R05 | Covered | U1 inherited RPATH versus direct-only RUNPATH, both fixes. |
| R06 | Partial | Search order implemented; competing RPATH/environment/RUNPATH provider matrix remains. |
| R07 | Partial | DSO load-path/symlink ORIGIN tested; more main-versus-DSO competition cases remain. |
| R08 | Partial | [Tokens][tokens] measure LIB/PLATFORM and missing facts; all braced spellings need explicit cases. |
| R09 | Covered | [Cache tests][cache] verify candidate order, disabled cache and stale first match. |
| R10 | Covered | NODEFLIB cache/default filtering compared with both architecture loaders. |
| R11 | Partial | Foreign architecture, directory and PIE candidates compared; corrupt candidate loader behavior needs dedicated evidence. |
| R12 | Partial | Alias/SONAME reuse is implemented; adversarial duplicate SONAME order cases remain. |
| R13 | Open | Dedicated dependency cycle/diamond graph with loader comparison remains. |
| R14 | Partial | Conditional cache records retain unknown; more real hwcap/OS-condition cases remain. |
| R15 | Partial | Profile guard covers preload/audit/secure execution; explicit test for each excluded mode remains. |
| S01 | Covered | U2 referenced strong exports, absent definitions, offsets and scope. |
| S02 | Covered | Weak-reference U2 cases and weak-missing COPY execution. |
| S03 | Covered | Missing version nodes and wrong-version exports, including COPY. |
| S04 | Covered | Reader verifies equal local indices with different names; U2 rejects mismatch. |
| S05 | Partial | Name/hash matching implemented and real cross-runtime cases exercised; forced unequal-index/same-name case remains. |
| S06 | Covered | Symbol fixtures exercise oldest/default/explicit nondefault versions. |
| S07 | Covered | U2 detached symbol reference still checks the declared version node. |
| S08 | Covered | Weak version-node and weak symbol fixtures treated separately. |
| S09 | Partial | Hidden provider tested; isolated LOCAL/INTERNAL definitions need explicit assertions. |
| S10 | Covered | Weak/strong order, main interposition and COPY/ordinary provider separation. |
| S11 | Covered | Eight hash-order/version fallback executions against the exact locked loaders. |
| S12 | Partial | 38 COPY executions plus two GOT controls; GNU_UNIQUE, broader protected/SYMBOLIC/TLS combinations remain unknown. |
| S13 | Partial | Real libc IFUNC references parsed; dedicated IFUNC existence/behavior boundary fixture remains. |
| S14 | Partial | Lazy phase is reported and references checked; explicit deferred failure/call timing fixture remains. |
| S15 | Partial | Actual GLIBC_2.38 mismatch in hello/jq; focused GLIBCXX missing-version case remains. |
| D01 | Covered | [Impact tests][impact] identify removed used export. |
| D02 | Covered | Stable U3 consumer passes after removal of an unused export. |
| D03 | Covered | [Corpus downgrade][corpus] reports newly introduced version requirements with unchanged applications. |
| D04 | Open | Dedicated before/after path/cache provider change case remains. |
| D05 | Covered | Impact tests classify unchanged failure as existing. |
| D06 | Partial | Unknown-before/fail-after retains indeterminate; add explicit unknown-to-pass case. |
| D07 | Covered | Reverse U3 comparison records resolved failure. |
| D08 | Covered | U3 two-consumer and real three-consumer downgrade examples. |
| D09 | Covered | Application-change digest and indeterminate baseline tests. |
| C01 | Open | Explicit shuffled namespace enumeration/report equivalence remains. |
| C02 | Covered | Repeated exact reports in U1 tests and process resource baseline. |
| C03 | Covered | CLI verifier exercises all four exit categories. |
| C04 | Covered | CLI reports parsed through pipes, including >64 KiB output regression. |
| C05 | Covered | Multi-consumer U3 and real downgrade preserve unaffected consumers. |
| C06 | Covered | Offline explain, unsupported schema, old additive-field compatibility and duplicate-ID rejection. |
| C07 | Partial | Parser name/count budgets and [report merge contract][reports]; end-to-end exhaustion after an earlier failure remains. |
| C08 | Partial | Complete before/after recomputation and manifest identity tests; explicit changed-rule cache sequence remains. |
| C09 | Open | Standalone local-source consumer passes; published Mooncakes version validation awaits release. |
| C10 | Covered | JS/native suites plus exact Windows/Linux snapshot report comparison. |
| C11 | Partial | Clean CI reconstructs recipes; separate human-facing README walkthrough remains. |
| C12 | Partial | Two wrong COPY rules are detected by assertion failures; the five originally planned fault classes remain. |

Priorities after this increment: finish the named input/path/graph gaps, exercise
the five C12 fault classes, then run end-to-end limit stress and review API/report
freeze. C09 belongs to the authorized release stage and cannot be replaced by a
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
