set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026/phase2
curl --noproxy '*' -sS -fL --connect-timeout 10 --max-time 1200 --retry 2 -C - -o "$ROOT/data/mendeley_counting/Dataset_Files.zip.partial" 'https://data.mendeley.com/public-files/datasets/dk54zg67dd/files/447679ea-783a-4702-bdd8-285dab542906/file_downloaded'
test "$(stat -c%s "$ROOT/data/mendeley_counting/Dataset_Files.zip.partial")" -eq 275216868
mv -n "$ROOT/data/mendeley_counting/Dataset_Files.zip.partial" "$ROOT/data/mendeley_counting/Dataset_Files.zip"
printf 'Completed transfer, expected published SHA256 will be checked in CPU allocation\n'
