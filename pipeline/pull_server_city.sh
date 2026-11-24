#!/bin/bash
# Bring a city built on the stream server back here for review and release (not the master; release_city.py
# fetches that from the archive when uploading). Usage: pipeline/pull_server_city.sh <city>
set -uo pipefail
cd "$(dirname "$0")/.."
C=$1; D=output/cities/$C/illustrated; mkdir -p $D output/samples
U=https://lofitrain-control.jchardukian.workers.dev; K=$(cat work/secrets/control_key)
get() { curl -sS --retry 5 -f -H "X-Key: $K" "$U/obj/$1" -o "$2"; }
get control/built/$C.json /dev/null || { echo "$C not built on the server"; exit 1; }
for f in SHA256SUMS RESOLUTION ${C}_illustrated_vertical_1.mp4 ${C}_illustrated_vertical_2.mp4 ${C}_illustrated_video.render.json \
         ${C}_illustrated_master.audio.json ${C}_illustrated_vertical_1.audio.json ${C}_illustrated_vertical_2.audio.json \
         ${C}_illustrated_master.contact.jpg ${C}_illustrated_vertical_1.contact.jpg ${C}_illustrated_vertical_2.contact.jpg; do
  get $C/$f $D/$f || { echo "missing $f"; exit 1; }; done
for f in sheet.jpg 300s_720p.mp4 vertical_1_540p.mp4 vertical_2_540p.mp4; do get $C/samples/${C}_illustrated_$f output/samples/${C}_illustrated_$f; done
(cd $D && grep vertical SHA256SUMS | sed "s#output/cities/$C/illustrated/##" | sha256sum -c --quiet) && echo "$C pulled and verified"
