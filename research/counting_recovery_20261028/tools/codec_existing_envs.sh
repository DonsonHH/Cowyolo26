set -euo pipefail
for path in /share/home/renly/miniconda3/bin/ffmpeg /usr/local/ffmpeg/bin/ffmpeg /opt/ffmpeg/bin/ffmpeg; do
  test ! -x "$path" || printf '%s\n' "$path"
done
test ! -d /share/home/renly/miniconda3/envs || find /share/home/renly/miniconda3/envs -maxdepth 3 -path '*/bin/ffmpeg' -type f
test ! -d /share/home/renly/.imageio || find /share/home/renly/.imageio -maxdepth 3 -name '*ffmpeg*' -type f
test ! -d /share/home/renly/.cache/imageio || find /share/home/renly/.cache/imageio -maxdepth 3 -name '*ffmpeg*' -type f
