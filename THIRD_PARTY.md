# Dependencies and references

| Project | Use | License/source |
| --- | --- | --- |
| moonbit-community/elf 0.0.1 | Internal parser dependency; source preserved, package configuration adapted | [Apache-2.0 source](https://github.com/moonbit-community/elf.mbt), [locked provenance](internal/elf_vendor/UPSTREAM.json) |
| GNU glibc and binutils | Loader behavior and independent test tools | [glibc manual](https://sourceware.org/glibc/manual/latest/html_node/Dynamic-Linker.html), [readelf manual](https://sourceware.org/binutils/docs/binutils/readelf.html) |
| Gentoo lddtree | Related dependency-analysis tool | [source](https://github.com/gentoo/pax-utils/blob/master/lddtree.py) |
| PyPA auditwheel | Related distribution compatibility tool | [source](https://github.com/pypa/auditwheel) |
| libabigail | Related ABI compatibility tool | [manual](https://sourceware.org/libabigail/manual/abicompat.html) |

The 17 parser source files in `internal/elf_vendor` are copied verbatim from the hash-verified Mooncakes archive, with its LICENSE. They are third-party work, excluded from original-contribution counts. No source from the other reference tools has been copied. New runtime-table adapters and all project analysis code are maintained outside the vendor directory.
