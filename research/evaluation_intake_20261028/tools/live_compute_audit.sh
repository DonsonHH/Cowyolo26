set -euo pipefail
id -un
hostname
printenv HOME
sinfo -o '%P|%a|%D|%t|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%R'
sacct -j 129998,129999,130000,130002,130003,130004,130005 --format=JobID,JobName%24,State,ExitCode,Elapsed -P
