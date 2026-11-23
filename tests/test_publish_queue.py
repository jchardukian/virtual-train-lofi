import copy, sys, pathlib, unittest
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "pipeline"))
import publish_queue as Q

LIM = {"channel": {"buffer_channel_id": "yt1", "timezone": "America/Chicago", "go_live": True},
       "per_calendar_day": {}}
DESC = "A ride. Music: X by Purrple Cat, CC BY 4.0."


def item(kind, due, n):
    return {"kind": kind, "title": f"t{n}", "description": DESC, "media_url": f"https://m.example/{n}.mp4",
            "media_sha256": f"h{n}", "approved_sha256": f"h{n}", "due_at": due}


REC = {"city": "chicago", "items": [item("youtube_short", "2026-11-24T12:00:00-06:00", 1), item("youtube_long", "2026-11-24T18:00:00-06:00", 2),
                                    item("youtube_short", "2026-11-24T20:30:00-06:00", 3)]}


class T(unittest.TestCase):
    def test_good_day(self):
        r = Q.build_day(REC, [], LIM)
        self.assertTrue(r["ok"], r["violations"]); self.assertEqual(len(r["payloads"]), 3)
        self.assertTrue(all(p["channelId"] == "yt1" and p["metadata"]["youtube"]["isAiGenerated"] is False for p in r["payloads"]))

    def test_no_go_live_returns_nothing(self):
        lim = copy.deepcopy(LIM); lim["channel"]["go_live"] = False
        r = Q.build_day(REC, [], lim)
        self.assertFalse(r["ok"]); self.assertEqual(r["payloads"], [])

    def test_missing_url(self):
        rec = copy.deepcopy(REC); rec["items"][1]["media_url"] = ""
        self.assertFalse(Q.build_day(rec, [], LIM)["ok"])

    def test_hash_mismatch(self):
        rec = copy.deepcopy(REC); rec["items"][1]["media_sha256"] = "other"
        self.assertFalse(Q.build_day(rec, [], LIM)["ok"])

    def test_missing_credit(self):
        rec = copy.deepcopy(REC); rec["items"][0]["description"] = "no credit here"
        self.assertFalse(Q.build_day(rec, [], LIM)["ok"])

    def test_duplicate_of_existing(self):
        ex = [{"kind": "youtube_long", "channel_id": "yt1", "due_at": "2026-11-20T18:00:00-06:00", "title": "t2"}]
        self.assertFalse(Q.build_day(REC, ex, LIM)["ok"])

    def test_day_already_has_long_form(self):
        ex = [{"kind": "youtube_long", "channel_id": "yt1", "due_at": "2026-11-24T08:00:00-06:00", "title": "other"}]
        self.assertFalse(Q.build_day(REC, ex, LIM)["ok"])

    def test_wrong_shape(self):
        rec = copy.deepcopy(REC); rec["items"].append(item("youtube_long", "2026-11-24T21:00:00-06:00", 4))
        self.assertFalse(Q.build_day(rec, [], LIM)["ok"])

    def test_no_channel(self):
        self.assertFalse(Q.build_day(REC, [], {"channel": {"go_live": True}})["ok"])


if __name__ == "__main__":
    unittest.main()
