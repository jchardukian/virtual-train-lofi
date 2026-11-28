#!/bin/bash
# usage: queue_runner.sh [minutes]   builds cities one at a time from work/queue.txt (first line first), so the order
# can be edited while it runs. Stops before starting a city once fewer than 65 minutes of the budget remain, so a
# time-limited job never kills a build half way (a city takes ~40-55 min). Each city goes through build_list.sh.
cd /home/user/virtual-train-lofi
END=$(( $(date +%s) + ${1:-115} * 60 ))
while true; do
  [ $(( END - $(date +%s) )) -lt 3900 ] && { echo "=== time budget reached; rerun to continue"; break; }
  C=$(grep -m1 -v '^\s*$' work/queue.txt 2>/dev/null)
  [ -z "$C" ] && { echo "=== queue empty"; break; }
  echo "=== $C $(date -u +%FT%TZ)"
  pipeline/build_list.sh $C
  sed -i "0,/^$C\$/{/^$C\$/d}" work/queue.txt      # only removed once its build has finished or failed
done
