#!/bin/bash
# Build cities on the stream server, independently of the agent's workspace.
#   server_build.sh setup              fetch the code/art bundle, install tools
#   server_build.sh run city1 city2 …  build each (skipping cities already claimed or built), upload results
# Results go to the private archive under <city>/ (same layout as archive_city.sh) plus control/built/<city>.json.
set -uo pipefail
U=https://lofitrain-control.jchardukian.workers.dev; K=$(cat /etc/lofitrain/key); R=/home/user/virtual-train-lofi
get() { curl -sS --retry 5 -f -H "X-Key: $K" "$U/obj/$1" -o "$2"; }
put() { curl -sS --retry 5 -f -X PUT -H "X-Key: $K" --data-binary @"$1" "$U/obj/$2" -o /dev/null; }
exists() { curl -sS -o /dev/null -w "%{http_code}" -H "X-Key: $K" -H "Range: bytes=0-0" "$U/obj/$1" | grep -q 20; }
if [ "$1" = setup ]; then
  mkdir -p $R /tmp/b && cd /tmp/b
  get build/SUMS SUMS; for p in $(awk '{print $2}' SUMS); do get build/$p $p; done
  sha256sum -c SUMS --quiet || { echo "bundle verify FAILED"; exit 1; }
  cat bundle.tar.part* | tar -x -C $R && rm -f bundle.tar.part*
  apt-get install -y -q python3-pip >/dev/null
  pip3 install -q --break-system-packages torch --index-url https://download.pytorch.org/whl/cpu && pip3 install -q --break-system-packages spandrel
  echo "setup OK"; exit 0
fi
shift; cd $R
for C in "$@"; do
  exists control/built/$C.json && { echo "$C already built"; continue; }
  exists control/claim/$C && { echo "$C claimed elsewhere"; continue; }
  echo server > /tmp/claim; put /tmp/claim control/claim/$C
  python3 pipeline/upscale_art.py $C --threads 4 | tail -1 || { echo "$C UPSCALE FAILED"; continue; }
  read A B < <(python3 -c "import json;u=json.load(open('data/music/used.json'))['$C']['files'];print(u[0],u[1])")
  OUT=$(RENDER_SCALE=2 pipeline/illustrated_build.sh $C $A $B 2 150 2>&1); echo "$OUT" | tail -3
  echo "$OUT" | grep -q "BUILT OK" || { echo "$C FAILED"; continue; }
  D=output/cities/$C/illustrated; ok=1
  for f in $D/${C}_illustrated_vertical_1.mp4 $D/${C}_illustrated_vertical_2.mp4 $D/SHA256SUMS $D/*.audio.json $D/*.contact.jpg $D/RESOLUTION $D/${C}_illustrated_video.render.json; do put $f $C/$(basename $f) || ok=0; done
  T=$(mktemp -d); split -b 200M -d $D/${C}_illustrated_master.mp4 $T/${C}_illustrated_master.mp4.part
  for p in $T/*; do put $p $C/$(basename $p) || ok=0; done; rm -rf $T
  for f in output/samples/${C}_illustrated_*; do put $f $C/samples/$(basename $f) || ok=0; done
  [ $ok = 1 ] || { echo "$C UPLOAD FAILED"; continue; }
  echo "{\"city\":\"$C\",\"built_by\":\"server\",\"time\":\"$(date -u +%FT%TZ)\"}" > /tmp/done; put /tmp/done control/built/$C.json
  rm -f $D/${C}_illustrated_master.mp4 $D/${C}_illustrated_video.mp4
  echo "$C SERVER BUILT OK"
done
