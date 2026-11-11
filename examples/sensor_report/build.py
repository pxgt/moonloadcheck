"""Build the independent MoonBit native app and its original C shared library."""
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent


def build():
    output = ROOT / "_build/ffi"
    output.mkdir(parents=True, exist_ok=True)
    for variant in ["current", "legacy"]:
        subprocess.run(["gcc", "-shared", "-fPIC", "-Wall", "-Wextra", "-Werror",
            str(ROOT / "native/calibration.c"), "-Wl,-soname,libsensorcal.so.1",
            "-Wl,--version-script=" + str(ROOT / "native" / (variant + ".map")),
            "-o", str(output / (variant + ".so"))], check=True)
    shutil.copy2(output / "current.so", output / "libsensorcal.so")
    shutil.copy2(output / "current.so", output / "libsensorcal.so.1")
    subprocess.run(["moon", "build", "--target", "native", "--deny-warn"], cwd=ROOT, check=True)


if __name__ == "__main__":
    build()
