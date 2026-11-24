#!/bin/bash
# lofi-agent: runs on the stream server. Every 30 s it fetches the current command from the control Worker; a new
# command id is run once (in the background, so a running stream never blocks the next check), and its output is
# posted back to control/out/<id>.log. A heartbeat goes to control/status.json. No inbound ports are needed.
U=https://lofitrain-control.jchardukian.workers.dev
K=$(cat /etc/lofitrain/key)
S=/var/lib/lofitrain; mkdir -p $S/out; cd $S
put() { curl -sS -m 120 -X PUT -H "X-Key: $K" --data-binary @"$2" "$U/obj/control/$1" >/dev/null; }
while true; do
  c=$(curl -sS -m 30 -H "X-Key: $K" "$U/cmd")
  id=$(printf '%s' "$c" | python3 -c "import json,sys;print(json.load(sys.stdin).get('id',''))" 2>/dev/null)
  if [ -n "$id" ] && [ ! -e "$S/out/$id.started" ]; then
    touch "$S/out/$id.started"
    printf '%s' "$c" | python3 -c "import json,sys;print(json.load(sys.stdin)['script'])" > "$S/out/$id.sh"
    ( bash "$S/out/$id.sh" > "$S/out/$id.log" 2>&1; echo "EXIT $?" >> "$S/out/$id.log"; put "out/$id.log" "$S/out/$id.log" ) &
  fi
  for f in $S/out/*.log; do [ -e "$f" ] && put "out/$(basename $f)" "$f"; done 2>/dev/null
  { echo "{\"time\":\"$(date -u +%FT%TZ)\",\"uptime\":\"$(uptime -p)\",\"load\":\"$(cut -d' ' -f1-3 /proc/loadavg)\",";
    echo "\"disk_free\":\"$(df -h / | awk 'NR==2{print $4}')\",\"ffmpeg_running\":$(pgrep -c ffmpeg || true)}"; } > $S/status.json
  put status.json $S/status.json
  sleep 30
done
