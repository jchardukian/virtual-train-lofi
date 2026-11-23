#!/bin/bash
# usage: build_list.sh city1 city2 ...   builds each with its picked music (skipping ones already built from the
# current settings), then archives it privately. Waits for any other build to finish first.
cd /home/user/virtual-train-lofi
while pgrep -f "illustrated_build.sh" >/dev/null; do sleep 20; done
for c in "$@"; do
  R=output/cities/$c/illustrated/RESOLUTION
  if [ -f $R ] && [ "$(cat $R)" = "$((1920 * ${RENDER_SCALE:-2}))x$((1080 * ${RENDER_SCALE:-2}))" ] && [ $R -nt cities/illustrated/$c.json ]; then echo "$c already built"; continue; fi
  if [ "${RENDER_SCALE:-2}" != "1" ]; then U=$(python3 pipeline/upscale_art.py $c 2>&1) || { echo "$c ART UPSCALE FAILED"; continue; }; echo "$U" | tail -1; fi
  read A B < <(python3 -c "import json;u=json.load(open('data/music/used.json'))['$c']['files'];print(u[0],u[1])")
  OUT=$(pipeline/illustrated_build.sh $c $A $B 2 150 2>&1); echo "$OUT" | grep -E "BUILT OK|FAILED|expected"
  if echo "$OUT" | grep -q "BUILT OK"; then pipeline/archive_city.sh $c | tail -1 | tee /dev/stderr | grep -q " archived$" && rm -f output/cities/$c/illustrated/${c}_illustrated_video.mp4; else echo "$c FAILED"; fi
done
