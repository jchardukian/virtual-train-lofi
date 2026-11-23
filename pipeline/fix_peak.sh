#!/bin/bash
# If a video's audio true peak is above -1.5 dBFS, turn the audio down just enough (picture copied untouched).
# Usage: pipeline/fix_peak.sh <video.mp4>
F=$1
P=$(ffmpeg -hide_banner -i "$F" -vn -af ebur128=peak=true -f null - 2>&1 | grep -A1 "True peak" | tail -1 | awk '{print $2}')
G=$(python3 -c "p=float('$P');print(round(-1.5-1.0-p,2) if p>-1.5 else 0)")
[ "$G" = "0" ] && exit 0
ffmpeg -hide_banner -loglevel error -y -i "$F" -map 0:v -map 0:a -c:v copy -af "volume=${G}dB" -c:a aac -b:a 192k -movflags +faststart "${F%.mp4}.peakfix.mp4" && mv "${F%.mp4}.peakfix.mp4" "$F" && echo "  $(basename "$F"): peak $P dBFS, audio lowered ${G} dB"
