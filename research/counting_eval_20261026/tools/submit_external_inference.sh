set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026/phase2
test -s "$ROOT/results/author_gt_audit/summary.json"
test -s "$ROOT/annotations/evaluation_protocol_v1.json"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/external_inference.slurm" | tee "$ROOT/logs/external_inference_jobid.txt"
