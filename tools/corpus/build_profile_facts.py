"""Declared-fact variants; these are schema/model tests, not loader executions."""
import copy
import json
import os
from build_environment_edges import GENERATED


def build():
    source = GENERATED / "amd64/jammy/empty-runpath/snapshot"
    original = json.loads((source / "manifest.json").read_text())
    original["profile"]["library_path_hex"] = [b"/".hex(), b"/runtime".hex()]
    outcomes = []

    def variant(label, changes, code, omit=()):
        manifest = copy.deepcopy(original)
        manifest["profile"].update(changes)
        for field in omit:
            del manifest["profile"][field]
        folder = GENERATED / "facts" / label / "snapshot"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "blobs").mkdir(exist_ok=True)
        for blob in (source / "blobs").iterdir():
            if not (folder / "blobs" / blob.name).exists():
                os.link(blob, folder / "blobs" / blob.name)
        (folder / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
        outcomes.append(dict(case=label, entry="/app/bin/app", expected_code=code, selected={}, executed=False))

    optional = ["lib_token_hex", "platform_token_hex"]
    for field in original["profile"]:
        if field not in optional:
            variant(field + "-missing", {}, 3, [field])
            variant(field + "-null", {field: None}, 3)
    for field, value, code in [
        ("rule_revision", "", 2), ("loader_family", "", 2), ("machine", 0, 3),
        ("loader_path_hex", "", 3), ("loader_sha256", "", 3), ("cwd_hex", "", 3),
        ("default_dirs_hex", [], 0), ("library_path_hex", [], 1),
        ("cache_mode", "", 2), ("hwcaps_policy", "", 2),
        ("secure_execution", False, 0), ("preload", [], 0), ("audit", [], 0),
    ]:
        variant(field + "-empty", {field: value}, code)
    variant("cwd-element", {"library_path_hex": ["", b"/runtime".hex()]}, 0)
    for field, token in zip(optional, ["$LIB", "${PLATFORM}"]):
        variant(field + "-null", {field: None}, 3)
        variant(field + "-missing-unused", {}, 0, [field])
        variant(field + "-empty-unused", {field: ""}, 3)
        paths = [token.encode().hex(), b"/runtime".hex()]
        variant(field + "-missing-used", {"library_path_hex": paths}, 2, [field])
        # This profile requires nonempty measured substitutions. An explicit
        # empty token is invalid even when unused; omission represents unknown.
        variant(field + "-empty-used", {field: "", "library_path_hex": paths}, 3)
    (GENERATED / "facts.json").write_text(json.dumps(outcomes, indent=2) + "\n")
    print(f"Profile facts: {len(outcomes)} non-executed schema/model variants")


if __name__ == "__main__":
    build()
