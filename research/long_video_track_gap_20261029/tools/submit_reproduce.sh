set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/long_video_track_gap_20261029
squeue -u renly -o '%.18i|%.9P|%.25j|%.8T|%.10M|%.10l|%R'
mkdir -p "$ROOT/logs"
sbatch --parsable --partition=cu --nodes=1 --ntasks=1 --cpus-per-task=2 --mem=4G --time=00:05:00 \
 --job-name=long-video-gap-repro --output="$ROOT/logs/reproduce_%j.out" --error="$ROOT/logs/reproduce_%j.err" \
 "$ROOT/tools/reproduce_job.sh"
