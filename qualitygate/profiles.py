"""Delivery profiles for common creator exports."""

PROFILES = {
    "vertical": {
        "width": 1080,
        "height": 1920,
        "ratio_tolerance": 0.015,
        "video_codecs": {"h264", "avc1"},
        "audio_codecs": {"aac"},
        "require_audio": True,
    },
    "horizontal": {
        "width": 1920,
        "height": 1080,
        "ratio_tolerance": 0.015,
        "video_codecs": {"h264", "avc1"},
        "audio_codecs": {"aac"},
        "require_audio": True,
    },
    "square": {
        "width": 1080,
        "height": 1080,
        "ratio_tolerance": 0.015,
        "video_codecs": {"h264", "avc1"},
        "audio_codecs": {"aac"},
        "require_audio": True,
    },
}


def get_profile(name, width=None, height=None, require_audio=None):
    if name not in PROFILES and name != "custom":
        raise ValueError(f"unknown profile: {name}")
    profile = dict(PROFILES.get(name, {}))
    if width is not None:
        profile["width"] = width
    if height is not None:
        profile["height"] = height
    if require_audio is not None:
        profile["require_audio"] = require_audio
    if "width" not in profile or "height" not in profile:
        raise ValueError("custom profile requires --width and --height")
    profile["name"] = name
    return profile
