"""Resolve and test the actual published release without a local workspace override."""
from pathlib import Path, PurePosixPath
import argparse
import hashlib
import io
import json
import re
import shutil
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
import zipfile
from verify_archive import verify_cli

ROOT = Path(__file__).resolve().parents[1]


def run_json(args, cwd):
    attempts = 3 if args[1] == "view" else 1
    for attempt in range(attempts):
        result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=120)
        if result.returncode == 0:
            return json.loads(result.stdout)
        if attempt + 1 < attempts:
            print("Registry metadata query unsuccessful; retrying", flush=True)
            time.sleep(attempt + 1)
    result.check_returncode()


def download(url):
    for attempt in range(3):
        try:
            with urllib.request.urlopen(url, timeout=45) as response:
                return response.read(32 * 1024 * 1024 + 1)
        except (urllib.error.URLError, TimeoutError):
            if attempt == 2:
                raise
            print("Registry download interrupted; retrying", flush=True)
            time.sleep(attempt + 1)


def verify(backend, requested_version="0.1.0"):
    if not __debug__:
        raise RuntimeError("registry verification requires Python assertions; do not use -O")
    assert re.fullmatch(r"\d+\.\d+\.\d+", requested_version)
    lock = json.loads((ROOT / "tools/releases" / (requested_version + ".json")).read_text())
    module, version = lock["module"], lock["version"]
    assert version == requested_version
    extended = lock.get("consumer_profile") == "reports-0.2"
    assert module == "Xpeng/moonloadcheck" and re.fullmatch(r"\d+\.\d+\.\d+", version)
    assert lock["archive_url"] == f"https://download.mooncakes.io/user/{module}/{version}.zip"
    output = ROOT / "artifacts/registry" / version / backend.replace(",", "-")
    output.mkdir(parents=True, exist_ok=True)

    # Fetch public registry bytes independently. This ZIP is never extracted or
    # added as a local dependency: Moon itself must resolve the versioned import.
    data = download(lock["archive_url"])
    assert len(data) == lock["archive_bytes"]
    assert hashlib.sha256(data).hexdigest() == lock["archive_sha256"]
    (output / (version + ".zip")).write_bytes(data)

    consumer = Path(tempfile.mkdtemp(prefix="moonloadcheck-registry-"))
    assert not consumer.is_relative_to(ROOT)
    for parent in [consumer, *consumer.parents]:
        assert not any((parent / name).exists() for name in ["moon.work", "moon.work.json"]), parent
    (consumer / "moon.mod").write_text('name = "validation/registry_consumer"\nimport { "'
        + module + '@' + version + '", "moonbitlang/x@0.5.5", }\n')
    extra = '"Xpeng/moonloadcheck/analysis", ' if extended else ''
    (consumer / "moon.pkg").write_text('import { "Xpeng/moonloadcheck", ' + extra + '"moonbitlang/x/fs", } for "test"\n')
    template = (ROOT / "tools/archive_consumer.mbt.txt").read_text()
    (consumer / "consumer_test.mbt").write_text(template.replace("__VERSION__", version)
        .replace("archive consumer", "registry consumer"))
    if extended:
        (consumer / "impact_test.mbt").write_text((ROOT / "tools/impact_consumer.mbt.txt").read_text())
    for view in ["before", "after"]:
        # Explicit portable input data, not a module source or resolution override.
        shutil.copytree(ROOT / "fixtures/generated/u3/x86_64" / view / "snapshot", consumer / view)

    metadata = run_json(["moon", "view", module + "@" + version, "--json"], consumer)
    assert metadata["status"] == "success"
    release = metadata["result"]
    assert release["module"] == module and release["version"] == version and not release["yanked"]
    assert release["metadata"]["checksum"] == lock["archive_sha256"]
    assert release["metadata"]["license"] == lock["license"]
    assert release["metadata"]["repository"] == lock["repository"]
    print("Registry consumer (no workspace):", consumer, flush=True)
    subprocess.run(["moon", "update"], cwd=consumer, check=True, timeout=180)
    tree = run_json(["moon", "tree", "--json"], consumer)
    assert tree["status"] == "success"
    roots = tree["modules"]
    selected = [m for m in roots if m["name"] == module]
    assert len(selected) == 1
    assert selected[0]["version"] == version and selected[0]["source"]["kind"] == "registry"
    assert all(not m["workspace_member"] for m in roots)
    assert all(m["source"]["kind"] == "registry" or
               (m["name"] == "validation/registry_consumer" and
                Path(m["source"]["path"]).resolve() == consumer.resolve()) for m in roots)
    # tree resolves the graph but does not materialize .mooncakes. The normal
    # test command must perform that download and build, without local overrides.
    subprocess.run(["moon", "test", "--target", backend, "--deny-warn"],
                   cwd=consumer, check=True, timeout=600)
    installed = consumer / ".mooncakes" / module
    assert installed.is_dir() and not installed.is_symlink()
    assert installed.resolve().is_relative_to(consumer.resolve())

    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        names = [n for n in archive.namelist() if not n.endswith("/")]
        assert len(names) == lock["archive_files"] and len(set(names)) == len(names)
        assert {p.relative_to(installed).as_posix() for p in installed.rglob("*") if p.is_file()} == set(names)
        for name in names:
            path = PurePosixPath(name)
            assert not path.is_absolute() and ".." not in path.parts and "\\" not in name
            actual = installed / name
            assert actual.is_file() and not actual.is_symlink(), name
            assert actual.read_bytes() == archive.read(name), "resolved file differs: " + name
    cli_checks = 0
    if extended:
        # Build only a separate copy of the verified registry installation. It
        # never becomes a workspace override for the consumer's normal import.
        cli_source = Path(tempfile.mkdtemp(prefix="moonloadcheck-registry-cli-")) / "package"
        shutil.copytree(installed, cli_source)
        for parent in [cli_source, *cli_source.parents]:
            assert not any((parent / n).exists() for n in ["moon.work", "moon.work.json"])
        cli_checks = verify_cli(cli_source, consumer, backend, version, output)
    after = run_json(["moon", "tree", "--json"], consumer)
    assert after["status"] == "success"
    assert all(after[key] == tree[key] for key in ["root", "modules", "edges"])
    assert not (consumer / "moon.work").exists()
    record = dict(module=module, version=version, source_commit=lock["source_commit"],
        archive_sha256=lock["archive_sha256"], verified_installed_files=len(names),
        dependency_source="registry", workspace_override=False,
        original_repository_dependency=False, backends=backend.split(","),
        consumer_tests_per_backend=4 if extended else 3, cli_checks=cli_checks,
        cli_source="verified registry installation copy" if extended else None,
        isolated_root=str(consumer),
        input_manifests={v: hashlib.sha256((consumer / v / "manifest.json").read_bytes()).hexdigest()
                         for v in ["before", "after"]})
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    (output / "tree.json").write_text(json.dumps(tree, indent=2) + "\n")
    (output / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"Published registry consumer: {record['consumer_tests_per_backend']} tests/backend and {cli_checks} CLI checks passed ({backend}); {len(names)} resolved files match the pinned registry ZIP")
    print("Published archive SHA-256:", lock["archive_sha256"])


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", choices=["native", "js", "js,native"], default="native")
    parser.add_argument("--version", default="0.1.0", help="Exact published version with tools/releases/VERSION.json")
    args = parser.parse_args()
    verify(args.target, args.version)
