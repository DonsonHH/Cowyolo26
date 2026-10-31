set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%.10M|%R'
sacct -j 130611,130612,130613,130614,130615,130616 -X --format=JobID,State,ExitCode,Elapsed,AllocCPUS -P
