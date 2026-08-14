"""Report render findings as JSON, text, or Markdown."""

import json
from pathlib import Path


def summarize(path, findings):
    levels = [f.level for f in findings]
    return {
        "file": str(path),
        "status": "fail" if "fail" in levels else ("warn" if "warn" in levels else "pass"),
        "findings": [f.as_dict() for f in findings],
    }


def render_markdown(results, profile):
    lines = [f"# Video quality report\n", f"Profile: `{profile['name']}`\n"]
    for result in results:
        lines.extend([f"## `{result['file']}`: **{result['status'].upper()}**", ""])
        for f in result.get("findings", []):
            evidence = f" `{json.dumps(f['evidence'], sort_keys=True)}`" if f.get("evidence") else ""
            lines.append(f"- **{f['level'].upper()}** `{f['code']}`: {f['message']}{evidence}")
        lines.append("")
    return "\n".join(lines)


def write_json(results, destination):
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    Path(destination).write_text(json.dumps({"results": results}, indent=2) + "\n")


def write_markdown(results, profile, destination):
    Path(destination).parent.mkdir(parents=True, exist_ok=True)
    Path(destination).write_text(render_markdown(results, profile) + "\n")
