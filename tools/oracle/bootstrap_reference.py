"""Download hash-pinned Ubuntu tools into .tools, without installing system packages."""
from pathlib import Path
import hashlib
import subprocess
import urllib.request

ROOT = Path(__file__).resolve().parents[2]
PACKAGES = [
    ("qemu", "https://security.ubuntu.com/ubuntu/pool/universe/q/qemu/qemu-user-static_6.2+dfsg-2ubuntu6.30_amd64.deb", "e4665bb7ce12d7f057f6d8bf3aa82c610dadf536e0cc733772116d0bacb19258"),
    ("noble", "https://security.ubuntu.com/ubuntu/pool/main/g/glibc/libc6_2.39-0ubuntu8.9_amd64.deb", "ff5557d99b51f761c4b7c92368b9cc45565eda17df9bf9eb4b134d09825008be"),
]

def main():
    target = ROOT / ".tools" / "reference"
    target.mkdir(parents=True, exist_ok=True)
    for name, url, expected in PACKAGES:
        archive = target / (name + ".deb")
        if not archive.exists():
            with urllib.request.urlopen(url, timeout=60) as response:
                data = response.read()
            if hashlib.sha256(data).hexdigest() != expected:
                raise ValueError("download digest mismatch: " + name)
            archive.write_bytes(data)
        if hashlib.sha256(archive.read_bytes()).hexdigest() != expected:
            raise ValueError("cached digest mismatch: " + name)
        destination = target / name
        destination.mkdir(exist_ok=True)
        subprocess.run(["dpkg-deb", "-x", str(archive), str(destination)], check=True)
        print(name, expected, flush=True)

if __name__ == "__main__":
    main()
