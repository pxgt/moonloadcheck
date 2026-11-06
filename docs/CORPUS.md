# Real-program deployment evidence

The corpus checks unmodified distribution executables against two hash-pinned
startup runtimes. It includes successful deployments, an actual version failure,
an actual removed/missing export, and an unaffected consumer. The analyzer never
executes these programs; a separate reference recipe executes trusted inputs and
records expected outcomes before analyzer verification.

## Frozen inputs

| Input | Ubuntu Jammy release | Ubuntu Noble release |
| --- | --- | --- |
| libc6 / loader | 2.35-0ubuntu3 | 2.39-0ubuntu8 |
| GNU hello | 2.10-2ubuntu4 | 2.10-3build1 |
| jq / libjq1 | 1.6-2.1ubuntu3 | 1.7.1-3build1 |
| zstd | 1.4.8+dfsg-3build1 | 1.5.5+dfsg2-2build1 |

Both amd64 and arm64 use official archive packages, with separate package hashes.
The [lock](../tools/corpus/ubuntu.lock.json) includes all 44 package records
(11 packages × 2 releases × 2 architectures), source identities, exact versions,
URLs, sizes and hashes. InRelease signatures were verified using the Ubuntu
archive keyring; each package-index hash was checked against that signed release.
CI uses the checked-in lock and rechecks every .deb hash, without resolving moving
package versions. These historical inputs are for regression testing, not current
deployment recommendations. Noble's liblzma5 is the archive's
5.6.1+really5.4.5-1 source reversion; the exact package is in the lock.

Extraction does not install packages or execute maintainer scripts. Complete
package extractions, including copyright notices, stay under .tools/corpus/roots.
Execution roots contain the programs, loaders and startup libraries needed here;
they omit documentation, locale data, gconv modules and most other OS facilities.
They are **not full distribution images**. No binary corpus is committed or
published. See [provenance](../THIRD_PARTY.md).

## Matrix and observed results

Each row runs on x86-64 and AArch64, giving 24 program/environment cases:

| Executable source → runtime | hello | jq | zstd |
| --- | --- | --- | --- |
| Jammy → Jammy | pass | pass | pass |
| Noble → Noble | pass | pass | pass |
| Jammy → Noble | pass | pass | pass |
| Noble → Jammy | fail: GLIBC_2.38 | fail: GLIBC_2.38; jq_set_stderr_cb | pass |

Executable hashes are unchanged between the two target views for a given source
release. A successful hello run must print the specified greeting; jq must add
[1,2,3] to 6; zstd must compress and decompress a payload without changes. Each
invocation uses the target loader in a chroot, explicit library directories,
disabled cache/hwcaps, LC_ALL=C and LD_BIND_NOW=1. AArch64 uses the pinned static
QEMU helper only while executing; it is removed from the snapshot namespace.

The four failing cases have independent loader errors for GLIBC_2.38. Analysis
also identifies __isoc23_fscanf in hello and __isoc23_strtol in jq. It identifies
jq_set_stderr_cb as absent from Jammy libjq; the loader's first version error can
stop execution before that later lookup. This extra finding is not claimed as a
second separately observed loader error. The downgrade comparison recomputes
three consumers: hello and jq acquire failures, while zstd remains unaffected.

## Hash-order regression and exact loader revision

Eight additional own-source cases cover two architectures, two fixed loaders
and GNU/SysV hashing. They place an unversioned fallback before an exact version
in the hash lookup chain. In the SysV case this deliberately reverses dynsym
index order. Actual execution returns the fallback function's value (7), not the
exact-version function's value (9). Analyzer reports must select that same
unversioned definition. This caught and fixed enumeration by dynsym index.

The Noble profile is ubuntu-noble-2.39-0ubuntu8-v1. Its behavior agrees with the
[original glibc-2.39 lookup implementation](https://github.com/bminor/glibc/blob/glibc-2.39/elf/dl-lookup.c).
A moving release/2.39 maintenance branch has later changes and cannot identify
the behavior of this package. Later 2.39 patch levels are not covered by this
profile. The earlier M0 2.39-0ubuntu8.9 smoke input remains a separate experiment.

## Reproduce and inspect

Follow the [Linux toolchain and reference prerequisites](../tools/oracle/README.md),
including an AArch64 cross compiler, Node and root or passwordless sudo for
project-owned chroots. Then run:

```sh
python3 tools/corpus/build_roots.py
python3 tools/corpus/build_version_fallback.py
python3 tools/corpus/build_copy.py
python3 tools/corpus/build_paths.py
python3 tools/corpus/build_inputs.py
python3 tools/corpus/build_limits.py
python3 tools/corpus/build_linkage_edges.py
python3 tools/corpus/build_parser_edges.py
moon check --target js,native --deny-warn
moon build --target js,native
moon test --target js,native
python3 tools/corpus/verify.py --js _build/js/debug/build/cmd/main/main.js --native _build/native/debug/build/cmd/main/main.exe
python3 tools/corpus/self_host.py --js _build/js/debug/build/cmd/main/main.js --native _build/native/debug/build/cmd/main/main.exe
python3 tools/verify_consumer.py
```

Generated corpus and fallback oracle.json files record actual outcomes and
loader/program hashes. artifacts/corpus contains JSON reports and per-process
wall times, report sizes, object counts and reference counts; these timings are
observations, not portable performance guarantees. The verifier compares native
and JS reports; --compare-dir accepts a saved report directory from another host.

The self-host recipe additionally deploys the just-built MoonBit native/FFI CLI
into both x86-64 runtime roots, verifies its input-error command executes normally
(exit 3). readelf independently confirms COPY relocations for stdout, stderr and
__environ. These previously produced unknown findings; the subsequent
[COPY validation](COPY.md) now checks their separate source/ordinary bindings and
equal sizes, and requires pass_static in both runtime roots.
The standalone consumer uses a temporary Moon workspace outside this checkout
and imports only the public facade. This validates a source dependency, not an
installed Mooncakes release.

Maintainers can reconstruct the lock with python3 tools/corpus/lock_ubuntu.py on
Linux with gpgv and ubuntu-keyring. That operation freezes release-pocket indexes;
it does not update apt sources. Normal tests must use the checked-in lock.

## Remaining acceptance work

The corpus supports controlled startup conclusions. It does not establish
complete application functionality, kernel/CPU compatibility, full distro
support or type/layout ABI compatibility. Additional COPY and GNU_UNIQUE/protected/SYMBOLIC
combinations remain outside the validated model. Later increments add finite
[malformed/resource and special-binding evidence](MATURITY_BOUNDARIES.md), but
do not establish a universal worst-case performance bound. The current
[acceptance map](ACCEPTANCE_STATUS.md) tracks the remaining release-stage row.
AArch64 self-hosting
of the MoonBit CLI has not been validated. No Mooncakes release or registration
is implied by these tests.
