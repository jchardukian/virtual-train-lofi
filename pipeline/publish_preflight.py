#!/usr/bin/env python3
"""Fail-closed check that a proposed set of posts respects the owner's hard publishing limits.

Pure logic, no network: the caller supplies what is already scheduled or published (from the scheduling
tool) and what it proposes to add. Returns a list of violations; an empty list means the plan may proceed.
Nothing in this repository schedules posts yet; this is the gate any scheduler must call first.
"""
import datetime
import json
import pathlib
import zoneinfo

LIMITS = json.loads((pathlib.Path(__file__).resolve().parent.parent / "publish/limits.json").read_text())["per_calendar_day"]
KINDS = {"youtube_long", "youtube_short", "tiktok"}


def local_date(iso, tz):
    """Calendar date of an ISO-8601 timestamp in the account's time zone. Naive timestamps are refused."""
    dt = datetime.datetime.fromisoformat(iso)
    if dt.tzinfo is None:
        raise ValueError(f"timestamp without a UTC offset: {iso}")
    return dt.astimezone(zoneinfo.ZoneInfo(tz)).date().isoformat()


def check(proposed, existing, allowed_channels, tz, go_live=False):
    """proposed/existing: lists of {"kind", "channel_id", "due_at"}. allowed_channels: {"youtube": id, "tiktok": id}."""
    bad = []
    if not go_live:
        bad.append("no explicit go-live from the owner")
    if not allowed_channels or not allowed_channels.get("youtube"):
        bad.append("no owner-named YouTube channel configured")
    counts = {}
    for src, posts in (("existing", existing), ("proposed", proposed)):
        for p in posts:
            if p.get("kind") not in KINDS:
                bad.append(f"{src}: unknown kind {p.get('kind')!r}")
                continue
            try:
                day = local_date(p["due_at"], tz)
            except Exception as e:
                bad.append(f"{src}: {e}")
                continue
            service = "tiktok" if p["kind"] == "tiktok" else "youtube"
            if src == "proposed" and p.get("channel_id") != (allowed_channels or {}).get(service):
                bad.append(f"proposed {p['kind']} on {day}: channel {p.get('channel_id')!r} is not the owner-named {service} channel")
            if (allowed_channels or {}).get(service) == p.get("channel_id"):
                counts.setdefault(day, {k: 0 for k in KINDS})[p["kind"]] += 1
    for day, c in sorted(counts.items()):
        if c["youtube_long"] > LIMITS["youtube_long_form_max"]:
            bad.append(f"{day}: {c['youtube_long']} long-form videos (limit {LIMITS['youtube_long_form_max']})")
        if c["youtube_short"] > LIMITS["youtube_shorts_max"]:
            bad.append(f"{day}: {c['youtube_short']} Shorts (limit {LIMITS['youtube_shorts_max']})")
        if c["youtube_long"] + c["youtube_short"] > LIMITS["youtube_regular_uploads_total_max"]:
            bad.append(f"{day}: {c['youtube_long'] + c['youtube_short']} YouTube uploads (limit {LIMITS['youtube_regular_uploads_total_max']})")
        if c["tiktok"] > LIMITS["tiktok_posts_max"]:
            bad.append(f"{day}: {c['tiktok']} TikTok posts (limit {LIMITS['tiktok_posts_max']})")
    return bad
