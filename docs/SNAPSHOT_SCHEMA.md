# Snapshot schema 1

A snapshot directory contains `manifest.json` and `blobs/<sha256>`. The core
accepts manifest text and a blob-reading callback, so it does not depend on the
analysis host's filesystem semantics. The collector is a small Linux Python
adapter; all content verification, ELF parsing and dependency decisions use MoonBit.

A blob callback that raises is wrapped as InvalidSnapshot with the validated
digest, rather than propagating host-specific read-error text. Successful reads
still undergo the normal size and SHA-256 checks.

The manifest contains `schema_version: 1`, `profile` and `entries`. Profile
fields are required except optional `lib_token_hex` and `platform_token_hex`;
see the public `snapshot.Profile` type and the
[supported model](SUPPORTED_PROFILE.md). The collector accepts an explicit
profile, never inherits LD_* variables, and never executes target programs.

The optional token values encode the target loader's measured LIB/PLATFORM
substitutions as raw bytes. Omit a value when unknown; use is then inconclusive.
They are not guessed from the analysis host. The v2 controlled profile can use
`cache_mode: "glibc-cache-v1"` to read the indexed `/etc/ld.so.cache`; missing
cache means a known empty cache. The v1 profile retains disabled cache use.

Paths and symlink targets use canonical lowercase hex encodings of raw filename
bytes. Entry kinds are:

| kind | required fields | omitted fields |
| --- | --- | --- |
| directory | path_hex, kind | file_id, sha256, target_hex |
| file | path_hex, kind, file_id, sha256 | target_hex |
| symlink | path_hex, kind, target_hex | file_id, sha256 |

Absent optional fields are **omitted**, not JSON null. The decoder rejects
inconsistent field combinations and unsupported schema versions. Paths must
be unique canonical absolute physical paths with indexed directory parents.
Symlink aliases are resolved at lookup time. Case differences remain distinct.

Each regular file has both `file_id` and `sha256`: hardlink aliases share an
identity, while identical content alone does not merge file identities.
Conflicting content for one identity is rejected. Blobs are deduplicated by
digest and every referenced digest is checked on load. An indexed loader's
digest must match the profile; a missing loader remains a deployment finding.

The collector uses lstat and no-follow reads, verifies file identity/size/times
around each read, and rejects special entries and set-id files. It does not
claim an atomic filesystem snapshot: capture a quiescent root or a filesystem
snapshot for coherent evidence. Target file access permissions and ACLs are
outside the current model. The collector does not guess library search rules.

```sh
python3 tools/capture_snapshot.py --root /path/to/staged-root --profile /path/to/profile.json --out /path/to/snapshot
```

The output must be outside the input root. Existing blobs with conflicting
content are rejected. No reference system binary is checked into this repo;
sample snapshots are generated locally by recorded recipes.

Schema 1 is experimental until the first release. A future format change will
use an explicit schema revision rather than silently changing path or identity
semantics. The manifest digest in a report hashes the exact input JSON bytes;
formatting a manifest therefore changes its evidence identifier.
