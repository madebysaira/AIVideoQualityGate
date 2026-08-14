import unittest

from qualitygate.checks import inspect_metadata
from qualitygate.profiles import get_profile


class QualityGateChecksTest(unittest.TestCase):
    def setUp(self):
        self.profile = get_profile("vertical")
        self.good = {
            "format": {"duration": "4.0"},
            "streams": [
                {"codec_type": "video", "codec_name": "h264", "width": 1080, "height": 1920, "avg_frame_rate": "30/1"},
                {"codec_type": "audio", "codec_name": "aac", "channels": 2},
            ],
        }

    def test_good_vertical_file_passes_contract_checks(self):
        findings = inspect_metadata(self.good, self.profile)
        self.assertFalse([f for f in findings if f.level == "fail"])
        self.assertTrue(any(f.code == "video.dimensions" and f.level == "pass" for f in findings))

    def test_wrong_dimensions_fail(self):
        self.good["streams"][0]["width"] = 1920
        findings = inspect_metadata(self.good, self.profile)
        self.assertTrue(any(f.code == "video.dimensions" and f.level == "fail" for f in findings))

    def test_missing_audio_fails_when_profile_requires_it(self):
        self.good["streams"] = self.good["streams"][:1]
        findings = inspect_metadata(self.good, self.profile)
        self.assertTrue(any(f.code == "audio.missing" and f.level == "fail" for f in findings))

    def test_silent_custom_profile_can_warn_instead(self):
        profile = get_profile("custom", 640, 360, require_audio=False)
        metadata = {"format": {"duration": "1"}, "streams": [self.good["streams"][0]]}
        metadata["streams"][0] = dict(metadata["streams"][0], width=640, height=360)
        findings = inspect_metadata(metadata, profile)
        self.assertTrue(any(f.code == "audio.missing" and f.level == "warn" for f in findings))


if __name__ == "__main__":
    unittest.main()
