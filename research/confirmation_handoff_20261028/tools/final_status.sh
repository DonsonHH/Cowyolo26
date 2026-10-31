set -euo pipefail
date -u
sacct -j 130241,130243,130244 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
