set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/composition_control
ids=129831,129832,129835,129836,129838,129840,129841,129842,129844,129847,129848,129849
sacct -j "$ids" --format=JobID,JobName%28,State,ExitCode,Elapsed,MaxRSS,ReqMem,NodeList
if test -f "$ROOT/delivery_bundle.json"; then cat "$ROOT/delivery_bundle.json";fi
for stage in freeze infer collect; do job=$(cat "$ROOT/logs/${stage}_job_id.txt"); if test -f "$ROOT/logs/${stage}-${job}.err"; then printf "%s\n" "${stage} stderr"; cat "$ROOT/logs/${stage}-${job}.err";fi;done
