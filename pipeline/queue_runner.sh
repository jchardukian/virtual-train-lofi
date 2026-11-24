#!/bin/bash
# usage: queue_runner.sh   builds cities one at a time from work/queue.txt (first line first), so the order can be
# edited while it runs. Each city goes through build_list.sh (build, archive, delete local master).
cd /home/user/virtual-train-lofi
while true; do
  C=$(grep -m1 -v '^\s*$' work/queue.txt 2>/dev/null) || break
  [ -z "$C" ] && break
  sed -i "0,/^$C\$/{/^$C\$/d}" work/queue.txt
  echo "=== $C $(date -u +%FT%TZ)"
  pipeline/build_list.sh $C
done
echo "=== queue empty $(date -u +%FT%TZ)"
