# Internal third-party ELF parser

The `.mbt` files and LICENSE in this directory are preserved byte-for-byte from
`moonbit-community/elf@0.0.1`, Apache-2.0. `UPSTREAM.json` records the published
archive hash and each preserved file hash. Reproduce with `python3 tools/vendor_elf.py`.

Only package configuration is adapted. The registry version's legacy module
manifest cannot be installed directly with the tested current toolchains. The
internal copy removes that installation dependency while preserving the parser
implementation. It does not create a separately published ELF package.

These files are third-party code and must not be counted as MoonLoadCheck's
original contribution. Do not run project-wide formatting over this directory;
verify its byte hashes before commits. Analysis, runtime-table adaptations and
deployment diagnostics live outside this directory.

When an installable upstream release becomes available, evaluate replacing this
copy with a normal dependency against the same regression fixtures.
