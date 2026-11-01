"""Path precedence, graph identity and host-isolation reference executions."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
from build_roots import ROOT, target_file, loader_command, capture

CASES = ["absolute-needed", "relative-needed", "empty-path", "rpath-first", "runpath-after-env",
         "direct-missing", "cycle", "diamond", "hardlink", "same-content", "corrupt-first",
         "select-good", "select-bad", "host-decoy"]


def build():
    outcomes = []
    for arch, machine, multiarch in [("amd64", 62, "x86_64-linux-gnu"), ("arm64", 183, "aarch64-linux-gnu")]:
        cc = "gcc" if machine == 62 else "aarch64-linux-gnu-gcc"
        interpreter = "/lib64/ld-linux-x86-64.so.2" if machine == 62 else "/lib/ld-linux-aarch64.so.1"
        for suite in ["jammy", "noble"]:
            for case in CASES:
                folder = ROOT / "fixtures/generated/paths" / arch / suite / case
                root = folder / "root"
                owned = (ROOT / "fixtures/generated/paths").resolve()
                if root.is_symlink() or root.resolve() == owned or not root.resolve().is_relative_to(owned):
                    raise ValueError("refusing cleanup outside generated path fixtures")
                if root.exists():
                    shutil.rmtree(root)
                for directory in ["runtime", "libs", "preferred", "override", "aliases", "good", "bad"]:
                    (root / directory).mkdir(parents=True, exist_ok=True)
                (root / interpreter.lstrip("/")).parent.mkdir(parents=True, exist_ok=True)
                compile_commands = []

                def run(command):
                    compile_commands.append([str(p).replace(str(ROOT), "$PROJECT") for p in command])
                    subprocess.run(command, check=True)

                def library(path, soname, *flags):
                    run([cc, "-shared", "-fPIC", str(ROOT / "fixtures/src/graph_library.c"),
                        "-Wl,-soname," + soname, "-Wl,--hash-style=both", *flags, "-o", str(root / path)])

                paths, links, flags, expected = ["/runtime"], [], [], 7
                if case in ["cycle", "diamond"]:
                    if case == "cycle":
                        library("runtime/libb.so.1", "libb.so.1", "-DFUNCTION=second")
                        library("runtime/liba.so.1", "liba.so.1", "-Wl,--no-as-needed", "-L" + str(root / "runtime"), "-l:libb.so.1")
                        library("runtime/libb.so.1", "libb.so.1", "-DFUNCTION=second", "-Wl,--no-as-needed", "-L" + str(root / "runtime"), "-l:liba.so.1")
                        links = ["-l:liba.so.1"]
                    else:
                        library("runtime/libleaf.so.1", "libleaf.so.1", "-DFUNCTION=leaf", "-DVALUE=3")
                        library("runtime/liba.so.1", "liba.so.1", "-DDEPENDENCY=leaf", "-DVALUE=2", "-L" + str(root / "runtime"), "-l:libleaf.so.1")
                        library("runtime/libb.so.1", "libb.so.1", "-DFUNCTION=second", "-DDEPENDENCY=leaf", "-DVALUE=4", "-L" + str(root / "runtime"), "-l:libleaf.so.1")
                        links, flags, expected = ["-l:liba.so.1", "-l:libb.so.1"], ["-DSECOND"], 12
                elif case in ["hardlink", "same-content"]:
                    for name in ["one", "two"]:
                        library("aliases/lib" + name + ".so.1", "/aliases/lib" + name + ".so.1", "-DCOUNT_LOADS")
                    links = [str(root / "aliases/libone.so.1"), str(root / "aliases/libtwo.so.1")]
                    flags = ["-rdynamic", "-DEXPECTED_LOADS=" + ("1" if case == "hardlink" else "2")]
                elif case in ["select-good", "select-bad"]:
                    for directory, version in [("good", "PATH_1"), ("bad", "PATH_2")]:
                        script = folder / (directory + ".map")
                        script.write_text(version + " { global: api; };\n")
                        library(directory + "/libapi.so.1", "libapi.so.1", "-Wl,--version-script=" + str(script))
                    links = [str(root / "good/libapi.so.1")]
                    paths = ["/good", "/bad", "/runtime"] if case == "select-good" else ["/bad", "/good", "/runtime"]
                else:
                    soname = "/libs/libapi.so.1" if case == "absolute-needed" else "libs/libapi.so.1" if case == "relative-needed" else "libapi.so.1"
                    location = "libs/libapi.so.1" if case.endswith("-needed") else "runtime/libapi.so.1"
                    library(location, soname)
                    links = [str(root / location)]
                    if case in ["rpath-first", "runpath-after-env", "corrupt-first"]:
                        library("preferred/libapi.so.1", "libapi.so.1")
                        library("override/libapi.so.1", "libapi.so.1", "-DVALUE=9")
                        if case == "corrupt-first":
                            paths = ["/preferred", "/override", "/runtime"]
                        else:
                            paths = ["/override", "/runtime"]
                            flags = ["-Wl,-rpath,/preferred", "-Wl,--disable-new-dtags" if case == "rpath-first" else "-Wl,--enable-new-dtags"]
                            expected = 7 if case == "rpath-first" else 9
                    elif case == "empty-path":
                        library("libapi.so.1", "libapi.so.1", "-DVALUE=9")
                        paths, expected = ["", "/runtime"], 9
                run([cc, str(ROOT / "fixtures/src/graph_app.c"), "-Wl,-z,now", "-Wl,--no-as-needed",
                    "-Wl,-rpath-link," + str(root / "runtime"), "-L" + str(root / "runtime"),
                    "-DEXPECTED=" + str(expected), *flags, *links, "-o", str(root / "app")])
                if case in ["hardlink", "same-content"]:
                    second = root / "aliases/libtwo.so.1"
                    second.unlink()
                    if case == "hardlink":
                        os.link(root / "aliases/libone.so.1", second)
                    else:
                        shutil.copy2(root / "aliases/libone.so.1", second)
                if case == "direct-missing":
                    (root / "runtime/libapi.so.1").unlink()
                if case == "corrupt-first":
                    (root / "preferred/libapi.so.1").write_bytes(b"not an ELF library\n")
                if case == "host-decoy":
                    host = ROOT / ".tools/corpus/host-decoys" / arch / suite
                    host.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(root / "runtime/libapi.so.1", host / "libapi.so.1")
                    (root / "runtime/libapi.so.1").unlink()
                    paths = [str(host), "/runtime"]
                source = ROOT / ".tools/corpus/roots" / suite / arch
                shutil.copy2(target_file(source, interpreter), root / interpreter.lstrip("/"))
                shutil.copy2(target_file(source, "/lib/" + multiarch + "/libc.so.6"), root / "runtime/libc.so.6")
                profile = dict(rule_revision="glibc-2.35-controlled-v2" if suite == "jammy" else "ubuntu-noble-2.39-0ubuntu8-v1",
                    loader_family="glibc", machine=machine, loader_path_hex=interpreter.encode().hex(),
                    loader_sha256=hashlib.sha256((root / interpreter.lstrip("/")).read_bytes()).hexdigest(), cwd_hex=b"/".hex(),
                    default_dirs_hex=[], library_path_hex=[p.encode().hex() for p in paths], cache_mode="disabled", hwcaps_policy="none",
                    secure_execution=False, preload=[], audit=[])
                helper = root / "qemu"
                if helper.is_file():
                    helper.unlink()
                capture(root, profile, folder / "snapshot")
                if arch == "arm64":
                    shutil.copy2(ROOT / ".tools/reference/qemu/usr/bin/qemu-aarch64-static", helper)
                environment = {"PATH": os.environ["PATH"], "LC_ALL": "C", "LD_BIND_NOW": "1"}
                try:
                    command = loader_command(root, arch, interpreter, paths) + ["/app"]
                    result = subprocess.run(command, capture_output=True, text=True, timeout=30, env=environment)
                    fails = case in ["direct-missing", "corrupt-first", "select-bad", "host-decoy"]
                    assert (result.returncode != 0) == fails, (arch, suite, case, result.returncode, result.stderr)
                    if fails:
                        assert result.returncode == (1 if case == "select-bad" else 127) and ("not found" in result.stderr or "cannot open shared object" in result.stderr or "file too short" in result.stderr), (result.returncode, result.stderr)
                    outcomes.append(dict(architecture=arch, suite=suite, case=case, exit_code=result.returncode, stderr=result.stderr,
                        expected_value=expected, loader_sha256=profile["loader_sha256"], app_sha256=hashlib.sha256((root / "app").read_bytes()).hexdigest(),
                        compiler=subprocess.check_output([cc, "-dumpfullversion"], text=True).strip(), compile_commands=compile_commands,
                        command=[p.replace(str(ROOT), "$PROJECT") for p in command], environment=environment | {"PATH": "$HOST_PATH"}))
                    print(arch, suite, case, result.returncode, flush=True)
                finally:
                    if helper.is_file():
                        helper.unlink()
    (ROOT / "fixtures/generated/paths/oracle.json").write_text(json.dumps(outcomes, indent=2) + "\n")
    print(f"Paths: {len(outcomes)} independent lookup/graph outcomes matched")


if __name__ == "__main__":
    build()
