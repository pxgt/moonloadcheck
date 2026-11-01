"""Install the verified Linux toolchain inside this checkout, without global changes."""
from pathlib import Path
import hashlib
import os
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.10.16%2Bb1a0e846e"
ARCHIVES = [
    (f"https://cli.moonbitlang.com/binaries/{VERSION}/moonbit-linux-x86_64.tar.gz",
     "84ae424cd31bc485d2cf4d3736534e52f2f265ceafb562a187b9ab26d9566212", "toolchain.tar.gz", ""),
    (f"https://cli.moonbitlang.com/cores/core-{VERSION}.tar.gz",
     "e7db6e3c80a97af953598b374cf14f3e330918b1ca4659b141b9f550c9c0adb0", "core.tar.gz", "lib"),
]


def install():
    target = ROOT / ".tools/moon-0.10.16"
    target.mkdir(parents=True, exist_ok=True)
    for url, digest, filename, subdir in ARCHIVES:
        archive = target / filename
        if not archive.exists():
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read(512 * 1024 * 1024 + 1)
            if len(data) > 512 * 1024 * 1024:
                raise ValueError("toolchain archive exceeds limit")
            if hashlib.sha256(data).hexdigest() != digest:
                raise ValueError("toolchain download digest mismatch")
            archive.write_bytes(data)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != digest:
            raise ValueError("cached toolchain digest mismatch")
        destination = target / subdir
        destination.mkdir(exist_ok=True)
        subprocess.run(["tar", "xzf", str(archive), "--no-same-owner", "-C", str(destination)], check=True)
    binary = target / "bin/moon"
    env = {**os.environ, "PATH": str(target / "bin") + os.pathsep + os.environ["PATH"]}
    subprocess.run([str(binary), "-C", str(target / "lib/core"), "bundle", "--warn-list", "-a", "--all"], check=True, env=env)
    subprocess.run([str(binary), "version", "--all"], check=True, env=env)
    print(str(target / "bin"))


if __name__ == "__main__":
    install()
