"""Build the independent MoonBit native app and its original C shared library."""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent


def build(arch="amd64"):
    compiler = "gcc" if arch == "amd64" else "aarch64-linux-gnu-gcc"
    compiler = shutil.which(compiler)
    if compiler is None:
        raise RuntimeError("install the selected C compiler before building")
    triple = subprocess.check_output([compiler, "-dumpmachine"], text=True).strip()
    expected = "x86_64" if arch == "amd64" else "aarch64"
    if not triple.startswith(expected + "-"):
        raise RuntimeError(f"compiler target {triple} does not match {arch}")
    output = ROOT / "_build/ffi"
    output.mkdir(parents=True, exist_ok=True)
    for variant in ["current", "legacy"]:
        subprocess.run([compiler, "-shared", "-fPIC", "-Wall", "-Wextra", "-Werror",
            str(ROOT / "native/calibration.c"), "-Wl,-soname,libsensorcal.so.1",
            "-Wl,--version-script=" + str(ROOT / "native" / (variant + ".map")),
            "-o", str(output / (variant + ".so"))], check=True)
    shutil.copy2(output / "current.so", output / "libsensorcal.so")
    shutil.copy2(output / "current.so", output / "libsensorcal.so.1")
    # The pinned Moon toolchain selects generated C and recompiles its runtime
    # for MOON_CC. Never link the host's prebuilt runtime into the ARM binary.
    environment = dict(os.environ, MOON_CC=compiler)
    subprocess.run(["moon", "build", "--target", "native", "--deny-warn"], cwd=ROOT, env=environment, check=True)
    record = dict(architecture=arch, compiler_target=triple,
        compiler_version=subprocess.check_output([compiler, "-dumpfullversion"], text=True).strip())
    (ROOT / "_build/build.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arch", choices=["amd64", "arm64"], default="amd64")
    build(parser.parse_args().arch)
