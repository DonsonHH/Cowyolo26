set -euo pipefail
date -u
sacct -j 130293,130294 --format=JobID,State,ExitCode,Elapsed,Partition,AllocCPUS,ReqMem,AllocTRES,NodeList -P
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
