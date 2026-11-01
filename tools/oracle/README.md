# Rebuilding the M0 reference cases

On Linux with Python 3, GCC, binutils and an AArch64 cross compiler:

```sh
python3 tools/oracle/bootstrap_reference.py
python3 tools/oracle/build_fixtures.py
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
