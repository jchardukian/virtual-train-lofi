#!/bin/bash
# Build one illustrated city end to end, failing closed at every step.
#   pipeline/illustrated_build.sh <city> <trackA.mp3> <trackB.mp3> <vertical1_start_s> <vertical2_start_s>
# Output: output/cities/<city>/illustrated/<city>_illustrated_{master,vertical_1,vertical_2}.mp4, previews in output/samples.
set -euo pipefail
cd "$(dirname "$0")/.."
C=$1; A=$2; B=$3; V1=$4; V2=$5
DUR=${RIDE_S:-180}                              # owner 2026-11-27: 3-minute rides (was 300)
export RENDER_SCALE=${RENDER_SCALE:-2}          # 2 = 4K long-form (the standard since 23 Nov); 1 = the old 1080p
MW=$((1920 * RENDER_SCALE)); MH=$((1080 * RENDER_SCALE))
D=output/cities/$C/illustrated; O=output/samples; mkdir -p "$D"
[ "${REUSE_VIDEO:-0}" = "1" ] || rm -f "$D/${C}_illustrated_video.mp4"; rm -f "$D/${C}_illustrated_master.mp4" "$D"/${C}_illustrated_vertical_?.mp4 "$D"/*.part*.mp4 "$D/RESOLUTION"
T0=$(date +%s)
# REUSE_VIDEO=1 redoes only sound, cuts and checks, and only if the existing render's manifest proves it was made
# from exactly today's settings, code and artwork. Anything else forces a full render.
if [ "${REUSE_VIDEO:-0}" = "1" ] && python3 pipeline/render_manifest.py verify cities/illustrated/$C.json "$D/${C}_illustrated_video.mp4"; then
  echo "$C: reusing verified render"
else
  rm -f "$D/${C}_illustrated_video.mp4" "$D/${C}_illustrated_video.render.json"
  python3 pipeline/illustrated_city.py cities/illustrated/$C.json "$D/${C}_illustrated_video.mp4" 2> >(grep -v libpng >&2)
  [ -s "$D/${C}_illustrated_video.mp4" ] || { echo "RENDER FAILED for $C"; exit 1; }
  python3 pipeline/render_manifest.py write cities/illustrated/$C.json "$D/${C}_illustrated_video.mp4"
fi
[ -s "$D/${C}_illustrated_video.mp4" ] || { echo "RENDER FAILED for $C"; exit 1; }
N=$(ffprobe -v error -count_packets -select_streams v -show_entries stream=nb_read_packets -of csv=p=0 "$D/${C}_illustrated_video.mp4")
[ "$N" = "$((DUR * 30))" ] || { echo "$C: expected $((DUR * 30)) frames, got $N"; exit 1; }
ffmpeg -hide_banner -loglevel error -y -i "$D/${C}_illustrated_video.mp4" -i "$A" -i "$B" -filter_complex "[1:a]silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.1,areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.3,areverse[ta];[2:a]silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.1,areverse,silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.3,areverse[tb];[ta][tb]acrossfade=d=4:c1=tri:c2=tri[y];[y]atrim=0:$DUR,loudnorm=I=-16:TP=-1.5:LRA=11,alimiter=limit=0.6:level=false,afade=t=in:d=1.5,afade=t=out:st=$((DUR - 3)):d=3,aresample=48000[au];[0:v]fade=t=in:d=1.5,fade=t=out:st=$((DUR - 2)).5:d=1.5[v]" -map "[v]" -map "[au]" -t $DUR -c:v libx264 -preset medium -crf 18 -pix_fmt yuv420p -g 60 -c:a aac -b:a 192k -movflags +faststart "$D/${C}_illustrated_master.mp4"
i=1; for SS in $V1 $V2; do
  ffmpeg -hide_banner -loglevel error -y -ss $SS -i "$D/${C}_illustrated_master.mp4" -t 25 -filter_complex "[0:v]crop=$((608 * RENDER_SCALE)):$MH:$((656 * RENDER_SCALE)):0,scale=1080:1920:flags=lanczos,fade=t=in:d=0.5,fade=t=out:st=24.3:d=0.7[v];[0:a]afade=t=in:d=0.5,afade=t=out:st=24:d=1,loudnorm=I=-16:TP=-1.5:LRA=11,alimiter=limit=0.6:level=false,aresample=48000[a]" -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 19 -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart "$D/${C}_illustrated_vertical_$i.mp4"; i=$((i+1)); done
for f in master vertical_1 vertical_2; do pipeline/fix_peak.sh "$D/${C}_illustrated_$f.mp4"; python3 pipeline/audio_gate.py "$D/${C}_illustrated_$f.mp4" > "$D/${C}_illustrated_$f.audio.json" || { echo "$C $f: AUDIO GATE FAILED"; exit 1; }; done
python3 pipeline/qc.py "$D/${C}_illustrated_master.mp4" --no-jitter --fade 1.5 --sheet-every 15 --width $MW --height $MH >/dev/null 2>&1 || { echo "$C master: VIDEO QC FAILED"; exit 1; }
for i in 1 2; do python3 pipeline/qc.py "$D/${C}_illustrated_vertical_$i.mp4" --no-jitter --fade 0.7 --width 1080 --height 1920 --sheet-every 5 >/dev/null 2>&1 || { echo "$C vertical $i: VIDEO QC FAILED"; exit 1; }; done
ffmpeg -hide_banner -loglevel error -y -i "$D/${C}_illustrated_master.mp4" -vf scale=1280:720 -c:v libx264 -preset medium -crf 25 -maxrate 1500k -bufsize 3000k -c:a aac -b:a 128k -movflags +faststart "$O/${C}_illustrated_300s_720p.mp4"
for i in 1 2; do ffmpeg -hide_banner -loglevel error -y -i "$D/${C}_illustrated_vertical_$i.mp4" -vf scale=540:960 -c:v libx264 -preset medium -crf 24 -c:a aac -b:a 128k -movflags +faststart "$O/${C}_illustrated_vertical_${i}_540p.mp4"; done
ffmpeg -hide_banner -loglevel error -y -i "$D/${C}_illustrated_master.mp4" -vf "select='not(mod(n\,750))',scale=640:360,tile=4x3" -frames:v 1 -q:v 3 "$O/${C}_illustrated_sheet.jpg"
sha256sum "$D/${C}_illustrated_master.mp4" "$D"/${C}_illustrated_vertical_?.mp4 | tee "$D/SHA256SUMS"
echo "${MW}x${MH}" > "$D/RESOLUTION"
echo "$C BUILT OK in $(( $(date +%s)-T0 )) s; all gates passed"
