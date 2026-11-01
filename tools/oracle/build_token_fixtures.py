"""Record target loader's LIB/PLATFORM facts and exercise their expansion."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from capture_snapshot import capture

ROOT = Path(__file__).resolve().parents[2]


def build():
    outcomes = []
    for arch, machine in [("x86_64", 62), ("aarch64", 183)]:
        cc = "gcc" if machine == 62 else "aarch64-linux-gnu-gcc"
        system = Path("/lib/x86_64-linux-gnu") if machine == 62 else Path("/usr/aarch64-linux-gnu/lib")
        interpreter = "/lib64/ld-linux-x86-64.so.2" if machine == 62 else "/lib/ld-linux-aarch64.so.1"
        loader = system / Path(interpreter).name
        prefix = [] if machine == 62 else [str(ROOT / ".tools/reference/qemu/usr/bin/qemu-aarch64-static")]
        env = {k: v for k, v in os.environ.items() if not k.startswith("LD_")}
        diagnostics = subprocess.check_output(prefix + [str(loader), "--list-diagnostics"], text=True, env=env)
        facts = dict(line.split("=", 1) for line in diagnostics.splitlines() if line.startswith(("dl_dst_lib=", "dl_platform=")))
        lib, platform = json.loads(facts["dl_dst_lib"]), json.loads(facts["dl_platform"])
        for value in [lib, platform]:
            if not value or any(part in ["", ".", ".."] for part in value.split("/")):
                raise ValueError("unsupported diagnostic token")
        folder = ROOT / "fixtures/generated/tokens" / arch
        root = folder / "root"
        libraries = root / "opt/demo" / lib / platform
        for path in [libraries, root / "runtime", (root / interpreter.lstrip("/")).parent]:
            path.mkdir(parents=True, exist_ok=True)
        subprocess.run([cc, "-shared", "-fPIC", str(ROOT / "fixtures/src/choice.c"),
            "-Wl,-soname,libchoice.so.1", "-o", str(libraries / "libchoice.so.1")], check=True)
        subprocess.run([cc, str(ROOT / "fixtures/src/app.c"), "-L" + str(libraries), "-l:libchoice.so.1",
            "-Wl,-rpath,$ORIGIN/$LIB/${PLATFORM}", "-Wl,-z,now", "-o", str(root / "opt/demo/app")], check=True)
        shutil.copy2(system / "libc.so.6", root / "runtime/libc.so.6")
        shutil.copy2(loader, root / interpreter.lstrip("/"))
        profile = dict(rule_revision="glibc-2.35-controlled-v2", loader_family="glibc", machine=machine,
            loader_path_hex=interpreter.encode().hex(), loader_sha256=hashlib.sha256(loader.read_bytes()).hexdigest(),
            cwd_hex=b"/".hex(), default_dirs_hex=[], library_path_hex=[b"/runtime".hex()],
            cache_mode="disabled", hwcaps_policy="none", secure_execution=False, preload=[], audit=[],
            lib_token_hex=lib.encode().hex(), platform_token_hex=platform.encode().hex())
        capture(root, profile, folder / "snapshot")
        unknown = dict(profile)
        del unknown["platform_token_hex"]
        capture(root, unknown, folder / "unknown-snapshot")
        command = prefix + [str(loader), "--inhibit-cache", "--glibc-hwcaps-mask", "", "--library-path", str(root / "runtime")]
        result = subprocess.run(command + [str(root / "opt/demo/app")], env=env, capture_output=True, text=True, timeout=15)
        listing = subprocess.check_output(command + ["--list", str(root / "opt/demo/app")], env=env, text=True, timeout=15)
        if result.returncode != 0 or str(libraries / "libchoice.so.1") not in listing:
            raise AssertionError((arch, result.returncode, result.stderr, listing))
        outcomes.append(dict(architecture=arch, lib=lib, platform=platform, exit_code=result.returncode,
            selected="/opt/demo/" + lib + "/" + platform + "/libchoice.so.1"))
    (ROOT / "fixtures/generated/tokens/oracle.json").write_text(json.dumps(outcomes, indent=2) + "\n")
    print(f"Tokens: {len(outcomes)} loader outcomes matched with measured target values")


if __name__ == "__main__":
    build()
