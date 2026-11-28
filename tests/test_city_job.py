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
        self.assertTrue(any(x.startswith("fewer than 2 vertical cuts") for x in b))

    def full(self):
        import hashlib
        (self.root / "q.json").write_text("{}")
        (self.root / "lic.html").write_text("x")
        (self.root / "rights.json").write_text(json.dumps({"music": [{"licence_evidence": "lic.html"}], "required_credits": ["c"]}))
        h = hashlib.sha256((self.root / "out.mp4").read_bytes()).hexdigest()
        v = {"file": "out.mp4", "audio_gate": True, "visual_qc": True, "sha256": h, "qc_report": "q.json", "audio_report": "q.json"}
        return {"release": {"master": "out.mp4", "sha256": h, "master_duration_s": 300.0, "master_visual_qc": True,
                            "master_audio_gate": True, "transitions_clean": True, "verticals": [v, dict(v)], "rights_manifest": "rights.json"}}

    def test_release_passes_only_when_everything_holds(self):
        self.assertEqual(cj.release_blockers({"id": "c"}, self.full()), [])

    def test_replaced_vertical_is_rejected(self):
        st = self.full()
        st["release"]["verticals"][0]["sha256"] = "0" * 64
        self.assertTrue(any("vertical" in b for b in cj.release_blockers({"id": "c"}, st)))

    def test_bad_rights_manifest_is_rejected(self):
        st = self.full()
        (self.root / "rights.json").write_text("not json")
        self.assertTrue(any("rights" in b for b in cj.release_blockers({"id": "c"}, st)))

    def test_missing_planned_shot_blocks(self):
        st = self.full()
        st["release"]["missing_shots"] = ["scenes/x.json"]
        self.assertTrue(any("planned shots" in b for b in cj.release_blockers({"id": "c"}, st)))


if __name__ == "__main__":
    unittest.main()
