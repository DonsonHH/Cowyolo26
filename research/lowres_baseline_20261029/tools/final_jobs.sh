set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
sacct -j 130501,130502,130503,130504,130505 --format=JobID,JobName,Partition,State,ExitCode,Elapsed,AllocCPUS,ReqMem,MaxRSS -P
if [ ! -e /share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029 ]; then printf '%s\n' 'DETECTOR_FACTORIAL_REMOTE_DIRECTORY_NOT_CREATED_NO_NEW_TRAINING_ARTIFACTS'; fi
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
