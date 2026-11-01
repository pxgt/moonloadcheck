"""Build structurally valid unsupported ELF objects; never execute them."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[2]


def build():
    folder = ROOT / "fixtures/generated/inputs"
    folder.mkdir(parents=True, exist_ok=True)
    records = []
    for name, compiler, flags, expected in [
        ("rel64", "gcc", [], ["ELF64", "REL (Relocatable file)"]),
        ("elf32", "gcc", ["-m32"], ["ELF32", "REL (Relocatable file)"]),
        ("big-endian", "aarch64-linux-gnu-gcc", ["-mbig-endian"], ["ELF64", "big endian"]),
    ]:
        output = folder / (name + ".o")
        subprocess.run([compiler, *flags, "-c", str(ROOT / "fixtures/src/graph_library.c"), "-o", str(output)], check=True)
        header = subprocess.check_output(["readelf", "-hW", str(output)], text=True)
        assert all(part in header for part in expected), header
        (folder / (name + ".readelf.txt")).write_text(header)
        records.append(dict(case=name, sha256=hashlib.sha256(output.read_bytes()).hexdigest(),
            compiler=subprocess.check_output([compiler, "-dumpfullversion"], text=True).strip(), flags=flags, reference=header))
    (folder / "oracle.json").write_text(json.dumps(records, indent=2) + "\n")
    print("ELF input classes: 3 valid unsupported objects checked with readelf")


if __name__ == "__main__":
    build()
