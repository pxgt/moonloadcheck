"""Maintainer-only recipe: freeze release-pocket packages from signed Ubuntu indexes.

Normal CI uses the resulting lock, never a moving package resolver. Run on Linux
with ubuntu-keyring and gpgv; this does not install packages or alter apt sources.
"""
from pathlib import Path
import hashlib
import json
import lzma
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = {"hello", "jq", "zstd", "libc6", "libjq1", "libonig5", "libgcc-s1",
            "libstdc++6", "liblz4-1", "liblzma5", "zlib1g"}


def fetch(url, path, expected=None):
    if not path.exists():
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read(64 * 1024 * 1024 + 1)
        if len(data) > 64 * 1024 * 1024:
            raise ValueError("download exceeds bound")
        if expected and hashlib.sha256(data).hexdigest() != expected:
            raise ValueError("download hash mismatch")
        path.write_bytes(data)
    data = path.read_bytes()
    if expected and hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("cached hash mismatch")
    return data


def stanzas(path):
    with lzma.open(path, "rt", encoding="utf-8") as stream:
        record = {}
        for line in stream:
            if line == "\n":
                yield record
                record = {}
            elif not line.startswith(" ") and ": " in line:
                key, value = line.rstrip("\n").split(": ", 1)
                record[key] = value
        if record:
            yield record


def freeze():
    contexts = []
    for suite in ["jammy", "noble"]:
        for arch in ["amd64", "arm64"]:
            origin = "https://archive.ubuntu.com/ubuntu" if arch == "amd64" else "https://ports.ubuntu.com/ubuntu-ports"
            cache = ROOT / ".tools/corpus/indexes" / suite / arch
            cache.mkdir(parents=True, exist_ok=True)
            release_url = f"{origin}/dists/{suite}/InRelease"
            signed = fetch(release_url, cache / "InRelease")
            subprocess.run(["gpgv", "--keyring", "/usr/share/keyrings/ubuntu-archive-keyring.gpg",
                "--output", str(cache / "Release"), str(cache / "InRelease")], check=True)
            hashes, active = {}, False
            for line in (cache / "Release").read_text().splitlines():
                if line == "SHA256:":
                    active = True
                elif not line.startswith(" "):
                    active = False
                elif active:
                    digest, size, name = line.split()
                    hashes[name] = (digest, int(size))
            found, indexes = {}, []
            for component in ["main", "universe"]:
                name = f"{component}/binary-{arch}/Packages.xz"
                digest, size = hashes[name]
                url = f"{origin}/dists/{suite}/{name}"
                path = cache / (component + ".xz")
                data = fetch(url, path, digest)
                if len(data) != size:
                    raise ValueError("index size mismatch")
                indexes.append(dict(url=url, sha256=digest))
                for record in stanzas(path):
                    if record.get("Package") in PACKAGES:
                        package = record["Package"]
                        if package in found:
                            raise ValueError("ambiguous release package")
                        found[package] = dict(name=package, version=record["Version"], architecture=record["Architecture"],
                            source=record.get("Source", package), url=origin + "/" + record["Filename"],
                            sha256=record["SHA256"], size=int(record["Size"]), depends=record.get("Depends", ""),
                            metadata=f"https://packages.ubuntu.com/{suite}/{package}")
            if set(found) != PACKAGES:
                raise ValueError((suite, arch, PACKAGES - set(found)))
            contexts.append(dict(suite=suite, architecture=arch, release_url=release_url,
                inrelease_sha256=hashlib.sha256(signed).hexdigest(), indexes=indexes,
                packages=[found[key] for key in sorted(found)]))
            print(suite, arch, len(found), "packages locked", flush=True)
    (ROOT / "tools/corpus/ubuntu.lock.json").write_text(json.dumps(dict(schema_version=1,
        purpose="Historical release-pocket regression roots; not deployment recommendations",
        signature_keyring="Ubuntu archive keys verified by gpgv", contexts=contexts), indent=2) + "\n")


if __name__ == "__main__":
    freeze()
