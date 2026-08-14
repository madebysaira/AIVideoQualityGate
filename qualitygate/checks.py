"""Pure validation logic. No subprocesses or third-party dependencies."""

from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional


@dataclass
class Finding:
    level: str
    code: str
    message: str
    evidence: Optional[Dict[str, Any]] = None

    def as_dict(self):
        value = asdict(self)
        if value["evidence"] is None:
            value.pop("evidence")
        return value


def _number(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _codec(stream):
    return (stream.get("codec_name") or stream.get("codec_tag_string") or "").lower()


def inspect_metadata(metadata, profile):
    """Return findings for one ffprobe JSON document."""
    findings: List[Finding] = []
    streams = metadata.get("streams") or []
    videos = [s for s in streams if s.get("codec_type") == "video"]
    audios = [s for s in streams if s.get("codec_type") == "audio"]

    if not videos:
        findings.append(Finding("fail", "video.missing", "No video stream was found."))
        return findings
    if len(videos) > 1:
        findings.append(Finding("warn", "video.multiple", "More than one video stream is present.", {"count": len(videos)}))

    video = videos[0]
    width, height = video.get("width"), video.get("height")
    expected_w, expected_h = profile["width"], profile["height"]
    if width != expected_w or height != expected_h:
        findings.append(Finding("fail", "video.dimensions", f"Expected {expected_w}x{expected_h}, found {width}x{height}.", {"expected": [expected_w, expected_h], "actual": [width, height]}))
    else:
        findings.append(Finding("pass", "video.dimensions", f"Dimensions are {width}x{height}."))

    actual_ratio = _number(width) / _number(height, 1)
    expected_ratio = expected_w / expected_h
    if abs(actual_ratio - expected_ratio) > profile.get("ratio_tolerance", 0.015):
        findings.append(Finding("fail", "video.aspect_ratio", "Aspect ratio does not match the delivery profile.", {"expected": round(expected_ratio, 4), "actual": round(actual_ratio, 4)}))
    else:
        findings.append(Finding("pass", "video.aspect_ratio", "Aspect ratio matches the delivery profile."))

    codec = _codec(video)
    allowed = profile.get("video_codecs", set())
    if allowed and codec not in allowed:
        findings.append(Finding("warn", "video.codec", f"Video codec is {codec or 'unknown'}; expected one of {sorted(allowed)}.", {"actual": codec, "expected": sorted(allowed)}))
    else:
        findings.append(Finding("pass", "video.codec", f"Video codec is {codec or 'unknown'}."))

    duration = _number((metadata.get("format") or {}).get("duration"))
    if duration <= 0:
        findings.append(Finding("fail", "duration.missing", "The file has no positive duration."))
    else:
        findings.append(Finding("pass", "duration.present", f"Duration is {duration:.3f} seconds.", {"seconds": duration}))

    fps = _fps(video.get("avg_frame_rate") or video.get("r_frame_rate"))
    if fps <= 0:
        findings.append(Finding("warn", "video.fps", "Frame rate could not be read."))
    else:
        findings.append(Finding("pass", "video.fps", f"Frame rate is {fps:.3f} fps.", {"fps": round(fps, 3)}))

    if not audios:
        level = "fail" if profile.get("require_audio", True) else "warn"
        findings.append(Finding(level, "audio.missing", "No audio stream was found."))
    else:
        if len(audios) > 1:
            findings.append(Finding("warn", "audio.multiple", "More than one audio stream is present.", {"count": len(audios)}))
        acodec = _codec(audios[0])
        allowed_audio = profile.get("audio_codecs", set())
        if allowed_audio and acodec not in allowed_audio:
            findings.append(Finding("warn", "audio.codec", f"Audio codec is {acodec or 'unknown'}; expected one of {sorted(allowed_audio)}."))
        else:
            findings.append(Finding("pass", "audio.present", f"Audio stream is present ({acodec or 'unknown'})."))

    return findings


def _fps(value):
    if not value:
        return 0.0
    try:
        if "/" in str(value):
            n, d = str(value).split("/", 1)
            return float(n) / float(d) if float(d) else 0.0
        return float(value)
    except (ValueError, ZeroDivisionError):
        return 0.0


def apply_filter_findings(findings, filters):
    """Add optional ffmpeg filter findings from probe.py output."""
    for item in filters.get("black", []):
        findings.append(Finding("warn", "video.black", "Black section detected; review the timestamp.", item))
    for item in filters.get("freeze", []):
        findings.append(Finding("warn", "video.freeze", "Frozen section detected; review the timestamp.", item))
    if filters.get("loudness"):
        loud = filters["loudness"]
        findings.append(Finding("pass", "audio.loudness", f"Measured integrated loudness: {loud.get('integrated_lufs', 'unknown')} LUFS.", loud))
    return findings
