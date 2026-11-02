"""Independent loader and readelf evidence for byte names and lookup boundaries."""
from pathlib import Path
import hashlib
import json
import os
import re
import shutil
import struct
import subprocess
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "oracle"))
from elf_mutations import tables
from build_roots import ROOT, target_file, loader_command, capture

CASES = ["baseline-pie", "baseline-exec", "raw-name", "raw-mismatch", "unused-undefined", "version-index",
         "local-first", "internal-first", "hidden-first", "ifunc-good", "ifunc-wrong-value",
         "lazy-missing", "unknown-symbol", "unknown-free", "relative-none"]
NOT_EXECUTED = {"unknown-symbol", "unknown-free", "relative-none"}


def target_environment(command, values):
    # sudo clears LD_* before chroot starts. Assign the explicit target switches
    # after that boundary instead of relying on the invoker's environment.
    if values and command[0] == "sudo":
        return ["sudo", "env", *[key + "=" + value for key, value in values.items()], *command[1:]]
    return command


def layout(data):
    tags, offset = tables(data)
    syms, strings, hashpos = offset(tags[6]), offset(tags[5]), offset(tags[4])
    buckets, count = struct.unpack_from("<II", data, hashpos)
    def name(index):
        start = strings + struct.unpack_from("<I", data, syms + index * 24)[0]
        return bytes(data[start:data.index(0, start)])
    return tags, offset, syms, strings, hashpos, buckets, count, name


def sysv_hash(name):
    value = 0
    for byte in name:
        value = (value << 4) + byte
        high = value & 0xf0000000
        value ^= high >> 24
        value &= ~high
    return value


def rehash(data):
    _, _, _, _, pos, buckets, count, name = layout(data)
    chains = [[] for _ in range(buckets)]
    for i in range(1, count):
        chains[sysv_hash(name(i)) % buckets].append(i)
    data[pos + 8:pos + 8 + (buckets + count) * 4] = bytes((buckets + count) * 4)
    for bucket, chain in enumerate(chains):
        if chain:
            struct.pack_into("<I", data, pos + 8 + bucket * 4, chain[0])
            for left, right in zip(chain, chain[1:] + [0]):
                struct.pack_into("<I", data, pos + 8 + (buckets + left) * 4, right)


def rename(data, old, new):
    _, _, syms, strings, _, _, count, name = layout(data)
    indices = [i for i in range(count) if name(i) == old]
    assert indices and len(new) <= len(old)
    for i in indices:
        start = strings + struct.unpack_from("<I", data, syms + i * 24)[0]
        data[start:start + len(old)] = new + bytes(len(old) - len(new))
    rehash(data)
    return indices


def relocs(data):
    tags, offset = tables(data)
    for address, size in [(7, 8), (23, 2)]:
        if address in tags:
            for pos in range(offset(tags[address]), offset(tags[address]) + tags[size], 24):
                info = struct.unpack_from("<Q", data, pos + 8)[0]
                yield pos, info >> 32, info & 0xffffffff


def readelf_object(path):
    output = subprocess.check_output(["readelf", "-hW", "-lW", "-dW", str(path)], env={**os.environ, "LC_ALL": "C"}).decode()
    def value(tag):
        found = re.findall(r"\(" + tag + r"\).*?\[([^\]]*)\]", output)
        return found[0] if found else None
    machine = re.search(r"^\s*Machine:\s*(.*)$", output, re.M).group(1)
    kind = re.search(r"^\s*Type:\s*(\w+)", output, re.M).group(1)
    interp = re.search(r"Requesting program interpreter: ([^\]]+)\]", output)
    flags = re.findall(r"\(FLAGS_1\)\s+Flags:\s*(.*)", output)
    fields = dict(path=path.relative_to(ROOT).as_posix(), machine={"Advanced Micro Devices X86-64": 62, "AArch64": 183}[machine],
        object_type={"EXEC": 2, "DYN": 3}[kind], interpreter=interp.group(1) if interp else None,
        needed=re.findall(r"\(NEEDED\).*?\[([^\]]*)\]", output), soname=value("SONAME"), rpath=value("RPATH"), runpath=value("RUNPATH"),
        pie=any("PIE" in f.split() for f in flags), no_default_lib=any("NODEFLIB" in f.split() for f in flags))
    return {key: value for key, value in fields.items() if value is not None}, output


def build():
    outcomes, objects, executions = [], [], 0
    generated = ROOT / "fixtures/generated/linkage-edges"
    for arch, machine, multiarch in [("amd64", 62, "x86_64-linux-gnu"), ("arm64", 183, "aarch64-linux-gnu")]:
        cc = "gcc" if machine == 62 else "aarch64-linux-gnu-gcc"
        interpreter = "/lib64/ld-linux-x86-64.so.2" if machine == 62 else "/lib/ld-linux-aarch64.so.1"
        for suite in ["jammy", "noble"]:
            for case in CASES:
                folder = generated / arch / suite / case
                root, runtime = folder / "root", folder / "root/runtime"
                if root.is_symlink() or root.resolve() == generated.resolve() or not root.resolve().is_relative_to(generated.resolve()):
                    raise ValueError("refusing cleanup outside generated linkage fixtures")
                if root.exists():
                    shutil.rmtree(root)
                runtime.mkdir(parents=True)
                (root / interpreter.lstrip("/")).parent.mkdir(parents=True, exist_ok=True)
                commands = []
                def run(command):
                    commands.append([str(p).replace(str(ROOT), "$PROJECT") for p in command])
                    subprocess.run(command, check=True)
                library = runtime / "libedge.so.1"
                flags, links = [], ["-l:libedge.so.1"]
                source = "ifunc_edge.c" if case.startswith("ifunc-") else "binding.c"
                if case == "version-index":
                    script = folder / "versions.map"
                    script.write_text("EDGE_1 { global: api; local: *; };\n")
                    flags = ["-Wl,--version-script=" + str(script)]
                run([cc, "-shared", "-fPIC", str(ROOT / "fixtures/src" / source), "-Wl,--hash-style=sysv",
                     "-Wl,-soname,libedge.so.1", *flags, "-DVALUE=" + ("9" if case == "ifunc-wrong-value" else "7"), "-o", str(library)])
                appflags = ["-Wl,-z,now", "-Wl,-rpath,$ORIGIN/runtime"]
                if case == "baseline-exec":
                    appflags += ["-no-pie", "-Wl,-z,nodefaultlib", "-Wl,--disable-new-dtags"]
                if case == "lazy-missing":
                    appflags = ["-Wl,-z,lazy", "-DLAZY_CALL"]
                if case.endswith("-first"):
                    run([cc, "-shared", "-fPIC", str(ROOT / "fixtures/src/binding.c"), "-DVALUE=9",
                         "-Wl,--hash-style=sysv", "-Wl,-soname,libsecond.so.1", "-o", str(runtime / "libsecond.so.1")])
                    links += ["-l:libsecond.so.1"]
                    appflags += ["-DEXPECTED=9"]
                run([cc, str(ROOT / "fixtures/src/linkage_edge_app.c"), "-Wl,--hash-style=sysv", "-Wl,--no-as-needed",
                     "-L" + str(runtime), *appflags, *links, "-o", str(root / "app")])
                app, lib = bytearray((root / "app").read_bytes()), bytearray(library.read_bytes())
                if case in ["raw-name", "raw-mismatch"]:
                    rename(app, b"api", b"a\xffi")
                    rename(lib, b"api", b"a\xffi" if case == "raw-name" else b"a\xfei")
                if case == "unused-undefined":
                    index = rename(app, b"_ITM_deregisterTMCloneTable", b"absent_strong_unused")[0]
                    tags, offset, symbols, *_ = layout(app)
                    app[symbols + 24 * index + 4] = 0x10  # STB_GLOBAL, STT_NOTYPE, SHN_UNDEF.
                    for pos, symbol, _ in list(relocs(app)):
                        if symbol == index:
                            struct.pack_into("<Q", app, pos + 8, 0)  # R_*_NONE, no requested symbol.
                if case == "version-index":
                    tags, offset, _, _, _, _, count, _ = layout(lib)
                    pos = offset(tags[0x6ffffffc])
                    for _ in range(tags[0x6ffffffd]):
                        if struct.unpack_from("<H", lib, pos + 4)[0] == 2:
                            struct.pack_into("<H", lib, pos + 4, 17)
                        pos += struct.unpack_from("<I", lib, pos + 16)[0]
                    versions = offset(tags[0x6ffffff0])
                    for i in range(count):
                        value = struct.unpack_from("<H", lib, versions + i * 2)[0]
                        if value & 0x7fff == 2:
                            struct.pack_into("<H", lib, versions + i * 2, (value & 0x8000) | 17)
                if case.endswith("-first"):
                    _, _, symbols, _, _, _, count, name = layout(lib)
                    index = next(i for i in range(count) if name(i) == b"api")
                    if case == "local-first":
                        lib[symbols + 24 * index + 4] &= 15
                    else:
                        lib[symbols + 24 * index + 5] = 1 if case == "internal-first" else 2
                if case == "lazy-missing":
                    rename(lib, b"api", b"zzz")
                if case in NOT_EXECUTED:
                    _, _, _, _, _, _, _, name = layout(app)
                    relative = 8 if machine == 62 else 1027
                    if case == "unknown-symbol":
                        pos, symbol, _ = next((p, s, k) for p, s, k in relocs(app) if s and name(s) == b"api")
                    else:
                        pos, symbol, _ = next((p, s, k) for p, s, k in relocs(app) if s == 0 and k == relative)
                    struct.pack_into("<Q", app, pos + 8, (symbol << 32) | (0 if case == "relative-none" else 0x1234))
                (root / "app").write_bytes(app)
                library.write_bytes(lib)
                for path in [root / "app", library]:
                    reference, output = readelf_object(path)
                    objects.append(reference)
                    (folder / (path.name + ".readelf.txt")).write_text(output)
                source = ROOT / ".tools/corpus/roots" / suite / arch
                shutil.copy2(target_file(source, interpreter), root / interpreter.lstrip("/"))
                shutil.copy2(target_file(source, "/lib/" + multiarch + "/libc.so.6"), runtime / "libc.so.6")
                profile = dict(rule_revision="glibc-2.35-controlled-v2" if suite == "jammy" else "ubuntu-noble-2.39-0ubuntu8-v1",
                    loader_family="glibc", machine=machine, loader_path_hex=interpreter.encode().hex(),
                    loader_sha256=hashlib.sha256((root / interpreter.lstrip("/")).read_bytes()).hexdigest(), cwd_hex=b"/".hex(),
                    default_dirs_hex=[], library_path_hex=[b"/runtime".hex()], cache_mode="disabled", hwcaps_policy="none",
                    secure_execution=False, preload=[], audit=[])
                capture(root, profile, folder / "snapshot")
                observations = []
                if case not in NOT_EXECUTED:
                    helper = root / "qemu"
                    if arch == "arm64":
                        shutil.copy2(ROOT / ".tools/reference/qemu/usr/bin/qemu-aarch64-static", helper)
                    try:
                        expected = 41 if case == "ifunc-wrong-value" else 127 if case == "raw-mismatch" else 0
                        runs = [([], {}, expected)]
                        if case == "lazy-missing":
                            runs += [(["call"], {}, 127), ([], {"LD_BIND_NOW": "1"}, 127)]
                        for args, extra, expected in runs:
                            environment = {"PATH": os.environ["PATH"], "LC_ALL": "C", **extra}
                            command = target_environment(loader_command(root, arch, interpreter, ["/runtime"]) + ["/app", *args], extra)
                            result = subprocess.run(command, capture_output=True, timeout=30, env=environment)
                            assert result.returncode == expected, (arch, suite, case, args, extra, result.returncode, result.stderr)
                            if expected == 127:
                                assert (b"undefined symbol: a\xffi" if case == "raw-mismatch" else b"undefined symbol: api") in result.stderr
                            observations.append(dict(command=[p.replace(str(ROOT), "$PROJECT") for p in command],
                                environment={**environment, "PATH": "$HOST_PATH"}, exit_code=result.returncode,
                                stderr=result.stderr.decode(errors="replace")))
                            executions += 1
                    finally:
                        if helper.is_file():
                            helper.unlink()
                outcomes.append(dict(architecture=arch, suite=suite, case=case, executions=observations,
                    compiler=subprocess.check_output([cc, "-dumpfullversion"], text=True).strip(), compile_commands=commands,
                    app_sha256=hashlib.sha256(app).hexdigest(), library_sha256=hashlib.sha256(lib).hexdigest(), loader_sha256=profile["loader_sha256"]))
                print(arch, suite, case, [r["exit_code"] for r in observations], flush=True)
    (generated / "oracle.json").write_text(json.dumps(outcomes, indent=2) + "\n")
    (generated / "readelf-objects.json").write_text(json.dumps(objects, indent=2) + "\n")
    print(f"Linkage edges: {executions} actual executions, {len(outcomes)} snapshots, {len(objects)} readelf object comparisons")


if __name__ == "__main__":
    build()
