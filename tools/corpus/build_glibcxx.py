"""Isolate real GLIBCXX requirements by replacing only the C++ runtime library."""
import hashlib
import json
import os
import shutil
import struct
import subprocess
import sys
from build_roots import ROOT, target_file, loader_command, capture
sys.path.insert(0, str(ROOT / "tools/oracle"))
from elf_mutations import tables
from build_linkage_edges import sysv_hash

GENERATED = ROOT / "fixtures/generated/glibcxx"


def remove_version(source):
    # Metadata-only negative control: keep GLIBCXX_3.4.33 but rename 3.4.32.
    data = bytearray(source)
    tags, offset = tables(data)
    strings, pos = offset(tags[5]), offset(tags[0x6ffffffc])
    replacement = b"_ZSt21ios_base_library_initv"
    replacement_offset = data.index(replacement + b"\0", strings, strings + tags[10]) - strings
    found = False
    for _ in range(tags[0x6ffffffd]):
        auxiliary = pos + struct.unpack_from("<I", data, pos + 12)[0]
        for j in range(struct.unpack_from("<H", data, pos + 6)[0]):
            start = strings + struct.unpack_from("<I", data, auxiliary)[0]
            end = data.index(0, start)
            if data[start:end] == b"GLIBCXX_3.4.32":
                # Redirect only version labels/parent labels. The pooled
                # dynsym name must stay unchanged so its GNU hash stays valid.
                struct.pack_into("<I", data, auxiliary, replacement_offset)
                if j == 0:
                    struct.pack_into("<I", data, pos + 8, sysv_hash(replacement))
                    found = True
            auxiliary += struct.unpack_from("<I", data, auxiliary + 4)[0]
        pos += struct.unpack_from("<I", data, pos + 16)[0]
    assert found and b"GLIBCXX_3.4.33\0" in data
    return data


def build():
    records = []
    for arch, machine, multiarch in [("amd64", 62, "x86_64-linux-gnu"), ("arm64", 183, "aarch64-linux-gnu")]:
        cc = "gcc" if machine == 62 else "aarch64-linux-gnu-gcc"
        interpreter = "/lib64/ld-linux-x86-64.so.2" if machine == 62 else "/lib/ld-linux-aarch64.so.1"
        noble = ROOT / ".tools/corpus/roots/noble" / arch
        original = target_file(noble, "/usr/lib/" + multiarch + "/libstdc++.so.6")
        programs = GENERATED / arch / "programs"
        programs.mkdir(parents=True, exist_ok=True)
        commands = []
        for name in ["modern", "stable"]:
            command = [cc, str(ROOT / "fixtures/src/glibcxx_probe.c"), "-Wl,-z,now", "-Wl,--allow-shlib-undefined",
                       *(["-DMODERN"] if name == "modern" else []), str(original), "-o", str(programs / name)]
            subprocess.run(command, check=True)
            commands.append([p.replace(str(ROOT), "$PROJECT") for p in command])
            reference = subprocess.check_output(["readelf", "-VW", "--dyn-syms", str(programs / name)], text=True)
            assert ("GLIBCXX_3.4.32" in reference) == (name == "modern")
            (programs / (name + ".readelf.txt")).write_text(reference)
        for case in ["baseline", "downgrade", "version-hole"]:
            folder = GENERATED / arch / case
            root = folder / "root"
            if root.is_symlink() or root.resolve() == GENERATED.resolve() or not root.resolve().is_relative_to(GENERATED.resolve()):
                raise ValueError("refusing cleanup outside generated GLIBCXX fixtures")
            if root.exists():
                shutil.rmtree(root)
            for directory in ["runtime", "app", interpreter.lstrip("/").rsplit("/", 1)[0]]:
                (root / directory).mkdir(parents=True, exist_ok=True)
            shutil.copy2(target_file(noble, interpreter), root / interpreter.lstrip("/"))
            for library in ["libc.so.6", "libm.so.6", "libgcc_s.so.1"]:
                shutil.copy2(target_file(noble, "/lib/" + multiarch + "/" + library), root / "runtime" / library)
            provider = root / "runtime/libstdc++.so.6"
            if case == "downgrade":
                source = ROOT / ".tools/corpus/roots/jammy" / arch
                shutil.copy2(target_file(source, "/usr/lib/" + multiarch + "/libstdc++.so.6"), provider)
            elif case == "version-hole":
                provider.write_bytes(remove_version(original.read_bytes()))
            else:
                shutil.copy2(original, provider)
            versions = subprocess.check_output(["readelf", "-VW", str(provider)], text=True)
            assert ("Name: GLIBCXX_3.4.32" in versions) == (case == "baseline")
            assert ("Name: GLIBCXX_3.4.33" in versions) == (case != "downgrade")
            (folder / "provider.readelf.txt").write_text(versions)
            for name in ["modern", "stable"]:
                shutil.copy2(programs / name, root / "app" / name)
            profile = dict(rule_revision="ubuntu-noble-2.39-0ubuntu8-v1", loader_family="glibc", machine=machine,
                loader_path_hex=interpreter.encode().hex(), loader_sha256=hashlib.sha256((root / interpreter.lstrip("/")).read_bytes()).hexdigest(),
                cwd_hex=b"/".hex(), default_dirs_hex=[], library_path_hex=[b"/runtime".hex()], cache_mode="disabled",
                hwcaps_policy="none", secure_execution=False, preload=[], audit=[])
            capture(root, profile, folder / "snapshot")
            helper = root / "qemu"
            if arch == "arm64":
                shutil.copy2(ROOT / ".tools/reference/qemu/usr/bin/qemu-aarch64-static", helper)
            try:
                for name in ["modern", "stable"]:
                    command = loader_command(root, arch, interpreter, ["/runtime"]) + ["/app/" + name]
                    result = subprocess.run(command, capture_output=True, text=True, timeout=30, env={"PATH": os.environ["PATH"], "LC_ALL": "C"})
                    missing = name == "modern" and case != "baseline"
                    assert result.returncode == (1 if missing else 0), (arch, case, name, result.returncode, result.stderr)
                    if missing:
                        assert "GLIBCXX_3.4.32" in result.stderr and "not found" in result.stderr
                    else:
                        assert result.stdout == "MoonLoadCheck GLIBCXX probe\n"
                    records.append(dict(architecture=arch, case=case, app=name, exit_code=result.returncode, stderr=result.stderr,
                        stdout=result.stdout, command=[p.replace(str(ROOT), "$PROJECT") for p in command], compile_commands=commands,
                        compiler=subprocess.check_output([cc, "-dumpfullversion"], text=True).strip(),
                        program_sha256=hashlib.sha256((programs / name).read_bytes()).hexdigest(),
                        provider_sha256=hashlib.sha256(provider.read_bytes()).hexdigest(), loader_sha256=profile["loader_sha256"]))
                    print(arch, case, name, result.returncode, flush=True)
            finally:
                if helper.is_file():
                    helper.unlink()
    (GENERATED / "oracle.json").write_text(json.dumps(records, indent=2) + "\n")
    print(f"GLIBCXX: {len(records)} isolated real-runtime outcomes")


if __name__ == "__main__":
    build()
