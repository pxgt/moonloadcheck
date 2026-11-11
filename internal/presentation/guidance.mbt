///|
/// General investigation steps, not a claim that a particular repair is safe.
pub fn guidance(code : String) -> Array[String] {
  match code {
    "MLC001" =>
      [
        "Interpreter unavailable", "Check the executable's PT_INTERP path against the captured target namespace and loader identity.",
        "Stage the intended target loader and its runtime, or rebuild for that target. A host loader or an arbitrary symlink is not a verified replacement.",
        "Capture the repaired target again and rerun dependency and compatibility checks.",
      ]
    "MLC002" =>
      [
        "Dependency search failed", "Follow the dependency chain and ordered candidate trace; distinguish missing files from rejected candidates and search-stopping errors.",
        "Stage the required library in the intended target path, or correct the declaring object's RUNPATH/RPATH or explicit search facts. Keep architecture and SONAME consistent.",
        "Rerun compatibility checks: resolving a pathname alone does not establish symbol/version compatibility.",
      ]
    "MLC003" =>
      [
        "Architecture mismatch", "Compare the entry, interpreter and selected objects' ELF machine values with the declared target.",
        "Rebuild or select a matching architecture set. Renaming a library does not change its machine type.",
        "Recapture and check the complete dependency closure, then validate execution on the intended runtime.",
      ]
    "MLC004" =>
      [
        "Required version node unavailable", "Inspect the requested version, named provider and version-check evidence. A matching filename or SONAME is insufficient.",
        "Use a provider that exports the required version, or rebuild the consumer for the supported API baseline. Do not patch version names to manufacture compatibility.",
        "Compare before/after reports with the same consumer; confirm the finding is resolved and perform application tests.",
      ]
    "MLC005" =>
      [
        "Referenced symbol cannot be resolved", "Inspect the symbol, requested version, selected provider, lookup policy, phase and relocation reference offsets.",
        "Restore a compatible exported definition or rebuild the consumer against the intended library. Check visibility and ordering instead of assuming every removed export breaks every app.",
        "Rerun the explicit consumer comparison and application tests; a symbol match does not establish C/C++ type or layout ABI compatibility.",
      ]
    "MLC006" =>
      [
        "Invalid input evidence", "Inspect the reported path, digest, offset or malformed ELF condition before drawing a deployment conclusion.",
        "Regenerate a quiescent snapshot or replace corrupt input from its verified source; retain the original error for investigation.",
        "Only evaluate compatibility after the input error is resolved. Invalid evidence is not a pass.",
      ]
    "MLC007" =>
      [
        "Evidence is incomplete", "Identify the missing search fact, provider identity or scope evidence in the saved explanation.",
        "Supply facts measured on the actual target and capture the needed namespace. Do not substitute host defaults or guessed token values.",
        "Rerun analysis and preserve any remaining inconclusive result until the missing evidence is established.",
      ]
    "MLC008" =>
      [
        "Behavior outside the verified model", "Read the explanation and not_checked list to identify the unsupported loader, binding or runtime behavior.",
        "Use a genuinely supported deployment condition, or retain this gap and investigate with an independent runtime test. Changing a profile label does not add support.",
        "Keep the CI gate blocked by inconclusive evidence; a successful single execution does not prove the unmodeled behavior generally safe.",
      ]
    "MLC009" =>
      [
        "Analysis resource limit reached", "Locate the exhausted parser, namespace or traversal limit and retain the partial findings already reported.",
        "Reduce irrelevant input or review a bounded implementation change with resource tests. Do not discard required dependencies merely to pass.",
        "Recapture and rerun; a resource-limited analysis cannot certify the remaining input.",
      ]
    _ =>
      [
        "Unfamiliar diagnostic code", "Preserve the saved severity, explanation and suggested action; the code is not recognized by this renderer.",
        "Consult the matching analyzer version's documentation before changing the deployment.",
        "Rerun with reviewed tooling and retain unresolved uncertainty.",
      ]
  }
}
