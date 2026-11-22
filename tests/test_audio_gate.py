"""Run: python3 -m unittest discover -s tests -v"""
import pathlib
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "pipeline"))
import audio_gate as g  # noqa: E402

LOG = """[silencedetect @ 0x1] silence_start: 0
[silencedetect @ 0x1] silence_end: 2.5 | silence_duration: 2.5
[Parsed_ebur128_1 @ 0x2] t: 3 TARGET:-23 LUFS
[silencedetect @ 0x1] silence_start: 40.2
[silencedetect @ 0x1] silence_end: 44.0 | silence_duration: 3.8
[silencedetect @ 0x1] silence_start: 58.9
"""


def make(path, audio):
    """10 s test clip; `audio` is an ffmpeg lavfi audio source expression or None."""
    cmd = ["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-f", "lavfi", "-i", "testsrc2=s=320x180:r=10:d=10"]
    if audio:
        cmd += ["-f", "lavfi", "-i", audio, "-c:a", "aac", "-shortest"]
    cmd += ["-c:v", "libx264", "-pix_fmt", "yuv420p", str(path)]
    subprocess.run(cmd, check=True)


class Parsing(unittest.TestCase):
    def test_pairs_in_order_and_closes_final(self):
        s = g.parse_silences(LOG, 60.0)
        self.assertEqual(s, [(0.0, 2.5), (40.2, 44.0), (58.9, 60.0)])

    def test_initial_and_middle_block_final_fade_does_not(self):
        s = g.parse_silences(LOG, 60.0)
        self.assertEqual(g.blocking_gaps(s, 60.0), [(0.0, 2.5), (40.2, 44.0)])
        self.assertEqual(g.blocking_gaps([(58.9, 60.0)], 60.0), [])

    def test_unclosed_long_final_silence_blocks(self):
        s = g.parse_silences("x silence_start: 30.0\n", 60.0)
        self.assertEqual(g.blocking_gaps(s, 60.0), [(30.0, 60.0)])

    def test_nan_or_missing_loudness_is_none(self):
        self.assertIsNone(g.last_float(r"I:\s+(-?[\d.]+|nan) LUFS", "I: nan LUFS"))
        self.assertIsNone(g.last_float(r"I:\s+(-?[\d.]+|nan) LUFS", "no loudness here"))


class Decision(unittest.TestCase):
    def ok(self, **kw):
        base = dict(video_dur=60.0, audio_dur=60.0, has_audio=True, silences=[], lufs=-16.0, peak=-1.5)
        base.update(kw)
        return g.evaluate(**base)[1]

    def test_good_passes(self):
        self.assertTrue(self.ok())

    def test_fail_closed_cases(self):
        self.assertFalse(self.ok(has_audio=False))
        self.assertFalse(self.ok(audio_dur=None))          # unknown audio duration must not be assumed to cover
        self.assertFalse(self.ok(audio_dur=50.0))
        self.assertFalse(self.ok(silences=None))           # analysis failed
        self.assertFalse(self.ok(silences=[(10.0, 12.0)]))
        self.assertFalse(self.ok(lufs=None))
        self.assertFalse(self.ok(lufs=-40.0))
        self.assertFalse(self.ok(peak=0.0))
        self.assertFalse(self.ok(peak=None))


class RealFiles(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        d = pathlib.Path(cls.tmp.name)
        cls.tone, cls.silent, cls.mute, cls.gap = d / "tone.mp4", d / "silent.mp4", d / "mute.mp4", d / "gap.mp4"
        make(cls.tone, "sine=frequency=440:duration=10")
        make(cls.silent, None)
        make(cls.mute, "anullsrc=r=48000:cl=stereo:d=10")
        make(cls.gap, "sine=frequency=440:duration=10,volume='if(between(t,3,6),0,1)':eval=frame")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_audible_file_passes(self):
        r = g.check(str(self.tone))
        self.assertTrue(r["pass"], r)

    def test_no_audio_stream_fails(self):
        self.assertFalse(g.check(str(self.silent))["pass"])

    def test_digital_silence_fails(self):
        self.assertFalse(g.check(str(self.mute))["pass"])

    def test_middle_gap_fails(self):
        r = g.check(str(self.gap))
        self.assertFalse(r["checks"]["no_silent_gap_over_1.5s"], r)

    def test_missing_file_fails_without_crashing(self):
        r = g.check("/nonexistent/file.mp4")
        self.assertFalse(r["pass"])


if __name__ == "__main__":
    unittest.main()
