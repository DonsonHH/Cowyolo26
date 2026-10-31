set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026/phase2
mkdir -p "$ROOT/data/mendeley_counting" "$ROOT/logs"
curl --noproxy '*' -sS -fL --connect-timeout 10 --max-time 45 -o "$ROOT/data/mendeley_counting/description.pdf.partial" 'https://data.mendeley.com/public-files/datasets/dk54zg67dd/files/10f85eea-c352-4e28-aee8-0f209e09f05e/file_downloaded'
test "$(stat -c%s "$ROOT/data/mendeley_counting/description.pdf.partial")" -eq 587297
mv -n "$ROOT/data/mendeley_counting/description.pdf.partial" "$ROOT/data/mendeley_counting/description.pdf"
curl --noproxy '*' -sS -fL --range 0-1048575 --connect-timeout 10 --max-time 20 -o "$ROOT/data/mendeley_counting/direct_probe.bin.partial" -w 'direct_probe:code=%{http_code},bytes=%{size_download},speed=%{speed_download},elapsed=%{time_total}\n' 'https://data.mendeley.com/public-files/datasets/dk54zg67dd/files/447679ea-783a-4702-bdd8-285dab542906/file_downloaded'
