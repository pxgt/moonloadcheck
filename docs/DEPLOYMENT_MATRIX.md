# Preflight and multi-target deployment matrices

These are source additions for 0.3.0-dev, not features in the immutable 0.2.0
package. Build the current CLI with the pinned toolchain in README. The Python
adapters handle configuration and filesystem I/O; MoonBit retains ELF decisions,
saved-check validation, matrix verdict aggregation and HTML rendering.

## Preflight a staged root

Use the same explicit deployment config described in [INTEGRATION.md](INTEGRATION.md):

```sh
python3 tools/preflight_deployment.py --config /path/to/deployment.json \
  --native "$PWD/_build/native/debug/build/cmd/main/main.exe"
```

`--js "$PWD/_build/js/debug/build/cmd/main/main.js"` is also supported. Capture
requires Linux. This operation does not modify the staged root or execute its
programs/loader. It uses a temporary snapshot, removed after the check, and
prints JSON with missing facts, suggested next steps and dependency evidence.
The root must be quiescent and outside the temporary output directory.

A missing field is not known-empty or false. Working directory, library/default
paths, cache/hwcaps modes, secure execution, preloads and audit inputs remain
caller declarations. File inspection does not prove those runtime facts. Full
config validation and the analyzer's existing input/resource limits apply.
Up to 3 MiB of report evidence is retained; split larger entry lists.

Exit 0 means only the declared **dependency** checks passed. It does not mean
symbols, versions, application behavior or an arbitrary Linux environment are
compatible. A missing library fails, unknown rules remain inconclusive, and
invalid/missing facts remain input_error. Use the full compatibility check next.

## Check multiple targets and applications

Each target references an ordinary deployment config, whose `entries` can list
multiple programs. Config paths resolve relative to the matrix file; staged
roots still resolve relative to their own deployment config.

```json
{
  "schema_version": 1,
  "targets": [
    {"id": "release-amd64-jammy", "config": "./jammy.json"},
    {"id": "release-amd64-noble", "config": "./noble.json"},
    {"id": "release-arm64", "config": "./arm64.json"}
  ]
}
```

```sh
python3 tools/check_matrix.py --config /path/to/matrix.json \
  --out /path/to/new-matrix-run \
  --native "$PWD/_build/native/debug/build/cmd/main/main.exe"
```

Output is a new directory outside every staged root. Original config bytes are
hashed; execution uses frozen copies with absolute roots. A failed target is
recorded while subsequent targets are checked. Invalid matrix structure and
unsafe output placement stop the run before output creation. Never overwrite
a prior run. Artifacts include numbered target directories, raw `matrix.json`,
derived `summary.json`, and self-contained `index.html`.

Open `index.html` locally to scan the target/application verdict table and
expand individual evidence. Target errors and unrun entries stay visible.
Names/messages are escaped, links are generated local fragments, and the page
contains no scripts or external assets. Same entry/architecture groups with
different program digests are counted separately. Zero differing groups does
not establish identity for missing/unavailable program evidence; digests and
all saved metadata remain unauthenticated, not a proof of environment-only causation.

Matrix input is a new schema (`kind=deployment_matrix`, schema 1), separate
from check schema 2, comparison schema 2 and the existing deployment summary.
Its 1..16 targets contain config digests, declared entries, nested checks or
command errors, and optional target errors. At most 128 declared entries/checks
are accepted. The adapter caps retained reports at 3 MiB; the MoonBit renderer
caps total input at 4,194,304 UTF-16 code units and output at 33,554,432. These
are representation bounds, not whole-process memory guarantees. Invalid or
oversized rendering returns input_error; it cannot silently drop a failing cell.

Saved matrices can be rendered on Linux or Windows without their snapshots:

```sh
mlc matrix-report --input matrix.json --format html > matrix.html
mlc matrix-report --input matrix.json --format summary
```

The aggregate verdict is **input_error (3), fail (1), inconclusive (2), then
pass_static (0)**, in that precedence. Report rendering retains that exit.
Nested check verdicts are validated, not trusted summary labels. Duplicate target
IDs/entries, missing results without explicit errors, misbound entry names and
contradictory check evidence are rejected. No baseline suppression/waiver is added.

## Additional fixed runtime and external application

The new preset `ubuntu-jammy-2.35-0ubuntu3.15-amd64` identifies exactly Ubuntu
libc6 2.35-0ubuntu3.15, with loader SHA-256
`41daf7836f7fce21a40ca63a00c5caf21b05a35a76ccc075d86f1716212cdf01`.
`tools/external.lock.json` fixes the official package source/size/hash.
`python3 tools/verify_targets.py` extracts that pinned package locally and
checks the catalog. This is an additional x86-64 controlled identity, not a
promise for every updated Jammy host or a new AArch64 runtime identity.

The external case builds unmodified upstream zstd 1.5.7 using its official
`libzstd` and `zstd-dll` Make targets (optional gzip/lzma/lz4 integrations disabled).
It also builds upstream libzstd 1.4.8. All sources and notices stay ignored.
After the full README/corpus prerequisites and CLI build, run:

```sh
python3 tools/verify_targets.py
python3 tools/external_example.py --native _build/native/debug/build/cmd/main/main.exe \
  --js _build/js/debug/build/cmd/main/main.js
```

The same x86-64 executable is staged against fixed Jammy, Noble and the added
Jammy runtime, with good/missing/old/restored library cases. Independent loader
listing, application probes (with immediate binding) and compression/decompression
roundtrips distinguish loading from business behavior. In particular, the old
library can satisfy static symbol checks and load successfully while zstd's own
version guard refuses execution. That observed application rejection is outside
the static compatibility claim and must not be misreported as a loader failure.

This is our reproducible integration of an external project, not a claim that
zstd maintainers adopted MoonLoadCheck. The original MoonBit native/FFI example
continues to cover x86-64 and emulated AArch64. Neither example establishes
physical ARM hardware behavior. No maintainer is contacted by these recipes.

Keep whole run directories private: they contain runtime binaries and snapshots.
Only source, recipes, locks and documentation enter the repository/package.
Review selected JSON/HTML for internal paths before sharing; no upload is added.
