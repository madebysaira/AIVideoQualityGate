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


def _video_duration_s(metadata):
    """Real video duration in seconds, preferring frame math over container time.

    freezedetect never prints freeze_end when a freeze runs to end of file
    (the classic stalled-generator render, last frame cloned to EOF), so the
    event must be reconstructed from an orphan freeze_start plus the true
    duration. Frame count / fps survives short audio tracks that would
    otherwise shrink the answer.
    """
    for stream in metadata.get("streams", []):
        if stream.get("codec_type") != "video":
            continue
        frames = stream.get("nb_frames")
        rate = stream.get("r_frame_rate") or stream.get("avg_frame_rate")
        if frames is not None and rate and rate not in ("0/0", "N/A"):
            try:
                num, _, den = rate.partition("/")
                den_f = float(den or 1)
                if float(num or 0) > 0 and den_f > 0:
                    return float(frames) * den_f / float(num)
            except (TypeError, ValueError):
                pass
        if stream.get("duration"):
            try:
                return float(stream["duration"])
            except ValueError:
                pass
    fmt = metadata.get("format", {})
    if fmt.get("duration"):
        try:
            return float(fmt["duration"])
        except ValueError:
            pass
    return None


def optional_filters(path, metadata=None):
    """Run bounded diagnostics when ffmpeg exists; missing ffmpeg is not fatal.

    When metadata is supplied, an orphan freeze_start (freeze runs to EOF, no
    freeze_end is ever printed) is reconstructed as an event from freeze_start
    to the real duration of the video.
    """
    if not shutil.which("ffmpeg"):
        return {"available": False, "reason": "ffmpeg is not on PATH"}
    result = _run(["ffmpeg", "-hide_banner", "-nostats", "-i", path,
                   "-vf", "blackdetect=d=0.5:pic_th=0.98,freezedetect=n=0.003:d=1",
                   "-af", "ebur128=framelog=verbose", "-f", "null", "-"])
    text = (result.stderr or "")
    black = _timestamps(text, r"black_start:\s*([0-9.]+).*?black_end:\s*([0-9.]+)")
    freeze = _timestamps(text, r"freeze_start:\s*([0-9.]+).*?freeze_end:\s*([0-9.]+)")
    if metadata is not None:
        starts = [float(m.group(1)) for m in re.finditer(r"freeze_start:\s*([0-9.]+)", text)]
        # a start with no end marker on any later line is an EOF freeze
        ended = {row["start"] for row in freeze}
        duration = _video_duration_s(metadata)
        if duration is not None:
            for start in starts:
                if start in ended:
                    continue
                freeze.append({"start": start, "end": duration, "reconstructed": True})
    loudness = None
    matches = re.findall(r"I:\s*(-?[0-9.]+)\s+LUFS", text)
    if matches:
        loudness = {"integrated_lufs": float(matches[-1])}
    return {"available": True, "black": black, "freeze": freeze, "loudness": loudness}
