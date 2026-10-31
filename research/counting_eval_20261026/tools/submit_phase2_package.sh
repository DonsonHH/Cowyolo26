set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026/phase2
sacct -j 129669,129670,129671,129673,129675,129683,129685,129688,129689 --format=JobID,JobName%24,State,ExitCode,Elapsed,MaxRSS -P | tee "$ROOT/results/slurm_status_before_package.txt"
test "$(sacct -j 129683 -X --format=State --noheader | tr -d ' ')" = COMPLETED
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
sbatch --parsable "$ROOT/tools/package_phase2.slurm" | tee "$ROOT/logs/packaging_jobid.txt"
