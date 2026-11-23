#!/bin/bash
# usage: build_list.sh city1 city2 ...   builds each with its picked music (skipping ones already built from the
# current settings), then archives it privately. Waits for any other build to finish first.
cd /home/user/virtual-train-lofi
while pgrep -f "illustrated_build.sh" >/dev/null; do sleep 20; done
for c in "$@"; do
  if [ -f output/cities/$c/illustrated/SHA256SUMS ] && [ output/cities/$c/illustrated/SHA256SUMS -nt cities/illustrated/$c.json ]; then echo "$c already built"; continue; fi
  read A B < <(python3 -c "import json;u=json.load(open('data/music/used.json'))['$c']['files'];print(u[0],u[1])")
  if pipeline/illustrated_build.sh $c $A $B 2 150 2>&1 | grep -E "BUILT OK|FAILED|expected"; then pipeline/archive_city.sh $c | tail -1 | tee /dev/stderr | grep -q " archived$" && rm -f output/cities/$c/illustrated/${c}_illustrated_video.mp4; else echo "$c FAILED"; fi
done
