"""Run independent deployment configurations; MoonBit validates and aggregates evidence."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
from check_deployment import Parser, read_json, fields, string, load_config, run, write_json, unique_object


def matrix(config_path, out, command):
    config_path = config_path.resolve(strict=True)
    config = read_json(config_path)
    fields(config, ["schema_version", "targets"])
    if type(config["schema_version"]) is not int or config["schema_version"] != 1:
        raise ValueError("matrix configuration schema must be 1")
    targets = config["targets"]
    if not isinstance(targets, list) or not 1 <= len(targets) <= 16:
        raise ValueError("matrix requires 1..16 targets")
    out = out.resolve()
    inputs, names = [], set()
    for target in targets:
        fields(target, ["id", "config"])
        name = string(target["id"], "target.id")
        if name in names:
            raise ValueError("duplicate target id")
        names.add(name)
        path = (config_path.parent / string(target["config"], "target.config")).resolve()
        # Reject output/source overlap for every root before creating anything.
        raw, problem, data = None, None, b""
        try:
            with path.open("rb") as stream:
                data = stream.read(4 * 1024 * 1024 + 1)
            if len(data) > 4 * 1024 * 1024:
                raise ValueError("configuration exceeds 4 MiB")
            raw = json.loads(data.decode("utf-8"), object_pairs_hook=unique_object)
        except (OSError, ValueError, RecursionError) as error:
            problem = str(error)
        if not problem and isinstance(raw, dict) and isinstance(raw.get("root"), str):
            try:
                root = (path.parent / raw["root"]).resolve()
                raw["root"] = str(root)
            except (OSError, ValueError) as error:
                problem = str(error)
            if not problem and (out == root or root in out.parents or out in root.parents):
                raise ValueError("matrix output overlaps a staged root")
        inputs.append((name, data, raw, problem))
    out.mkdir(parents=True, exist_ok=False)
    evidence = dict(schema_version=1, kind="deployment_matrix", targets=[])
    total_report_bytes = 0
    for index, (name, data, raw, problem) in enumerate(inputs):
        item = dict(id=name, config_sha256="0" * 64, entries=[], reports=[])
        evidence["targets"].append(item)
        try:
            item["config_sha256"] = hashlib.sha256(data).hexdigest()
            if problem:
                raise ValueError(problem)
            # Execute a frozen configuration, preserving the original root base.
            path = out / f"config-{index:03}.json"
            write_json(path, raw)
            _, _, entries, _ = load_config(path)
            item["entries"] = entries
            target_out = out / f"target-{index:03}"
            result = run(path, target_out, command)
            if result.get("message"):
                item["error"] = result["message"]
            for report in result["reports"]:
                source = target_out / report["file"]
                total_report_bytes += source.stat().st_size
                if total_report_bytes > 3 * 1024 * 1024:
                    raise ValueError("matrix evidence exceeds 3 MiB; split the matrix")
                item["reports"].append(read_json(source))
        except (OSError, ValueError, RecursionError, subprocess.SubprocessError) as error:
            item["error"] = str(error)
    write_json(out / "matrix.json", evidence)
    codes = []
    for form, name in [("summary", "summary.json"), ("html", "index.html")]:
        with (out / name).open("wb") as stream:
            result = subprocess.run(command + ["matrix-report", "--input", str(out / "matrix.json"),
                "--format", form], stdout=stream, stderr=subprocess.PIPE, timeout=120)
        codes.append(result.returncode)
        if result.stderr or result.returncode not in [0, 1, 2, 3]:
            raise ValueError("matrix renderer failed")
    summary = read_json(out / "summary.json")
    if summary.get("kind") != "deployment_matrix_summary" or codes != [summary.get("exit_code")] * 2:
        raise ValueError("matrix renderer returned invalid or incomplete evidence")
    return summary


def main():
    parser = Parser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--native", type=Path)
    group.add_argument("--js", type=Path)
    try:
        args = parser.parse_args()
        binary = (args.native or args.js).resolve(strict=True)
        result = matrix(args.config, args.out, [str(binary)] if args.native else ["node", str(binary)])
    except (OSError, ValueError, RecursionError, subprocess.SubprocessError) as error:
        result = dict(kind="deployment_matrix_summary", status="input_error", exit_code=3, message=str(error))
    print(json.dumps(result, ensure_ascii=True))
    return result["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
