# Development evidence

## 2026-11-01 Project foundation

- Started a separate MoonBit module for MoonLoadCheck.
- Confirmed the proposed GitHub repository and Mooncakes module name did not already exist.
- Recorded MoonBit 0.1.20261012 / moonc 0.10.15 as the initial toolchain.
- Available reference environment: Ubuntu WSL, glibc 2.35, GCC, readelf, AArch64 cross compiler.
- Parser, snapshot format, loader model and architecture runtime validation are pending.

The initial scaffold is not an implementation or an acceptance result. Subsequent entries record reproducible commands and actual outcomes.

## 2026-11-01 Loader and parser experiments

- Built reproducible x86-64 and AArch64 ELF fixtures from the repository's C sources.
- Nine expected loader outcomes matched per architecture; AArch64 ran under hash-pinned Ubuntu QEMU 6.2.
- Ran the x86-64 baseline with a separately extracted glibc 2.39 loader and libraries as well as the host glibc 2.35. This is a second loader smoke test, not a complete second environment validation.
- Six MoonBit tests passed on Windows JS (toolchain 0.1.20261012) and Linux native (0.1.20261016).
- Confirmed upstream `dynamic_symbol_table` and `symbol_version_table` return no table for sectionless inputs.
- A bounded segment adapter experiment recovers needed libraries, referenced/hashed symbol span and version requirements on both architectures, using upstream header/segment/string readers.
- The upstream low-level ParseAt implementations are not exposed to consumers. The adapter therefore supplies small checked runtime-table readers instead of copying an entire ELF parser.
- An empty AArch64 GNU hash omits trailing undefined symbols. Relocation references are needed to cover the requested symbols. The experiment explicitly marks whether its symbol extent is exact.
- The published ELF manifest requires local migration. `tools/prepare_dependencies.py` records the temporary M0 bridge; clean release installation is still unresolved.
- Windows native tests require unavailable MSVC tools. Linux native validation is available in WSL; no global compiler installation was performed.

M0 remains in progress: verify clean-checkout setup and cache metadata before freezing the implementation scope.
