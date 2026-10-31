set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026/phase2
test -s "$ROOT/data/mendeley_counting/selected_compressed/members_manifest.json"
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/unpack_audit.slurm" | tee "$ROOT/logs/external_audit_jobid.txt"
