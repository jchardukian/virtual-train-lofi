#!/bin/bash
# usage: build_list.sh city1 city2 ...   builds each with its picked music, skipping cities already built OK
cd /home/user/virtual-train-lofi
for c in "$@"; do
  [ -f output/cities/$c/illustrated/SHA256SUMS ] && [ output/cities/$c/illustrated/SHA256SUMS -nt cities/illustrated/$c.json ] && { echo "$c already built"; continue; }
  read A B < <(python3 -c "import json;u=json.load(open('data/music/used.json'))['$c']['files'];print(u[0],u[1])")
  pipeline/illustrated_build.sh $c $A $B 2 150 || echo "$c FAILED"
done
