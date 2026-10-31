set -euo pipefail
for env in sd iqa pid pid310_gpu pid_author_clean; do
  file="/share/home/renly/miniconda3/envs/$env/bin/ffmpeg"
  if test -x "$file"; then
    printf '%s\n' "$file"
    "$file" -hide_banner -encoders 2>/dev/null | grep -E '264|vp9|VideoToolbox|mpeg4' || true
  fi
done
