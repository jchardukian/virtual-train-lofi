#!/bin/bash
# Copy a built city's master and Shorts to the private archive bucket, verifying each by download and SHA-256.
# Files over 290 MB are stored as 200 MB parts (the API route available here rejects larger single uploads);
# rejoin with cat. Usage: pipeline/archive_city.sh <city>
set -uo pipefail
cd "$(dirname "$0")/.."
C=$1; D=output/cities/$C/illustrated
A=$(cat /tmp/claude-0/-home-user-virtual-train-lofi/4d9ac6eb-369f-50a6-907b-5a9960b1cae9/scratchpad/cf_acct 2>/dev/null)
[ -z "$A" ] && A=$(curl -sS https://api.cloudflare.com/client/v4/accounts -H "Authorization: Bearer dummy" | python3 -c "import json,sys;print(json.load(sys.stdin)['result'][0]['id'])")
U="https://api.cloudflare.com/client/v4/accounts/$A/r2/buckets/lofitrain-archive/objects/$C"
H="Authorization: Bearer dummy"
ok=1
put() {  # local file, object name
  local code got want
  code=$(curl -sS --retry 3 -X PUT "$U/$2" -H "$H" -H "Content-Type: application/octet-stream" --data-binary @"$1" -o /dev/null -w "%{http_code}")
  want=$(sha256sum "$1" | cut -d' ' -f1); got=$(curl -sS --retry 3 "$U/$2" -H "$H" | sha256sum | cut -d' ' -f1)
  [ "$code" = "200" ] && [ "$want" = "$got" ] && echo "  $2 ok" || { echo "  $2 FAILED ($code)"; ok=0; }
}
for f in "$D"/${C}_illustrated_master.mp4 "$D"/${C}_illustrated_vertical_1.mp4 "$D"/${C}_illustrated_vertical_2.mp4 "$D"/SHA256SUMS; do
  [ -f "$f" ] || { echo "  missing $f"; ok=0; continue; }
  n=$(basename "$f")
  if [ $(stat -c %s "$f") -gt 304087040 ]; then
    T=$(mktemp -d); split -b 200M -d "$f" "$T/$n.part"
    for p in "$T"/*; do put "$p" "$(basename "$p")"; done; rm -rf "$T"
  else put "$f" "$n"; fi
done
[ $ok = 1 ] && echo "$C archived" || echo "$C ARCHIVE INCOMPLETE"
