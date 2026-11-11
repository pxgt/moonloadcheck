"""Verify target identity presets against the locked extracted Ubuntu corpus.

Use --write only when intentionally updating the reviewed catalog. No binaries
are embedded in this metadata; users must still supply actual environment facts.
"""
from pathlib import Path
import argparse
import hashlib
import json

from corpus.build_roots import target_file

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "tools/targets.json"
LOCK = ROOT / "tools/corpus/ubuntu.lock.json"
ARCHES = {
    "amd64": (62, "/lib64/ld-linux-x86-64.so.2"),
    "arm64": (183, "/lib/ld-linux-aarch64.so.1"),
}


def catalog():
    lock = json.loads(LOCK.read_text(encoding="utf-8"))
    targets = {}
    for context in lock["contexts"]:
        suite, arch = context["suite"], context["architecture"]
        machine, interpreter = ARCHES[arch]
        root = ROOT / ".tools/corpus/roots" / suite / arch
        data = target_file(root, interpreter).read_bytes()
        if data[:6] != b"\x7fELF\x02\x01" or int.from_bytes(data[18:20], "little") != machine:
            raise ValueError(f"invalid {arch} loader in {root}")
        package = next(p for p in context["packages"] if p["name"] == "libc6")
        targets[f"ubuntu-{suite}-{arch}"] = dict(suite=suite, architecture=arch,
            package=dict(name=package["name"], version=package["version"], sha256=package["sha256"]),
            identity=dict(rule_revision="glibc-2.35-controlled-v2" if suite == "jammy" else "ubuntu-noble-2.39-0ubuntu8-v1",
                loader_family="glibc", machine=machine, loader_path=interpreter,
                loader_sha256=hashlib.sha256(data).hexdigest()))
    return dict(schema_version=1, corpus_lock_sha256=hashlib.sha256(LOCK.read_bytes()).hexdigest(), targets=targets)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    expected = catalog()
    if args.write:
        CATALOG.write_text(json.dumps(expected, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if json.loads(CATALOG.read_text(encoding="utf-8")) != expected:
        raise ValueError("target catalog differs from the corpus lock and extracted loaders")
    print("Verified target identities: " + ", ".join(sorted(expected["targets"])))


if __name__ == "__main__":
    main()
