import sys, pathlib, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "pipeline"))
import publish_preflight as P

CH = {"youtube": "yt1", "tiktok": "tt1"}
TZ = "America/Chicago"


def post(kind, due, ch=None):
    return {"kind": kind, "due_at": due, "channel_id": ch or ("tt1" if kind == "tiktok" else "yt1")}


DAY = [post("youtube_long", "2026-11-24T09:00:00-06:00"), post("youtube_short", "2026-11-24T12:00:00-06:00"),
       post("youtube_short", "2026-11-24T18:00:00-06:00")]


class T(unittest.TestCase):
    def test_full_day_passes(self):
        self.assertEqual(P.check(DAY, [], CH, TZ, go_live=True), [])

    def test_no_go_live_blocks(self):
        self.assertTrue(any("go-live" in v for v in P.check(DAY, [], CH, TZ)))

    def test_no_channel_blocks(self):
        self.assertTrue(P.check(DAY, [], {}, TZ, go_live=True))

    def test_second_long_form_blocks(self):
        v = P.check([post("youtube_long", "2026-11-24T20:00:00-06:00")], DAY, CH, TZ, go_live=True)
        self.assertTrue(any("long-form" in x for x in v))

    def test_third_short_blocks(self):
        v = P.check([post("youtube_short", "2026-11-24T21:00:00-06:00")], DAY, CH, TZ, go_live=True)
        self.assertTrue(any("Shorts" in x for x in v))

    def test_existing_posts_count(self):
        v = P.check(DAY, [post("youtube_long", "2026-11-24T07:00:00-06:00")], CH, TZ, go_live=True)
        self.assertTrue(v)

    def test_any_tiktok_blocks_while_deferred(self):
        v = P.check([post("tiktok", "2026-11-24T22:00:00-06:00")], DAY, CH, TZ, go_live=True)
        self.assertTrue(any("TikTok" in x for x in v))

    def test_wrong_channel_blocks(self):
        v = P.check([post("youtube_long", "2026-11-25T09:00:00-06:00", "someone_else")], [], CH, TZ, go_live=True)
        self.assertTrue(any("not the owner-named" in x for x in v))

    def test_local_calendar_day_not_utc(self):
        # 23:30 local on the 24th is already the 25th in UTC; it must still count against the 24th
        v = P.check([post("youtube_long", "2026-11-25T05:30:00+00:00")], DAY, CH, TZ, go_live=True)
        self.assertTrue(any("2026-11-24" in x and "long-form" in x for x in v))

    def test_next_day_is_separate(self):
        self.assertEqual(P.check([post("youtube_long", "2026-11-25T09:00:00-06:00")], DAY, CH, TZ, go_live=True), [])

    def test_naive_timestamp_refused(self):
        self.assertTrue(P.check([post("youtube_long", "2026-11-25T09:00:00")], [], CH, TZ, go_live=True))


if __name__ == "__main__":
    unittest.main()
