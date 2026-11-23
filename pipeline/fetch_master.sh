#!/bin/bash
# Fetch a city's master back from the private archive (rejoining 200 MB parts) and verify it against SHA256SUMS.
# Usage: pipeline/fetch_master.sh <city>
set -uo pipefail
cd "$(dirname "$0")/.."
C=$1; D=output/cities/$C/illustrated; F=$D/${C}_illustrated_master.mp4
A=$(curl -sS https://api.cloudflare.com/client/v4/accounts -H "Authorization: Bearer dummy" | python3 -c "import json,sys;print(json.load(sys.stdin)['result'][0]['id'])")
U="https://api.cloudflare.com/client/v4/accounts/$A/r2/buckets/lofitrain-archive/objects/$C"
T=$(mktemp -d); i=0
if [ "$(curl -sS "$U/${C}_illustrated_master.mp4.part00" -H "Authorization: Bearer dummy" -o "$T/p00" -w "%{http_code}")" = "200" ]; then
  while :; do i=$((i+1)); n=$(printf %02d $i)
    [ "$(curl -sS --retry 3 "$U/${C}_illustrated_master.mp4.part$n" -H "Authorization: Bearer dummy" -o "$T/p$n" -w "%{http_code}")" = "200" ] || { rm -f "$T/p$n"; break; }; done
  cat "$T"/p* > "$F"
else
  curl -sS --retry 3 "$U/${C}_illustrated_master.mp4" -H "Authorization: Bearer dummy" -o "$F"
fi
rm -rf "$T"
want=$(grep "_master.mp4" "$D/SHA256SUMS" | cut -d' ' -f1); got=$(sha256sum "$F" | cut -d' ' -f1)
[ "$want" = "$got" ] && echo "$C master fetched and verified" || { echo "$C master FAILED verification"; rm -f "$F"; exit 1; }
