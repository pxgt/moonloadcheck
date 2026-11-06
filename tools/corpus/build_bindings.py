"""Real loader observations for excluded bindings and TLS type collisions."""
import hashlib
import json
import os
import shutil
import subprocess
from build_roots import ROOT, target_file, loader_command, capture
from build_linkage_edges import layout, target_environment

GENERATED = ROOT / "fixtures/generated/bindings"
CASES = ["interposition", "protected", "symbolic", "unique", "tls", "tls-missing", "tls-type-first", "ordinary-to-tls"]


def build():
    outcomes = []
    for arch, machine, multiarch in [("amd64", 62, "x86_64-linux-gnu"), ("arm64", 183, "aarch64-linux-gnu")]:
        cc = "gcc" if machine == 62 else "aarch64-linux-gnu-gcc"
        interpreter = "/lib64/ld-linux-x86-64.so.2" if machine == 62 else "/lib/ld-linux-aarch64.so.1"
        for suite in ["jammy", "noble"]:
            for case in CASES:
                folder = GENERATED / arch / suite / case
                root = folder / "root"
                if root.is_symlink() or root.resolve() == GENERATED.resolve() or not root.resolve().is_relative_to(GENERATED.resolve()):
                    raise ValueError("refusing cleanup outside generated binding fixtures")
                if root.exists():
                    shutil.rmtree(root)
                for directory in ["runtime", interpreter.lstrip("/").rsplit("/", 1)[0]]:
                    (root / directory).mkdir(parents=True, exist_ok=True)
                runtime, commands = root / "runtime", []

                def run(command):
                    commands.append([str(p).replace(str(ROOT), "$PROJECT") for p in command])
                    subprocess.run(command, check=True)

                def library(name, flags):
                    path = runtime / name
                    run([cc, "-shared", "-fPIC", str(ROOT / "fixtures/src/special_binding.c"),
                         "-Wl,--hash-style=sysv", "-Wl,-soname," + name, *flags, "-o", str(path)])
                    return path

                tls = case.startswith("tls")
                provider = library("libprovider.so.1", ["-DTLS"] if tls else ["-DPROTECTED"] if case == "protected" else [])
                links = []
                if case in ["interposition", "symbolic", "tls-type-first"]:
                    first = library("libfirst.so.1", ["-DVALUE=9", *(["-DTLS"] if tls else [])])
                    links = [str(first)]
                self_flags = ["-DSELF", "-Wl,-Bsymbolic"] if case == "symbolic" else ["-DCLIENT", *(["-DTLS"] if tls else []), str(provider)]
                client = library("libclient.so.1", self_flags)
                links += [str(client), str(provider)]
                expected = 9 if case in ["interposition", "tls-type-first"] else 7
                run([cc, str(ROOT / "fixtures/src/graph_app.c"), "-fPIC", "-Wl,-z,now", "-Wl,--no-as-needed",
                     "-Wl,-rpath-link," + str(runtime), "-DEXPECTED=" + str(expected), *links, "-o", str(root / "app")])
                if case == "tls-missing":
                    library("libprovider.so.1", ["-DTLS", "-DNAME=lost"])
                elif case == "tls-type-first":
                    library("libfirst.so.1", ["-DVALUE=9"])
                elif case == "ordinary-to-tls":
                    library("libprovider.so.1", ["-DTLS"])
                elif case == "unique":
                    data = bytearray(provider.read_bytes())
                    _, _, symbols, _, _, _, count, name = layout(data)
                    index = next(i for i in range(count) if name(i) == b"slot")
                    assert data[symbols + index * 24 + 4] == 0x11
                    data[symbols + index * 24 + 4] = 0xa1  # STB_GNU_UNIQUE, STT_OBJECT.
                    data[7] = 3  # GNU OS ABI, as emitted for GNU-unique symbols.
                    provider.write_bytes(data)
                source = ROOT / ".tools/corpus/roots" / suite / arch
                shutil.copy2(target_file(source, interpreter), root / interpreter.lstrip("/"))
                shutil.copy2(target_file(source, "/lib/" + multiarch + "/libc.so.6"), runtime / "libc.so.6")
                references = {}
                for path in [root / "app", client, provider] + ([runtime / "libfirst.so.1"] if links[0].endswith("libfirst.so.1") else []):
                    listing = subprocess.check_output(["readelf", "-dW", "-rW", "--dyn-syms", str(path)], text=True)
                    (folder / (path.name + ".readelf.txt")).write_text(listing)
                    references[path.name] = hashlib.sha256(path.read_bytes()).hexdigest()
                    if case == "unique" and path == provider:
                        assert "UNIQUE" in listing
                    if case == "protected" and path == provider:
                        assert "PROTECTED" in listing
                    if case == "symbolic" and path == client:
                        assert "SYMBOLIC" in listing
                    if tls and path == client:
                        assert ("DTPMOD64" in listing if machine == 62 else "TLSDESC" in listing)
                profile = dict(rule_revision="glibc-2.35-controlled-v2" if suite == "jammy" else "ubuntu-noble-2.39-0ubuntu8-v1",
                    loader_family="glibc", machine=machine, loader_path_hex=interpreter.encode().hex(),
                    loader_sha256=hashlib.sha256((root / interpreter.lstrip("/")).read_bytes()).hexdigest(),
                    cwd_hex=b"/".hex(), default_dirs_hex=[], library_path_hex=[b"/runtime".hex()], cache_mode="disabled",
                    hwcaps_policy="none", secure_execution=False, preload=[], audit=[])
                capture(root, profile, folder / "snapshot")
                helper = root / "qemu"
                if arch == "arm64":
                    shutil.copy2(ROOT / ".tools/reference/qemu/usr/bin/qemu-aarch64-static", helper)
                try:
                    extra = {"LD_DEBUG": "bindings"} if case in ["tls-type-first", "ordinary-to-tls"] else {}
                    command = target_environment(loader_command(root, arch, interpreter, ["/runtime"]) + ["/app"], extra)
                    # Prevent core dumps from deliberately inconsistent type fixtures.
                    def no_core():
                        import resource
                        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
                    result = subprocess.run(command, capture_output=True, text=True, timeout=30, preexec_fn=no_core,
                        env={"PATH": os.environ["PATH"], "LC_ALL": "C", **extra})
                    binding_lines = [line.strip() for line in result.stderr.splitlines()
                                     if "binding file /runtime/libclient.so.1" in line and ("`slot'" in line or "'slot'" in line)]
                    if extra:
                        (folder / "loader-bindings.txt").write_text(result.stderr)
                        expected_provider = "libfirst.so.1" if case == "tls-type-first" else "libprovider.so.1"
                        assert any("to /runtime/" + expected_provider in line for line in binding_lines), (case, binding_lines)
                    if case == "tls-missing":
                        assert result.returncode == 127 and "undefined symbol: slot" in result.stderr
                    elif case not in ["tls-type-first", "ordinary-to-tls"]:
                        assert result.returncode == 0, (arch, suite, case, result.returncode, result.stderr)
                    else:
                        assert result.returncode != 0, (arch, suite, case, "type collision unexpectedly succeeded")
                    outcomes.append(dict(architecture=arch, suite=suite, case=case, exit_code=result.returncode,
                        stderr=result.stderr if not extra else "\n".join(binding_lines), binding_lines=binding_lines,
                        command=[p.replace(str(ROOT), "$PROJECT") for p in command], compile_commands=commands,
                        compiler=subprocess.check_output([cc, "-dumpfullversion"], text=True).strip(),
                        objects=references, loader_sha256=profile["loader_sha256"]))
                    print(arch, suite, case, result.returncode, "; ".join(binding_lines), flush=True)
                finally:
                    if helper.is_file():
                        helper.unlink()
    (GENERATED / "oracle.json").write_text(json.dumps(outcomes, indent=2) + "\n")
    print(f"Bindings: {len(outcomes)} actual loader observations")


if __name__ == "__main__":
    build()
