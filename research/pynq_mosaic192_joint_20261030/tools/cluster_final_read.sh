set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
sacct -j 130634,130635,130636 -X --format=JobID,State,ExitCode,Elapsed,AllocCPUS -P
