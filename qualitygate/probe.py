"""Small ffprobe/ffmpeg adapters with no Python dependencies."""

import json
import re
import shutil
import subprocess


class ProbeError(RuntimeError):
    pass


def _run(command):
    try:
        return subprocess.run(command, check=False, capture_output=True, text=True, timeout=300)
    except FileNotFoundError as exc:
        raise ProbeError(f"required command is not installed: {command[0]}") from exc
    except subprocess.TimeoutExpired as exc:
        raise ProbeError(f"command timed out after 300 seconds: {command[0]}") from exc


def probe(path):
    if not shutil.which("ffprobe"):
        raise ProbeError("ffprobe is not on PATH")
    result = _run(["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", path])
    if result.returncode:
        raise ProbeError(result.stderr.strip() or "ffprobe could not read the file")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ProbeError("ffprobe returned invalid JSON") from exc


def _timestamps(output, pattern):
    rows = []
    for match in re.finditer(pattern, output):
        try:
            rows.append({"start": float(match.group(1)), "end": float(match.group(2)) if match.lastindex and match.lastindex >= 2 else None})
        except (TypeError, ValueError):
            pass
    return rows


def optional_filters(path):
    """Run bounded diagnostics when ffmpeg exists; missing ffmpeg is not fatal."""
    if not shutil.which("ffmpeg"):
        return {"available": False, "reason": "ffmpeg is not on PATH"}
    result = _run(["ffmpeg", "-hide_banner", "-nostats", "-i", path,
                   "-vf", "blackdetect=d=0.5:pic_th=0.98,freezedetect=n=0.003:d=1",
                   "-af", "ebur128=framelog=verbose", "-f", "null", "-"])
    text = (result.stderr or "")
    black = _timestamps(text, r"black_start:\s*([0-9.]+).*?black_end:\s*([0-9.]+)")
    freeze = _timestamps(text, r"freeze_start:\s*([0-9.]+).*?freeze_end:\s*([0-9.]+)")
    loudness = None
    matches = re.findall(r"I:\s*(-?[0-9.]+)\s+LUFS", text)
    if matches:
        loudness = {"integrated_lufs": float(matches[-1])}
    return {"available": True, "black": black, "freeze": freeze, "loudness": loudness}
