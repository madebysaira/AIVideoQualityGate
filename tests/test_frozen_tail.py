"""EOF-freeze regression: frozen-tail render must surface a freeze event.

freezedetect never prints freeze_end when a freeze runs to end of file,
so without orphan-start reconstruction the clip passes QC clean.
Runs real ffmpeg fixtures; skipped when ffmpeg is unavailable.
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from qualitygate.probe import optional_filters, probe


def _have_ffmpeg():
    return shutil.which("ffmpeg") and shutil.which("ffprobe")


@unittest.skipUnless(_have_ffmpeg(), "ffmpeg/ffprobe not on PATH")
class FrozenTailTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix="qg_frozentail_"))
        cls.clip = cls.tmp / "frozen_tail.mp4"
        proc = subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
             "-f", "lavfi", "-i", "testsrc2=size=1280x720:rate=24:duration=3",
             "-f", "lavfi", "-i", "sine=frequency=440:duration=3",
             "-vf", "tpad=stop_mode=clone:stop_duration=5",
             "-af", "apad=whole_dur=8",
             "-c:v", "libx264", "-pix_fmt", "yuv420p", "-preset", "ultrafast",
             "-c:a", "aac", str(cls.clip)],
            capture_output=True, text=True,
        )
        if proc.returncode != 0 or not cls.clip.exists():
            raise unittest.SkipTest(f"fixture build failed: {proc.stderr[-400:]}")

    def test_frozen_tail_surfaces_freeze_event(self):
        metadata = probe(str(self.clip))
        filters = optional_filters(str(self.clip), metadata)
        self.assertTrue(filters["available"])
        self.assertTrue(filters["freeze"], "5s frozen tail produced no freeze events")
        recon = [f for f in filters["freeze"] if f.get("reconstructed")]
        self.assertTrue(recon, "expected a reconstructed EOF-freeze event")
        self.assertGreater(recon[0]["end"] - recon[0]["start"], 4.0)


if __name__ == "__main__":
    unittest.main()
