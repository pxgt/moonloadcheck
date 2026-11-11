"""Read-only staged-root preflight. Never infer missing runtime facts or execute inputs."""
from pathlib import Path
import json
import subprocess
import sys
import tempfile
from check_deployment import Parser, read_json, load_config, run, STATUSES

FACTS = {
    "cwd": "Declare the process working directory on the target.",
    "default_dirs": "Supply verified loader default directories, in order.",
    "library_path": "Declare the intended library path components; [] means known empty.",
    "cache_mode": "Declare disabled or an independently verified cache mode.",
    "hwcaps_policy": "Declare the verified hardware-capability search policy.",
    "secure_execution": "Establish secure-execution behavior; do not assume false from ELF bytes.",
    "preload": "Declare preload inputs; [] means known empty.",
    "audit": "Declare audit inputs; [] means known empty.",
}


def preflight(path, command):
    result = dict(schema_version=1, kind="deployment_preflight", status="input_error", exit_code=3,
                  scope="dependencies", missing_facts=[], reports=[],
                  note="Dependency readiness only, not symbol/version or application compatibility. Runtime facts are caller declarations.")
    try:
        path = path.resolve(strict=True)
        config = read_json(path)
        if not isinstance(config, dict):
            raise ValueError("configuration must be an object")
        key = "target" if "target" in config else "profile"
        facts = config.get(key)
        if isinstance(facts, dict):
            result["missing_facts"] = [dict(field=key + "." + name, action=action)
                                       for name, action in FACTS.items() if name not in facts]
        # Full strict validation still applies, even when missing facts were listed.
        load_config(path)
        with tempfile.TemporaryDirectory(prefix="mlc-preflight-") as folder:
            temp = Path(folder)
            # Preserve relative-root semantics when moving the config to a temporary directory.
            config["root"] = str((path.parent / config["root"]).resolve(strict=True))
            config["scope"] = "dependencies"
            cfg = temp / "config.json"
            cfg.write_text(json.dumps(config), encoding="utf-8")
            observed = run(cfg, temp / "run", command)
            result.update(status=observed["status"], exit_code=observed["exit_code"])
            if "message" in observed:
                result["message"] = observed["message"]
            total = 0
            for item in observed["reports"]:
                total += (temp / "run" / item["file"]).stat().st_size
                if total > 3 * 1024 * 1024:
                    raise ValueError("preflight evidence exceeds 3 MiB; split the entry list")
                result["reports"].append(dict(entry=item["entry"], evidence=read_json(temp / "run" / item["file"])))
    except (OSError, ValueError, RecursionError, subprocess.SubprocessError) as error:
        result.update(status=STATUSES[3], exit_code=3, message=str(error))
    return result


def main():
    parser = Parser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--native", type=Path)
    group.add_argument("--js", type=Path)
    try:
        args = parser.parse_args()
        binary = (args.native or args.js).resolve(strict=True)
        command = [str(binary)] if args.native else ["node", str(binary)]
        result = preflight(args.config, command)
    except (OSError, ValueError) as error:
        result = dict(kind="deployment_preflight", status="input_error", exit_code=3, message=str(error))
    print(json.dumps(result, ensure_ascii=True))
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
