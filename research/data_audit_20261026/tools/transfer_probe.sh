set +e
ROOT=/share/home/renly/projects/idcoo_research_20261026
curl --noproxy '*' -sS -L --range 0-1048575 --connect-timeout 8 --max-time 20 -o "$ROOT/catalog/direct_probe.bin.partial" -w 'direct_probe:code=%{http_code},bytes=%{size_download},speed=%{speed_download},elapsed=%{time_total}\n' 'https://data.bris.ac.uk/datasets/10m32xl88x2b61zlkkgz3fml17/10m32xl88x2b61zlkkgz3fml17.zip'
printf 'curl_exit:%s\n' "$?"
tail -n 3 "$ROOT/catalog/stage_media.log"
find "$ROOT/data" -type f -printf '%s %p\n' | head -n 10
