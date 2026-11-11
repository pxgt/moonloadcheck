"""Capture an explicitly configured Linux deployment and run the MoonBit CLI.

This adapter only translates UTF-8 configuration and orchestrates I/O. All
dependency/symbol/version decisions remain in MoonLoadCheck. Target programs
are never executed. Exit codes: 0 pass, 1 failure, 2 inconclusive, 3 input error.
"""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys

from capture_snapshot import capture

STATUSES = {0: "pass_static", 1: "fail", 2: "inconclusive", 3: "input_error"}
MAX_JSON = 4 * 1024 * 1024


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON field: " + key)
        result[key] = value
    return result


def read_json(path):
    with path.open("rb") as stream:
        data = stream.read(MAX_JSON + 1)
    if len(data) > MAX_JSON:
        raise ValueError("JSON input exceeds 4 MiB: " + str(path))
    return json.loads(data.decode("utf-8"), object_pairs_hook=unique_object)


def fields(value, required, optional=(), label="configuration"):
    if not isinstance(value, dict):
        raise ValueError(label + " must be an object")
    missing = set(required) - value.keys()
    extra = value.keys() - set(required) - set(optional)
    if missing or extra:
        raise ValueError(f"{label}: missing {sorted(missing)}, unknown {sorted(extra)}")


def string(value, label, empty=False, absolute=False):
    if not isinstance(value, str) or "\0" in value or (not empty and not value):
        raise ValueError(label + " must be a " + ("possibly empty " if empty else "nonempty ") + "string without NUL")
    value.encode("utf-8", errors="strict")
    if absolute and not value.startswith("/"):
        raise ValueError(label + " must be an absolute Linux path")
    return value


def strings(value, label, empty=False):
    if not isinstance(value, list):
        raise ValueError(label + " must be an explicit array; use [] for known empty")
    return [string(item, label, empty=empty) for item in value]


def convert_profile(value):
    plain = ["rule_revision", "loader_family", "loader_sha256", "cache_mode", "hwcaps_policy"]
    paths = ["loader_path", "cwd"]
    lists = ["default_dirs", "library_path"]
    fields(value, plain + paths + lists + ["machine", "secure_execution", "preload", "audit"],
           ["lib_token", "platform_token"], "profile")
    profile = {key: string(value[key], "profile." + key) for key in plain}
    if not re.fullmatch(r"[0-9a-f]{64}", profile["loader_sha256"]):
        raise ValueError("profile.loader_sha256 must be the expected target loader's lowercase SHA-256")
    if type(value["machine"]) is not int or not 0 < value["machine"] < 65536:
        raise ValueError("profile.machine must be an ELF machine integer, not a boolean")
    if type(value["secure_execution"]) is not bool:
        raise ValueError("profile.secure_execution must be an explicit boolean")
    profile.update(machine=value["machine"], secure_execution=value["secure_execution"])
    for key in paths:
        profile[key + "_hex"] = string(value[key], "profile." + key, absolute=True).encode().hex()
    for key in lists:
        profile[key + "_hex"] = [item.encode().hex() for item in strings(value[key], "profile." + key, empty=True)]
    for key in ["preload", "audit"]:
        profile[key] = strings(value[key], "profile." + key)
    for key in ["lib_token", "platform_token"]:
        if key in value:
            profile[key + "_hex"] = string(value[key], "profile." + key).encode().hex()
    return profile


def load_config(path):
    config = read_json(path)
    fields(config, ["schema_version", "root", "entries", "scope", "profile"])
    if type(config["schema_version"]) is not int or config["schema_version"] != 1:
        raise ValueError("configuration schema_version must be 1")
    root = (path.parent / string(config["root"], "root")).resolve(strict=True)
    if not root.is_dir():
        raise ValueError("root must name a staged directory")
    entries = strings(config["entries"], "entries")
    if not 1 <= len(entries) <= 128 or len(set(entries)) != len(entries):
        raise ValueError("entries must contain 1..128 distinct program paths")
    for entry in entries:
        string(entry, "entry", absolute=True)
    if config["scope"] not in ["dependencies", "compatibility"]:
        raise ValueError("scope must be dependencies or compatibility")
    return config, root, entries, convert_profile(config["profile"])


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")


def run(config_path, out, command):
    if sys.platform != "linux":
        raise ValueError("deployment capture requires Linux; use the CLI directly for existing portable snapshots")
    config_path = config_path.resolve(strict=True)
    config, root, entries, profile = load_config(config_path)
    out = out.resolve()
    if out == root or root in out.parents:
        raise ValueError("output must be outside the staged root")
    # A run owns a new directory. Never reuse stale blobs/reports or overwrite a
    # prior successful result when capture or analysis fails halfway through.
    out.mkdir(parents=True, exist_ok=False)
    summary = dict(schema_version=1, kind="deployment_check", status="input_error", exit_code=3,
                   scope=config["scope"], reports=[], output=str(out))
    try:
        write_json(out / "profile.json", profile)
        capture(root, profile, out / "snapshot")
        summary["snapshot_sha256"] = hashlib.sha256((out / "snapshot/manifest.json").read_bytes()).hexdigest()
        exits = []
        for index, entry in enumerate(entries):
            filename = f"report-{index:03}.json"
            report_path = out / filename
            with report_path.open("wb") as stdout, (out / f"report-{index:03}.stderr").open("wb") as stderr:
                result = subprocess.run(command + ["check", "--snapshot", str(out / "snapshot"),
                    "--entry", entry, "--scope", config["scope"], "--format", "json"],
                    stdout=stdout, stderr=stderr, timeout=120, check=False)
            try:
                report = read_json(report_path)
            except (ValueError, UnicodeError) as error:
                raise ValueError(f"analyzer did not return JSON ({filename}); rebuild the CLI and inspect report-{index:03}.stderr") from error
            if not isinstance(report, dict):
                raise ValueError("analyzer report must be a schema-2 JSON object")
            if result.returncode not in STATUSES or report.get("status") != STATUSES[result.returncode]:
                raise ValueError("MoonLoadCheck returned an inconsistent status/exit code")
            if report.get("schema_version") != 2:
                raise ValueError("MoonLoadCheck report schema must be 2")
            exits.append(result.returncode)
            summary["reports"].append(dict(entry=entry, status=report["status"],
                exit_code=result.returncode, file=filename))
        # Input errors invalidate a gate; a proven failure dominates unknown.
        code = next(code for code in [3, 1, 2, 0] if code in exits)
        summary.update(status=STATUSES[code], exit_code=code)
    except (OSError, ValueError, RecursionError, subprocess.SubprocessError) as error:
        summary["message"] = str(error)
    write_json(out / "summary.json", summary)
    return summary


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise ValueError(message)


def main():
    parser = Parser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True, help="new directory outside the staged root")
    engine = parser.add_mutually_exclusive_group(required=True)
    engine.add_argument("--native", type=Path, help="trusted MoonLoadCheck Linux CLI executable")
    engine.add_argument("--js", type=Path, help="trusted MoonLoadCheck JS CLI (requires node)")
    try:
        args = parser.parse_args()
        binary = (args.native or args.js).resolve(strict=True)
        if not binary.is_file():
            raise ValueError("analyzer must be a file")
        command = [str(binary)] if args.native else ["node", str(binary)]
        summary = run(args.config, args.out, command)
    except (OSError, ValueError, RecursionError) as error:
        summary = dict(schema_version=1, kind="deployment_check", status="input_error", exit_code=3, message=str(error))
    print(json.dumps(summary, ensure_ascii=True))
    return summary["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
