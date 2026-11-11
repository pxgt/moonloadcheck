# Dependencies and references

| Project | Use | License/source |
| --- | --- | --- |
| moonbit-community/elf 0.0.1 | Internal parser dependency; source preserved, package configuration adapted | [Apache-2.0 source](https://github.com/moonbit-community/elf.mbt), [locked provenance](internal/elf_vendor/UPSTREAM.json) |
| GNU glibc and binutils | Loader behavior and independent test tools | [glibc manual](https://sourceware.org/glibc/manual/latest/html_node/Dynamic-Linker.html), [readelf manual](https://sourceware.org/binutils/docs/binutils/readelf.html) |
| GCC libstdc++ | Locked runtime binaries for version probes; ABI/entry-point reference | [ABI manual](https://gcc.gnu.org/onlinedocs/libstdc%2B%2B/manual/abi.html); package-supplied copyright and license notices are authoritative |
| Gentoo lddtree | Related dependency-analysis tool | [source](https://github.com/gentoo/pax-utils/blob/master/lddtree.py) |
| PyPA auditwheel | Related distribution compatibility tool | [source](https://github.com/pypa/auditwheel) |
| libabigail | Related ABI compatibility tool | [manual](https://sourceware.org/libabigail/manual/abicompat.html) |

The 17 parser source files in `internal/elf_vendor` are copied verbatim from the hash-verified Mooncakes archive, with its LICENSE. They are third-party work, excluded from original-contribution counts. No source from the other reference tools has been copied. New runtime-table adapters and all project analysis code are maintained outside the vendor directory.

## Real-program test inputs

The [Ubuntu corpus lock](tools/corpus/ubuntu.lock.json) records official archive URLs, source-package names, exact versions, sizes and SHA-256 digests for hello, jq, zstd and their runtime libraries. The lock was derived from signed InRelease files and hash-verified package indexes. The [corpus documentation](docs/CORPUS.md) describes the package and runtime boundaries. These are historical regression inputs, not recommended deployment versions.

Downloaded .deb archives, extracted binaries, generated snapshots and Ubuntu copyright files remain in ignored local directories. The repository distributes recipes and metadata, not these binaries. Full extractions preserve the packages' supplied copyright files and documentation symlinks; some runtime packages refer to documentation in other packages, so this subset is not a complete redistribution bundle. Reduced execution roots omit documentation. The supplied notices identify GPLv3+ for GNU hello, MIT for jq, BSD-3-Clause/GPLv2 alternatives for zstd, and LGPL for most glibc files. Package copyright files are authoritative for each included file. Repackaging these roots requires a separate review of notices and corresponding-source obligations; the current workflow does not redistribute them.

The GLIBCXX negative control edits version-definition metadata in a local copy
of a locked libstdc++ binary. That modified binary is also ignored and is never
published by this workflow. The C ABI probes, metadata-editing recipes and
analysis implementation are original project code; no GCC source is copied.

## Independent application integration example

`examples/sensor_report` is original Apache-2.0 MoonBit and C source, including
its two ELF version maps. It has its own module and license, imports only
MoonBit core packages and does not import MoonLoadCheck. It is an example, not
an external adopter. `SENSOR_1.0`/`SENSOR_2.0` are our example library's versions.

The integration verifier builds a separate temporary copy and stages its
generated binaries with the existing locked Ubuntu runtime files. All such
binaries, generated snapshots, reports and reduced execution roots stay under
ignored `fixtures/generated`, `artifacts` or `_build` directories. The reduced
roots are test inputs, not redistribution bundles. No runtime binary is added
to source, a release asset or a CI upload. Any later redistribution needs its
own source/notice/license review as described above.

Cross-builds use the existing pinned MoonBit toolchain's runtime C sources as
local compiler inputs; they are not copied into this repository. AArch64
reference execution uses the hash-pinned QEMU package from
`tools/oracle/bootstrap_reference.py`. The verifier temporarily installs QEMU
only in ignored execution roots, after snapshot capture, and removes it even
when execution fails. `tools/targets.json` contains original catalog metadata
(package and loader identities), not binary payloads or an OS distribution.
This stage adds no third-party copied source or binary distribution.
