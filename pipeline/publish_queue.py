#!/usr/bin/env python3
"""Build one day's release (1 long-form + 2 Shorts) as scheduling payloads, failing closed.

This module does not talk to any service. It turns a city's publish record into the exact
payloads a scheduling call would need, and refuses to return them unless every gate holds:
go-live flag, owner-named channel, daily caps (via publish_preflight), every media URL present
and https, media hashes matching the approved build, and no duplicate of anything already
scheduled or sent. The caller (a person or agent) passes the payloads to the scheduling tool.

  plan = build_day(record, existing_posts, limits)   ->  {"ok": bool, "violations": [...], "payloads": [...]}
"""
import json
import pathlib

import publish_preflight

ROOT = pathlib.Path(__file__).resolve().parent.parent


def load_limits():
    return json.loads((ROOT / "publish/limits.json").read_text())


def build_day(record, existing, limits):
    """record: {"city", "items": [{"kind", "title", "description", "media_url", "media_sha256", "approved_sha256", "due_at"}]}
    existing: posts already scheduled or sent on the channel: [{"kind", "channel_id", "due_at", "title"?, "media_url"?}]"""
    ch = limits.get("channel", {})
    bad = []
    kinds = sorted(i.get("kind") for i in record.get("items", []))
    if kinds != ["youtube_long", "youtube_short", "youtube_short"]:
        bad.append(f"a day's release must be exactly one long-form and two Shorts, got {kinds}")
    seen_titles = {e.get("title") for e in existing if e.get("title")}
    seen_urls = {e.get("media_url") for e in existing if e.get("media_url")}
    proposed = []
    for it in record.get("items", []):
        label = f"{record.get('city')} {it.get('kind')}"
        url = it.get("media_url") or ""
        if not url.startswith("https://"):
            bad.append(f"{label}: no https media URL")
        if not it.get("media_sha256") or it.get("media_sha256") != it.get("approved_sha256"):
            bad.append(f"{label}: uploaded file hash does not match the approved build")
        if not it.get("title") or not it.get("description"):
            bad.append(f"{label}: missing title or description")
        elif "Purrple Cat" not in it["description"] or "CC BY 4.0" not in it["description"]:
            bad.append(f"{label}: description lacks the music credit")
        if it.get("title") in seen_titles or url in seen_urls:
            bad.append(f"{label}: duplicate of a post already scheduled or sent")
        seen_titles.add(it.get("title")); seen_urls.add(url)
        proposed.append({"kind": it.get("kind"), "channel_id": ch.get("buffer_channel_id"), "due_at": it.get("due_at")})
    bad += publish_preflight.check(proposed, existing, {"youtube": ch.get("buffer_channel_id")}, ch.get("timezone", "UTC"),
                                   go_live=bool(ch.get("go_live")))
    if bad:
        return {"ok": False, "violations": bad, "payloads": []}
    # isAiGenerated is False by owner decision (2026-11-22): no on-video AI label; descriptions say the art is illustrated.
    payloads = [{"channelId": ch["buffer_channel_id"], "schedulingType": "automatic", "mode": "customScheduled", "dueAt": it["due_at"],
                 "text": it["description"], "assets": [{"video": {"url": it["media_url"]}}],
                 "metadata": {"youtube": {"title": it["title"], "categoryId": "10", "privacy": "public", "madeForKids": False,
                                          "isAiGenerated": False, return {"ok": True, "violations": [], "payloads": payloads}
