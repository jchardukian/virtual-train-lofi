# Media storage and delivery: proposal (nothing created)

Written 2026-11-23. Read-only findings plus a design. No bucket exists, nothing is public,
no spend. Needs the owner's approval before any of it is created.

## Verified facts

From Cloudflare's own pages (developers.cloudflare.com/r2/pricing and /r2/platform/limits, both dated 2026-10-30):
- Storage 0.015 USD per GB-month; Class A operations 4.50 USD per million; Class B 0.36 USD per million; egress free.
- Free allowance: 10 GB-month storage, 1 million Class A, 10 million Class B per month. The pages do not say
  whether that is per account or per bucket; assume per account.
- Single-request upload up to 5 GiB; larger via multipart. (My earlier "about 300 MB" figure was wrong.)
- The built-in `r2.dev` public address is rate-limited and "not intended for production"; Cloudflare says to
  connect a custom domain for production.
- Not confirmed from those pages: presigned URL lifetime, lifecycle rules. Both need checking before relying on them.

From the owner's account (read-only API calls, 2026-11-22): seven buckets holding about 4.9 GB in total, so
roughly 5 GB of the free storage allowance is unused. One bucket already serves media from a custom hostname.

## Design: two places, not one

1. **Archive bucket, private** (`lofitrain-archive`). Every approved 1080p master and full-resolution Short,
   plus source art. Never public. This is the durable copy.
2. **Delivery bucket, public read** (`lofitrain-delivery`). Only the three files due for release, copied in
   shortly before scheduling, under unguessable names (a random prefix per file). Removed after YouTube has
   processed the upload: by a lifecycle rule if supported, otherwise by an explicit delete step.
   Public address: a subdomain on one of the owner's domains is the production route; `r2.dev` is acceptable
   only for a first test.

A short-lived signed link instead of a public bucket would be better still. Whether the scheduling tool can
fetch one has not been tested, because testing means creating a real post. If the owner approves a single
draft-only test, that can be tried first.

Trade-off stated plainly: anything in the delivery bucket can be downloaded by anyone who obtains its link
while it is there. The video is about to be public on YouTube anyway; the archive is what stays private.

## Cost at one city a day (about 0.33 GB per day archived; delivery copies transient)

| After | Archive size | With about 4.9 GB already used elsewhere | Storage cost per month |
|---|---|---|---|
| 30 days | about 10 GB | about 15 GB | about 0.07 USD |
| 90 days | about 30 GB | about 35 GB | about 0.37 USD |
| 365 days | about 120 GB | about 125 GB | about 1.73 USD |

Operations: a few dozen writes and reads per day, far inside the free operation allowances. Egress free.
Livestream files would add to this and are not included.

## What needs the owner's approval

1. Create the two buckets in the existing account.
2. Public read on the delivery bucket only.
3. Storage charges once the account passes 10 GB (table above).
4. Optional: which domain to hang a delivery subdomain on.

## Automation status, honestly

- `pipeline/publish_queue.py` builds a day's three scheduling payloads and refuses unless: go-live is set, the
  channel is the owner-named one, the daily cap holds, every file has an https link, each uploaded file's hash
  matches the approved build, the music credit is in the description, and nothing duplicates an existing post.
  It has tests. It does not upload files and does not call the scheduling tool.
- Not built: the upload step (needs the buckets), and anything that runs unattended. A person or agent still
  triggers each day's release. Automated daily publishing is **not** solved.
