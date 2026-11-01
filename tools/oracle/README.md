# Rebuilding reference cases

On Linux with Python 3, GCC, binutils and an AArch64 cross compiler:

```sh
python3 tools/oracle/bootstrap_reference.py
python3 tools/oracle/build_fixtures.py
python3 tools/oracle/build_u1_snapshots.py
```

The bootstrap downloads two hash-pinned Ubuntu packages into the ignored
`.tools/reference` directory and extracts them without installing system
packages. QEMU is used directly; no binfmt registration is required.

Package sources and published hashes:

- [qemu-user-static 6.2+dfsg-2ubuntu6.30](https://packages.ubuntu.com/jammy/amd64/qemu-user-static/download)
- [libc6 2.39-0ubuntu8.9](https://packages.ubuntu.com/noble/amd64/libc6/download)

The fixture builder generates our Apache-2.0 C sources under
`fixtures/generated/{x86_64,aarch64}` and records compiler versions, loader
hashes, input hashes, commands and actual outcomes in `oracle.json`.

The nine cases per architecture cover normal, stripped and sectionless ELF,
missing symbol versions, removal of used versus unused exports, RPATH
propagation, RUNPATH non-propagation and corrected RUNPATH. These are reference
loader results, not claims that MoonLoadCheck already diagnoses each case.

The parser experiments can then be checked with:

```sh
moon test --target js
moon test --target native
moon run --target js cmd/probe -- --file fixtures/generated/x86_64/app
```

The parser is preserved as a hash-locked internal third-party dependency, so a
clean checkout does not need a registry-manifest migration. The M0 experiments
do not implement a deployment verdict.

The M1 U1 builder captures portable snapshots and checks seven additional
loading outcomes on each architecture. It covers relocation failure and two
fixes, wrong architecture, directory/PIE candidates and symlink ORIGIN behavior.
These cases are checked by the dependency analyzer tests.

For the pinned Linux compiler, install only inside this checkout:

```sh
python3 tools/bootstrap_moon.py
export PATH="$PWD/.tools/moon-0.10.16/bin:$PATH"
moon update
moon check --target js,native --deny-warn
moon build --target js,native
moon test --target js,native
python3 tools/verify_cli.py --js _build/js/debug/build/cmd/main/main.js --native _build/native/debug/build/cmd/main/main.exe
python3 tools/check_vendor.py
```

JS tests require Node.js in PATH. Native tests require a Linux C toolchain.
The CLI verifier accepts either backend separately and can compare reports
against `--compare-dir artifacts/cli` from another host. It checks all four
exit categories, content tampering and deterministic reports.

The official compiler archive's SHA-256 is published by MoonBit; the matching
core archive is pinned to the hash fetched from its versioned official URL.
Distribution reference compiler versions and actual loader hashes are recorded
by the fixture builder; apt packages are not claimed to be frozen byte-for-byte.
