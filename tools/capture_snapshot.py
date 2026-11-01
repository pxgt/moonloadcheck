"""Capture facts from an explicitly supplied Linux root; never execute inputs.

The portable index preserves filename bytes, symlinks and hardlink identity.
Dependency decisions and hash validation belong to the MoonBit consumer.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat


def capture(root: Path, profile: dict, out: Path):
    if os.name != "posix":
        raise RuntimeError("capture requires a Linux filesystem; analysis is portable")
    root, out = root.resolve(strict=True), out.resolve()
    if out == root or root in out.parents:
        raise ValueError("snapshot output must be outside the captured root")
    out.mkdir(parents=True, exist_ok=True)
    (out / "blobs").mkdir(exist_ok=True)
    entries, identities, stored = [], {}, set()
    total = 0

    def visit(host, target):
        nonlocal total
        if len(entries) >= 20000:
            raise ValueError("snapshot exceeds 20000 entries")
        before = os.lstat(host)
        entry = dict(path_hex=target.hex(), file_id=None, sha256=None, target_hex=None)
        if stat.S_ISLNK(before.st_mode):
            entry.update(kind="symlink", target_hex=os.readlink(host).hex())
        elif stat.S_ISDIR(before.st_mode):
            entry["kind"] = "directory"
        elif stat.S_ISREG(before.st_mode):
            if before.st_mode & 0o6000:
                raise ValueError("set-id files require an unsupported secure-execution profile")
            if before.st_size > 128 * 1024 * 1024:
                raise ValueError("file exceeds 128 MiB")
            fd = os.open(host, os.O_RDONLY | os.O_NOFOLLOW)
            with os.fdopen(fd, "rb") as stream:
                opened = os.fstat(stream.fileno())
                data = stream.read(128 * 1024 * 1024 + 1)
                after = os.fstat(stream.fileno())
            fingerprint = lambda s: (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)
            if fingerprint(before) != fingerprint(opened) or fingerprint(opened) != fingerprint(after):
                raise ValueError("input changed during capture")
            if len(data) > 128 * 1024 * 1024:
                raise ValueError("file grew beyond limit")
            digest = hashlib.sha256(data).hexdigest()
            identity = identities.setdefault((before.st_dev, before.st_ino), "file-" + str(len(identities)))
            entry.update(kind="file", file_id=identity, sha256=digest)
            if digest not in stored:
                total += len(data)
                if total > 256 * 1024 * 1024:
                    raise ValueError("snapshot exceeds 256 MiB")
                blob = out / "blobs" / digest
                if blob.exists() and blob.read_bytes() != data:
                    raise ValueError("existing content-addressed blob is corrupt")
                if not blob.exists():
                    blob.write_bytes(data)
                stored.add(digest)
        else:
            raise ValueError("special filesystem entries are not supported")
        entries.append(entry)
        if entry["kind"] == "directory":
            for name in sorted(os.listdir(host)):
                visit(os.path.join(host, name), (target.rstrip(b"/") + b"/" + name))
            if fingerprint_dir(before) != fingerprint_dir(os.lstat(host)):
                raise ValueError("directory changed during capture")

    def fingerprint_dir(s):
        return (s.st_dev, s.st_ino, s.st_mtime_ns, s.st_ctime_ns)

    visit(os.fsencode(root), b"/")
    manifest = dict(schema_version=1, profile=profile, entries=entries)
    text = json.dumps(manifest, sort_keys=True, indent=2) + "\n"
    if len(text.encode()) > 4 * 1024 * 1024:
        raise ValueError("manifest exceeds 4 MiB")
    (out / "manifest.json").write_text(text, encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    result = capture(args.root, json.loads(args.profile.read_text()), args.out)
    print(f"captured {len(result['entries'])} entries; MoonBit validates content on load")
