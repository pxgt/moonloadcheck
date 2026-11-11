"""Verify offline MoonBit presentation against CLI evidence and hostile text.

Generated HTML contains report metadata only, never snapshot blobs. Keep even
these outputs private by default because paths and symbols may be sensitive.
"""
from pathlib import Path
from html.parser import HTMLParser
from collections import Counter
import argparse
import copy
import hashlib
import json
import re
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
STATUS = {"pass_static": 0, "fail": 1, "inconclusive": 2, "input_error": 3}
HOSTILE = '</pre><script>alert("report")</script><img src="https://invalid.example/" onerror="alert(1)"><svg onload="alert(2)"></svg><a href="javascript:alert(3)">click</a>&\'\u2028'


class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(convert_charrefs=True)
        self.tags, self.text, self.pre, self.evidence = [], [], None, []
        self.ids, self.links, self.csp = [], [], None
        self.feed(text)
        self.close()
        assert self.tags.count("html") == self.tags.count("head") == self.tags.count("body") == 1
        assert self.tags.count("style") == 1
        assert self.csp == "default-src 'none'; script-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'"
        assert len(set(self.ids)) == len(self.ids) and all(link[1:] in self.ids for link in self.links)

    def handle_starttag(self, tag, attrs):
        assert tag in {"html", "head", "meta", "title", "style", "body", "header", "p", "h1", "main", "aside",
                       "strong", "section", "h2", "h3", "h4", "h5", "span", "code", "small", "dl", "dt", "dd",
                       "div", "ul", "ol", "li", "article", "details", "summary", "pre", "table", "thead", "tr",
                       "th", "tbody", "td", "br", "footer", "nav", "a"}, tag
        self.tags.append(tag)
        for key, value in attrs:
            assert key in {"lang", "charset", "name", "content", "http-equiv", "class", "id", "href"}, (tag, key)
            assert tag == "meta" or key not in {"charset", "name", "content", "http-equiv"}
            if key == "class":
                assert re.fullmatch(r"[a-z ]+", value), value
            if key == "id":
                assert re.fullmatch(r"consumer-\d+", value)
                self.ids.append(value)
            if key == "href":
                assert tag == "a" and re.fullmatch(r"#consumer-\d+", value)
                self.links.append(value)
        if tag == "meta" and dict(attrs).get("http-equiv") == "Content-Security-Policy":
            self.csp = dict(attrs)["content"]
        if tag == "pre":
            assert self.pre is None
            self.pre = []

    def handle_data(self, data):
        self.text.append(data)
        if self.pre is not None:
            self.pre.append(data)

    def handle_endtag(self, tag):
        if tag == "pre":
            value = "".join(self.pre)
            self.pre = None
            try:
                self.evidence.append(json.loads(value))
            except json.JSONDecodeError:
                pass


def invoke(command, expected):
    result = subprocess.run(list(map(str, command)), capture_output=True, text=True, timeout=60)
    assert result.returncode == expected, (command, expected, result.returncode, result.stdout[-2000:], result.stderr)
    assert not result.stderr, result.stderr
    return result.stdout


def verify(native, js):
    if not __debug__:
        raise RuntimeError("verification requires assertions")
    output = ROOT / "artifacts/presentation"
    output.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="run-", dir=output))
    commands = {"native": [str(native.resolve())], "js": ["node", str(js.resolve())]}
    deployment = json.loads((ROOT / "artifacts/deployment/result.json").read_text())
    deployed = Path(deployment["work"])
    payloads = {}
    for case in deployment["cases"]:
        label = f'{case["architecture"]}-{case["suite"]}-{case["case"]}'
        path = deployed / case["architecture"] / case["suite"] / case["case"] / "native/report-000.json"
        payloads[label] = json.loads(path.read_text())
    payloads["unknown"] = json.loads((deployed / "unverified-profile-native/report-000.json").read_text())
    payloads["mixed-input-error"] = json.loads((deployed / "mixed-input-error-native/report-001.json").read_text())
    entries = work / "entries.json"
    entries.write_text('["/opt/demo/app","/opt/demo/stable-app"]')
    for label, before, after, expected in [("introduced", "before", "after", 1),
                                          ("existing", "after", "after", 1), ("resolved", "after", "before", 0)]:
        value = invoke(commands["native"] + ["diff", "--before", ROOT / "fixtures/generated/u3/x86_64" / before / "snapshot",
            "--after", ROOT / "fixtures/generated/u3/x86_64" / after / "snapshot", "--entries", entries, "--format", "json"], expected)
        payloads[label] = json.loads(value)
    entries.write_text('["/opt/sensor-report/bin/sensor-report"]')
    payloads["indeterminate"] = json.loads(invoke(commands["native"] + ["diff", "--before", deployed / "unverified-profile-native/snapshot",
        "--after", deployed / "amd64/jammy/old-library/native/snapshot", "--entries", entries, "--format", "json"], 1))
    payloads["unknown-comparison"] = json.loads(invoke(commands["native"] + ["diff", "--before", deployed / "unverified-profile-native/snapshot",
        "--after", deployed / "amd64/jammy/good/native/snapshot", "--entries", entries, "--format", "json"], 2))
    entries.write_text('["/not-a-program"]')
    payloads["input-error-comparison"] = json.loads(invoke(commands["native"] + ["diff", "--before", deployed / "amd64/jammy/good/native/snapshot",
        "--after", deployed / "amd64/jammy/good/native/snapshot", "--entries", entries, "--format", "json"], 3))
    payloads["command-error"] = json.loads(invoke(commands["native"] + ["check", "--snapshot", work / "absent",
        "--entry", "/app", "--scope", "compatibility", "--format", "json"], 3))
    payloads["legacy-schema2"] = json.loads((ROOT / "fixtures/reports/schema-2.json").read_text())

    hostile = copy.deepcopy(payloads["legacy-schema2"])
    def poison(value, key=""):
        if isinstance(value, dict):
            return {k: poison(v, k) for k, v in value.items()}
        if isinstance(value, list):
            return [poison(v, key) for v in value]
        if isinstance(value, str) and key != "status":
            return HOSTILE
        return value
    payloads["hostile"] = poison(hostile)
    payloads["hostile-error"] = dict(schema_version=2, status="input_error", error_kind=HOSTILE, message=HOSTILE)
    future = copy.deepcopy(hostile)
    future["findings"][0]["code"] = "MLC999"
    future["future_optional_evidence"] = HOSTILE
    payloads["future-code"] = future
    for number in range(1, 10):
        sample = copy.deepcopy(hostile)
        sample["findings"][0]["code"] = f"MLC{number:03}"
        payloads[f"guide-{number}"] = sample

    checks, pages = 0, {}
    for label, value in payloads.items():
        source = work / (label + ".json")
        source.write_text(json.dumps(value, ensure_ascii=True), encoding="utf-8")
        original = source.read_bytes()
        expected = STATUS[value["status"]]
        views = {}
        for backend, command in commands.items():
            brief = json.loads(invoke(command + ["report", "--input", source, "--format", "summary"], expected))
            page = invoke(command + ["report", "--input", source, "--format", "html"], expected)
            parsed = Page(page)
            assert brief["status"] == value["status"] and brief["exit_code"] == expected
            text = "".join(parsed.text)
            assert value["status"] in text and "Saved evidence, not a fresh analysis." in text
            if "entries" in value:
                findings = [f for e in value["entries"] for f in e["after"]["findings"]]
                changes = [c for e in value["entries"] for c in e["changes"]]
                assert brief["entries"] == len(value["entries"])
                assert brief["changes"] == dict(Counter(c["classification"] for c in changes))
                assert parsed.evidence == [r for e in value["entries"] for r in [e["before"], e["after"]]]
            elif "entry" in value:
                findings = value["findings"]
                assert brief["entries"] == 1 and brief["changes"] == {}
                canonical = {k: v for k, v in value.items() if k != "future_optional_evidence"}
                assert parsed.evidence == [canonical]
            else:
                findings = []
                assert brief["entries"] == 0
                assert value in parsed.evidence
            assert brief["findings"] == len(findings)
            assert brief["codes"] == dict(Counter(f["code"] for f in findings))
            if label in ["hostile", "hostile-error"]:
                assert HOSTILE in text
            if label == "legacy-schema2":
                assert "18446744073709551615" in text
            if label == "future-code":
                assert "Unfamiliar diagnostic code" in text
            views[backend] = (brief, page)
            checks += 2
        assert views["native"] == views["js"], label
        assert source.read_bytes() == original
        (work / (label + ".html")).write_text(views["native"][1], encoding="utf-8")
        pages[label] = hashlib.sha256(views["native"][1].encode()).hexdigest()

    invalid = {"unknown-schema": {"schema_version": 99, "entry": {}},
               "invalid-shape": {}, "ambiguous": {"entries": [], "entry": {}},
               "bad-command-error": {"schema_version": 2, "status": "pass_static", "message": "bad"}}
    for label, mutate in [
        ("forged-status", lambda r: r.update(status="pass_static")),
        ("forged-change", lambda r: r["entries"][0]["changes"][0].update(classification="resolved")),
        ("omitted-change", lambda r: r["entries"][0].update(changes=[])),
        ("duplicate-consumer", lambda r: r["entries"].append(r["entries"][0])),
        ("forged-nested-status", lambda r: r["entries"][0]["after"].update(status="pass_static")),
        ("forged-finding", lambda r: r["entries"][0]["changes"][0]["after"].update(explanation="changed")),
        ("wrong-entry", lambda r: r["entries"][0]["entry"].update(hex="00")),
    ]:
        value = copy.deepcopy(payloads["introduced"])
        mutate(value)
        invalid[label] = value
    for label, value in invalid.items():
        (work / (label + ".json")).write_text(json.dumps(value), encoding="utf-8")
    invalid["duplicate-json-key"] = None
    (work / "duplicate-json-key.json").write_text('{"schema_version":2,"schema_version":2}')
    invalid["too-large"] = None
    (work / "too-large.json").write_text(" " * 4194305)
    for label in invalid:
        for command in commands.values():
            for format in ["html", "summary"]:
                error = json.loads(invoke(command + ["report", "--input", work / (label + ".json"), "--format", format], 3))
                assert error["status"] == "input_error" and error["error_kind"] in ["report", "json"]
                checks += 1
    for command in commands.values():
        for arguments in [["report"], ["report", "--input", entries, "--format", "xml"],
                          ["report", "--input", entries, "--format", "html", "extra"]]:
            assert json.loads(invoke(command + arguments, 3))["error_kind"] == "arguments"
            checks += 1
    record = dict(checks=checks, valid_inputs=len(payloads), invalid_inputs=len(invalid), work=str(work), pages=pages,
                  backends=list(commands), binary_blobs_embedded=False)
    (output / "result.json").write_text(json.dumps(record, indent=2) + "\n")
    print(f"Presentation: {checks} CLI checks; {len(payloads)} valid / {len(invalid)} invalid inputs; {work}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--native", required=True, type=Path)
    parser.add_argument("--js", required=True, type=Path)
    args = parser.parse_args()
    verify(args.native, args.js)
