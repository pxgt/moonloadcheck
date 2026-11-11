"""Audit and consume the packaged ZIP in an isolated workspace; never publish it."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import json
import re
import shutil
import stat
import subprocess
import tempfile
import zipfile

from verify_reports import Page

ROOT = Path(__file__).resolve().parents[1]


def metadata(text):
    return {key: re.search(r'^' + key + r'\s*=\s*"([^"]+)"', text, re.M).group(1)
            for key in ["name", "version", "license", "repository"]}


def audit(archive):
    if not __debug__:
        raise RuntimeError("archive verification requires Python assertions; do not use -O")
    expected = metadata((ROOT / "moon.mod").read_text())
    with zipfile.ZipFile(archive) as package:
        entries = package.infolist()
        assert 0 < len(entries) <= 2000 and sum(e.file_size for e in entries) <= 32 * 1024 * 1024
        seen = set()
        for entry in entries:
            name = entry.filename
            path = PurePosixPath(name)
            key = str(path).casefold()
            assert key not in seen and not path.is_absolute() and ".." not in path.parts, name
            assert "\\" not in name and ":" not in name and str(path) == name.rstrip("/"), name
            assert not stat.S_ISLNK(entry.external_attr >> 16), name
            assert not any(p in path.parts for p in [".git", ".tools", ".mooncakes", "_build", "artifacts", "__pycache__", "target"]), name
            assert not name.startswith("fixtures/generated/"), name
            assert path.suffix not in [".deb", ".zip", ".exe", ".wasm", ".pyc"], name
            seen.add(key)
        actual = metadata(package.read("moon.mod").decode())
        assert actual == expected, (actual, expected)
        assert actual["name"] == "Xpeng/moonloadcheck" and actual["license"] == "Apache-2.0"
        for name in ["LICENSE", "THIRD_PARTY.md", "internal/elf_vendor/UPSTREAM.json"]:
            assert package.read(name) == (ROOT / name).read_bytes(), name
        lock = json.loads(package.read("internal/elf_vendor/UPSTREAM.json"))
        for name, digest in lock["files"].items():
            assert hashlib.sha256(package.read("internal/elf_vendor/" + name)).hexdigest() == digest, name
        for entry in entries:
            if not entry.is_dir():
                payload = package.read(entry)
                assert not payload[:4].startswith((b"\x7fELF", b"MZ")), entry.filename
                original = ROOT / entry.filename
                assert original.is_file() and not original.is_symlink(), entry.filename
                assert payload == original.read_bytes(), "archive differs from source: " + entry.filename
        return dict(metadata=actual, files=len(entries), uncompressed_bytes=sum(e.file_size for e in entries),
                    archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                    vendor_files_verified=len(lock["files"]))


def verify(archive, backend):
    archive = archive.resolve()
    record = audit(archive)
    version = record["metadata"]["version"]
    assert re.fullmatch(r"\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?", version)
    # Unique sibling roots prevent fallback to the original project or its build cache.
    work = Path(tempfile.mkdtemp(prefix="moonloadcheck-archive-"))
    extracted, consumer = work / "package", work / "consumer"
    extracted.mkdir()
    consumer.mkdir()
    with zipfile.ZipFile(archive) as package:
        package.extractall(extracted)  # All names/types/total size were validated above.
    for view in ["before", "after"]:
        source = ROOT / "fixtures/generated/u3/x86_64" / view / "snapshot"
        shutil.copytree(source, consumer / view)
    record["input_manifests"] = {v: hashlib.sha256((consumer / v / "manifest.json").read_bytes()).hexdigest()
                                 for v in ["before", "after"]}
    (consumer / "moon.mod").write_text('name = "validation/archive_consumer"\nimport { "Xpeng/moonloadcheck@'
        + version + '", "moonbitlang/x@0.5.5", }\n')
    (consumer / "moon.pkg").write_text('import { "Xpeng/moonloadcheck", "Xpeng/moonloadcheck/analysis", "moonbitlang/x/fs", } for "test"\n')
    template = (ROOT / "tools/archive_consumer.mbt.txt").read_text()
    (consumer / "consumer_test.mbt").write_text(template.replace("__VERSION__", version))
    (consumer / "impact_test.mbt").write_text((ROOT / "tools/impact_consumer.mbt.txt").read_text())
    (consumer / "moon.work").write_text("members = " + json.dumps([".", str(extracted)]) + "\n")
    assert ROOT not in [consumer, extracted] and not extracted.is_relative_to(ROOT)
    print("Archive audited; isolated package/consumer:", work, flush=True)
    subprocess.run(["moon", "test", "--package", "validation/archive_consumer", "--target", backend, "--deny-warn"],
                   cwd=consumer, check=True, timeout=600)
    output = ROOT / "artifacts/archive"
    checks = verify_cli(extracted, consumer, backend, version, output)
    record.update(backends=backend.split(","), consumer_tests_per_backend=4, cli_checks=checks,
                  original_workspace_member=False, published_registry_consumer=False,
                  isolated_root=str(work))
    (output / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"Archive consumer: 4 tests/backend and {checks} CLI checks passed; no original workspace member")
    print(f"Archive SHA-256: {record['archive_sha256']}; version {version}; {record['files']} entries")


def verify_cli(extracted, consumer, backend, version, output):
    """Build and exercise a byte-verified package, independent of its source repo."""
    subprocess.run(["moon", "build", "--target", backend], cwd=extracted, check=True, timeout=600)
    commands = []
    if "js" in backend.split(","):
        commands.append(("js", ["node", str(extracted / "_build/js/debug/build/cmd/main/main.js")]))
    if "native" in backend.split(","):
        commands.append(("native", [str(extracted / "_build/native/debug/build/cmd/main/main.exe")]))
    entries = consumer / "entries.json"
    entries.write_text('["/opt/demo/app","/opt/demo/stable-app"]')
    output.mkdir(parents=True, exist_ok=True)
    checks = 0

    def invoke(label, args, expected, help_text=False, html_page=False):
        nonlocal checks
        results = []
        for name, command in commands:
            result = subprocess.run(command + list(map(str, args)), cwd=consumer,
                                    capture_output=True, text=True, timeout=60)
            assert result.returncode == expected and not result.stderr, (label, name, result.returncode, result.stdout, result.stderr)
            report = result.stdout if help_text or html_page else json.loads(result.stdout)
            if help_text:
                assert report.startswith("usage:")
            elif html_page:
                assert report.startswith("<!doctype html>")
                Page(report)
            elif "tool_version" in report:
                assert report["tool_version"] == version
            # explain succeeds when it returns a finding, even when that finding
            # describes a failure. Its status is not the command's verdict.
            if not help_text and not html_page and label != "explain" and "status" in report:
                assert report["status"] == ["pass_static", "fail", "inconclusive", "input_error"][expected]
            results.append(report)
            checks += 1
        assert all(r == results[0] for r in results), label
        if html_page:
            (output / (label + ".html")).write_text(results[0], encoding="utf-8")
        elif not help_text:
            (output / (label + ".json")).write_text(json.dumps(results[0], indent=2) + "\n")
        return results[0]

    def check(view, scope, expected):
        return invoke(view + "-" + scope, ["check", "--snapshot", consumer / view,
            "--entry", "/opt/demo/app", "--scope", scope, "--format", "json"], expected)
    check("before", "compatibility", 0)
    after = check("after", "compatibility", 1)
    check("after", "dependencies", 0)
    diff = invoke("diff", ["diff", "--before", consumer / "before", "--after", consumer / "after",
                          "--entries", entries, "--format", "json"], 1)
    assert diff["entries"][0]["changes"][0]["classification"] == "introduced"
    assert diff["entries"][1]["after"]["status"] == "pass_static"
    saved = consumer / "saved.json"
    saved.write_text(json.dumps(after))
    finding = after["findings"][0]
    assert invoke("explain", ["explain", "--report", saved, "--finding", finding["id"]], 0) == finding
    invoke("help", ["--help"], 0, help_text=True)
    error = invoke("invalid", ["invalid-command"], 3)
    assert error["error_kind"] == "arguments"
    for label, value in [("saved-check", after), ("saved-comparison", diff)]:
        source = consumer / (label + ".json")
        source.write_text(json.dumps(value), encoding="utf-8")
        brief = invoke(label + "-summary", ["report", "--input", source, "--format", "summary"], 1)
        assert brief["status"] == "fail" and brief["exit_code"] == 1
        page = invoke(label + "-html", ["report", "--input", source, "--format", "html"], 1, html_page=True)
        expected = [after] if label == "saved-check" else [r for e in diff["entries"] for r in [e["before"], e["after"]]]
        assert Page(page).evidence == expected
    # New source candidates exercise the matrix command too. Immutable 0.2.0
    # registry CLI verification keeps its original command surface.
    if (extracted / "internal/presentation/matrix.mbt").is_file():
        source = consumer / "matrix.json"
        source.write_text(json.dumps(dict(schema_version=1, kind="deployment_matrix", targets=[
            dict(id="candidate", config_sha256="a" * 64, entries=["/opt/demo/app"], reports=[after])])), encoding="utf-8")
        brief = invoke("matrix-summary", ["matrix-report", "--input", source, "--format", "summary"], 1)
        assert brief["check_count"] == 1 and brief["status"] == "fail"
        page = invoke("matrix-html", ["matrix-report", "--input", source, "--format", "html"], 1, html_page=True)
        assert Page(page).evidence == [after]
    return checks


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    version = metadata((ROOT / "moon.mod").read_text())["version"]
    parser.add_argument("--archive", type=Path, default=ROOT / f"_build/publish/Xpeng-moonloadcheck-{version}.zip")
    parser.add_argument("--target", choices=["js", "native", "js,native"], default="native")
    args = parser.parse_args()
    verify(args.archive, args.target)
