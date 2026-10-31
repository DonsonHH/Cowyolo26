set -euo pipefail
root=/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028
date -u
sacct -j 130214,130215,130217,130220,130221,130222,130236 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
find "$root" -maxdepth 2 -type f \( -name '*staging.json' -o -name 'media_ffmpeg*' \) -printf '%p %s bytes\n'
pgrep -a -u renly -f 'python -m pip download --no-deps --only-binary=:all: --index-url https://pypi.org/simple --dest /share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028/media_runtime_wheels' || true
