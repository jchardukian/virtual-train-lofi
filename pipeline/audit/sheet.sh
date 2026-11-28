#!/usr/bin/env bash
# Usage: sheet.sh <dir> <out.jpg> <id>...   (max ~8 ids per sheet)
# One row per clip: 4 evenly spaced frames, labelled with the id.
dir="$1"; out="$2"; shift 2; tmp=$(mktemp -d); args=(); n=0
for id in "$@"; do
  f="$dir/$id.mp4"; [ -s "$f" ] || continue
  d=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$f")
  ffmpeg -hide_banner -loglevel error -y -i "$f" -vf "fps=4/$d,scale=400:224:force_original_aspect_ratio=decrease:force_divisible_by=2,pad=400:224:(ow-iw)/2:(oh-ih)/2,tile=4x1,drawtext=text='$id':fontcolor=yellow:fontsize=18:x=6:y=6:box=1:boxcolor=black@0.6" -frames:v 1 -q:v 4 "$tmp/$id.jpg" && { args+=(-i "$tmp/$id.jpg"); n=$((n+1)); }
done
if [ "$n" -gt 1 ]; then ffmpeg -hide_banner -loglevel error -y "${args[@]}" -filter_complex "vstack=inputs=$n" -q:v 4 "$out"; elif [ "$n" = 1 ]; then cp "$tmp"/*.jpg "$out"; fi
rm -rf "$tmp"; echo "$out ($n clips)"
