# Symbol lookup and parser boundary evidence

This increment tests the existing controlled profiles. It adds independent
evidence, not new loader families or a broader application-correctness claim.

## Real loader observations

`tools/corpus/build_linkage_edges.py` builds our own C sources against the locked
Jammy/Noble runtime roots, on amd64 and arm64. It records **60 snapshots and 56
actual executions**; AArch64 execution uses the pinned QEMU helper. Twelve
snapshots contain deliberately changed relocation metadata and are never run.

| Case | Actual execution | Required static result |
| --- | --- | --- |
| PIE and non-PIE executable controls | Success | pass_static; ELF type, RPATH/RUNPATH and NODEFLIB facts agree with readelf |
| Matching non-UTF-8 name `61ff69` | Success | Byte name and selected provider preserved |
| Required `61ff69`, provided `61fe69` | Undefined-symbol failure | fail, even though lossy UTF-8 displays both names identically |
| Strong undefined dynsym without any active relocation | Success | pass_static; the unused dynsym entry does not become a requirement |
| Required version with a different provider-local index | Success | Match `EDGE_1` by name/hash; provider index 17 differs from the consumer index |
| LOCAL, INTERNAL or HIDDEN first provider | Calls second provider and returns its distinct value | First provider does not satisfy an external reference |
| IFUNC returning the expected implementation value | Success | Definition exists, pass_static |
| IFUNC returning the wrong application value | Application exits 41 | Definition still exists, pass_static; resolver/implementation behavior is outside this check |
| Missing lazy PLT symbol, never called | Success | fail for the missing reference, labeled startup-or-first-call |
| Same lazy executable, first call requested | Undefined-symbol failure | Same missing-reference evidence |
| Same lazy executable with LD_BIND_NOW=1 | Failure before the call is reached | Same missing-reference evidence; execution timing differs |

The lazy checks use the same executable and library bytes for all three runs.
The snapshot analyzer does not consume invocation arguments or general process
environment variables. Its conservative check covers all declared dynamic
references, including potentially deferred ones.

The IFUNC cases deliberately show why pass_static is not a prediction of the
program's return value. They do not execute IFUNC resolvers inside the analyzer.
The fixtures use ordinary global functions as resolver results and do not claim
coverage of arbitrary resolver side effects or hardware-dependent selection.

The LOCAL/visibility, byte-name, unused-symbol and version-index cases apply
documented byte edits to our own compiled fixtures. LOCAL/visibility edits leave
the hash candidate present, making rejection observable; these are controlled
loader experiments, not claims that ordinary linkers emit that table layout.
Byte-name edits rebuild the SysV hash table from the raw names. Both compiler
commands and post-edit input hashes are retained in the generated oracle.

The primary rule reference is the fixed [glibc 2.35 symbol lookup source](https://github.com/bminor/glibc/blob/glibc-2.35/elf/dl-lookup.c).
The separately locked Noble loader is independently executed rather than inferred
from that source revision. No loader implementation code is copied.

## Non-executed relocation inputs

Three metadata variants per architecture/runtime exercise an unknown relocation
with a symbol, an unknown symbol-free relocation, and R_*_NONE in place of one
RELATIVE record. Unknown types retain MLC008/unknown and final inconclusive.
NONE and ordinary symbol-free RELATIVE records do not cause external-symbol
lookups. These inputs are never executed and their acceptance does not validate
relocation writes, addresses or resulting application behavior.

## Independent object fields and exact table ends

The builder captures `readelf -hW -lW -dW` output and extracts expected runtime
metadata for 120 own-source objects. MoonBit tests compare machine/type,
interpreter, ordered NEEDED, SONAME, RPATH, RUNPATH, PIE and NODEFLIB fields.
These checks cover PIE, non-PIE EXEC and shared objects. They are object-field
checks, not a field-by-field comparison of every ELF structure.

`tools/corpus/build_parser_edges.py` supplies 36 additional **non-executed**
inputs on the two architectures. Twelve positive controls relocate intact GNU
hash, SysV hash, dynsym, Versym, Verneed and Verdef tables to the exact end of a
new file-backed PT_LOAD segment. Their metadata remains readable, including
the last hashed symbol. Twenty-four negative variants truncate the final
record, a version header or auxiliary record, or remove the final GNU-chain
terminator. They must return Malformed rather than pass or an unrelated
resource-limit result. The complete controls distinguish an actual range check
from failure caused by an invalid enclosing ELF header.

The runtime reader now reports the requested virtual address and size when a
table is not file backed, the PT_DYNAMIC file offset for partial/unterminated
entries, and the dynamic-string offset/table size for invalid names. Dedicated
tests check those positions. These are diagnostic improvements; public API
signatures and error categories are unchanged.

These are focused range tests. They do not establish exhaustive malformed-input
coverage, allocator resilience or behavior at every configured resource cap.

## Reproduce

After the existing reference/corpus setup:

```sh
python3 tools/corpus/build_linkage_edges.py
python3 tools/corpus/build_parser_edges.py
moon build --target js,native
moon test --target js,native
python3 tools/corpus/verify_linkage_edges.py --js _build/js/debug/build/cmd/main/main.js --native _build/native/debug/build/cmd/main/main.exe
```

The CLI verifier checks all 60 snapshots per backend and can compare saved JSON
from another host with `--compare-dir`. See the [evidence map](ACCEPTANCE_STATUS.md)
for outstanding resource, profile, special-binding and release work.
