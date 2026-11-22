#!/usr/bin/env bash
# Usage: fetch_pexels.sh <outdir> <pexels_video_id>...
# Finds the best available file for each Pexels video id on the public CDN,
# downloads it (max 250 MB), and prints: id width height fps duration url
out="$1"; shift; mkdir -p "$out"
for id in "$@"; do
  if [ ! -s "$out/$id.mp4" ]; then
    found=""
    for res in uhd_3840_2160 hd_1920_1080 uhd_2560_1440 uhd_4096_2160 uhd_2732_1440 hd_2048_1080 uhd_2160_3840 hd_1080_1920 uhd_1440_2560 uhd_2160_4096 hd_1280_720 sd_960_540 sd_640_360; do
      for fps in 30 25 24 60 50; do
        u="https://videos.pexels.com/video-files/$id/$id-${res}_${fps}fps.mp4"
        c=$(curl -s -m 12 -r 0-99 -o /dev/null -w "%{http_code}" -A "Mozilla/5.0" "$u")
        if [ "$c" = "206" ] || [ "$c" = "200" ]; then found="$u"; break 2; fi
      done
    done
    if [ -z "$found" ]; then echo "$id UNRESOLVED"; continue; fi
    curl -s -m 400 --max-filesize 250000000 -A "Mozilla/5.0" -o "$out/$id.mp4" "$found" || { rm -f "$out/$id.mp4"; echo "$id DOWNLOAD_FAILED $found"; continue; }
    echo "$found" > "$out/$id.url"
  fi
  meta=$(ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate:format=duration -of csv=p=0 "$out/$id.mp4" 2>/dev/null | tr '\n' ',' )
  if [ -z "$meta" ]; then echo "$id NOT_PLAYABLE"; continue; fi
  echo "$id $meta $(cat "$out/$id.url" 2>/dev/null)"
done
