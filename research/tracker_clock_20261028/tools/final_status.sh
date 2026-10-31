set -euo pipefail
date -u
sacct -j 130238,130239,130240 --format=JobID,State,ExitCode,Elapsed,MaxRSS -P
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
