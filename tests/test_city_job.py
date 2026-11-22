"""Run: python3 -m unittest discover -s tests -v"""
import json
import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "pipeline"))
import city_job as cj  # noqa: E402


class Cache(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = pathlib.Path(self.tmp.name)
        cj.ROOT = self.root
        (self.root / "scenes").mkdir()
        (self.root / "frames").mkdir()
        (self.root / "scenes/s.json").write_text(json.dumps({"camera": {"duration_s": 1}, "render": {"fps": 2}}))
        for i in range(2):
            (self.root / f"frames/f_{i:04d}.png").write_bytes(b"x" * 200_000)
        (self.root / "out.mp4").write_bytes(b"v")
        self.shot = {"scene": "scenes/s.json", "frames_dir": "frames"}

    def tearDown(self):
        self.tmp.cleanup()

    def good(self):
        return {"encoded": "out.mp4", "qc_pass": True, "fingerprint": cj.fingerprint(self.shot), "duration_s": 1}

    def test_valid_cache_kept(self):
        ss = self.good()
        cj.validate_cached(self.shot, ss)
        self.assertEqual(ss["encoded"], "out.mp4")

    def test_missing_file_invalidates(self):
        ss = self.good()
        (self.root / "out.mp4").unlink()
        cj.validate_cached(self.shot, ss)
        self.assertNotIn("encoded", ss)

    def test_failed_qc_invalidates(self):
        ss = self.good()
        ss["qc_pass"] = False
        cj.validate_cached(self.shot, ss)
        self.assertNotIn("encoded", ss)

    def test_changed_scene_or_frames_invalidates(self):
        ss = self.good()
        (self.root / "frames/f_0001.png").write_bytes(b"y" * 250_000)
        cj.validate_cached(self.shot, ss)
        self.assertNotIn("encoded", ss)

    def test_release_fails_closed(self):
        self.assertTrue(cj.release_blockers({"id": "c"}, {}))
        st = {"release": {"master": "out.mp4", "master_duration_s": 49.0, "master_visual_qc": True, "master_audio_gate": True,
                          "verticals": [], "rights_manifest": "out.mp4"}}
        b = cj.release_blockers({"id": "c"}, st)
        self.assertIn("master is not 300 s", b)
        self.assertIn("fewer than 2 vertical cuts with audio and QC passed", b)

    def test_release_passes_only_when_everything_holds(self):
        st = {"release": {"master": "out.mp4", "master_duration_s": 300.0, "master_visual_qc": True, "master_audio_gate": True,
                          "verticals": [{"file": "out.mp4", "audio_gate": True, "visual_qc": True}] * 2, "rights_manifest": "out.mp4"}}
        self.assertEqual(cj.release_blockers({"id": "c"}, st), [])


if __name__ == "__main__":
    unittest.main()
