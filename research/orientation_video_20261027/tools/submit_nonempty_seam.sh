set -euo pipefail
project=/share/home/renly/projects/idcoo_research_20261026
stage="$project/orientation_video_20261027"
test -f "$stage/results/smoke.json"
test ! -e "$stage/results/nonempty_seam_smoke.json"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%R'
jobid=$(sbatch --parsable --job-name=idcoo-video-rot-box --partition=4gpu --nodes=1 --ntasks=1 --gres=gpu:V100S:1 --cpus-per-task=2 --mem=6G --time=00:05:00 --output="$stage/logs/box-smoke-%j.out" --error="$stage/logs/box-smoke-%j.err" --wrap="srun $project/env/bin/python $stage/tools/nonempty_seam_smoke.py")
printf '%s\n' "$jobid" > "$stage/results/nonempty_smoke_job_id.txt"
printf '%s\n' "$jobid"
