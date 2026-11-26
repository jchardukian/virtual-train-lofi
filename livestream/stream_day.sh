#!/bin/bash
# On a stream server: build one day's ~4 h stream and send it to YouTube at the scheduled time.
#   stream_day.sh <day> <start UTC, e.g. 2026-11-26T04:15:00Z>
# Needs control/pkg/stream.tgz (pipeline code + approved music) and /var/lib/lofitrain/rtmp_<day> (written by the agent
# after it creates the broadcast; holds the stream key, never logged). Logs to /var/lib/lofitrain/out/stream_<day>.log.
set -uo pipefail
DAY=$1; START=$2; R=/home/user/virtual-train-lofi; cd $R
K=$(cat /etc/lofitrain/key); U=https://lofitrain-control.jchardukian.workers.dev/obj/control/pkg
curl -sf -H "X-Key: $K" $U/stream.tgz | tar xzf - || { echo "no stream package"; exit 1; }
CITIES=$(ls cities/illustrated/*.json | xargs -n1 basename | sed 's/.json//' | grep -vE '^(denver_v1|tokyo_v1|street_lines|alps|denver)$')
# cities whose fixed version is not built yet stay out of this stream (one name per line)
[ -f livestream/exclude_$DAY.txt ] && CITIES=$(echo "$CITIES" | grep -vxF -f livestream/exclude_$DAY.txt)
python3 pipeline/livestream_build.py prep $CITIES
python3 pipeline/livestream_build.py plan $DAY --minutes 240
python3 pipeline/livestream_build.py trans $DAY
python3 pipeline/livestream_build.py audio $DAY
python3 pipeline/livestream_build.py assemble $DAY || { echo "ASSEMBLE FAILED"; exit 1; }
echo "STREAM FILE READY"
# wait for the key and the start time
until [ -s /var/lib/lofitrain/rtmp_$DAY ]; do sleep 30; done
T=$(( $(date -d "$START" +%s) - 60 )); while [ $(date +%s) -lt $T ]; do sleep 20; done
echo "STREAMING $(date -u +%FT%TZ)"
ffmpeg -v error -re -i work/stream/$DAY/stream.mp4 -c:v copy -c:a aac -ar 48000 -ac 2 -b:a 160k -f flv "$(cat /var/lib/lofitrain/rtmp_$DAY)"
echo "STREAM ENDED $(date -u +%FT%TZ) exit $?"
