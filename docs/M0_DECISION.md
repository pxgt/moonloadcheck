# M0 feasibility decision

2026-11-01: proceed to M1 using explicit, bounded glibc target profiles. This is
a feasibility decision, not acceptance of a completed compatibility checker.

| Question | Evidence | Decision |
| --- | --- | --- |
| Can the ELF parser be reused? | Parser/segment experiments pass on JS and Linux native | Reuse the locked upstream implementation; maintain small runtime adapters separately |
| Can a clean checkout build? | An isolated Git archive with no dependency cache passed `moon check --target js` | Internal source lock avoids the published legacy manifest; upstream source/license hashes match |
| Are sectionless inputs viable? | Original, stripped and sectionless fixture metadata agrees on x86-64/AArch64 | Use program-header-based metadata and bounded readers |
| Are there independent behavior tests? | Nine loader outcomes per architecture matched, AArch64 using QEMU | Keep recipes and input/loader hashes; do not confuse these outcomes with analyzer coverage |
| Can cache metadata be captured? | All 428 host cache entries match `ldconfig -p` | Preserve raw flags, order and extension metadata; unsupported selection conditions remain unknown |
| Is a second glibc available? | Separately extracted 2.39 loader runs the baseline alongside host 2.35 | Complete environment snapshots and comparisons remain M1/M3 work |

Important boundaries discovered during M0:

- Empty GNU hash tables do not establish the full extent of trailing undefined
  symbols. Relocation references must be included; the adapter tracks whether
  the recovered symbol extent is exact.
- Upstream section-based convenience APIs return no dynamic symbol table for
  sectionless inputs. That absence is not evidence of no requirements.
- The host cache had no nonzero hwcap entries. Hardware-capability ranking has
  not been verified and must not be inferred from the metadata test.
- Tests on a Windows-mounted WSL directory do not establish Linux case-sensitive
  filesystem behavior. Path reference cases run on the Linux filesystem.
- Windows native compilation lacks MSVC tools. Native validation currently runs
  on Linux; Windows runs the JS backend and will analyze portable snapshots.

The internal ELF source is third-party code, excluded from original-contribution
counts. The source lock changes packaging only and does not publish another ELF
parser project. Replace it with a normal dependency when an installable upstream
release passes the same regression cases.

The next implementation gate is U1: capture a target namespace, apply the
declared library search policy, explain a broken indirect dependency, and verify
the corrected layout. Full symbol/version compatibility and upgrade impact
remain later gates.
