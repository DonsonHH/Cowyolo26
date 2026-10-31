set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
sacct -j 130637,130638,130639,130641 -X --format=JobID,State,ExitCode,Elapsed,AllocCPUS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json,tarfile,subprocess
root=Path('unconfirmed_iou_20261030')
state=subprocess.check_output(['sacct','-j','130641','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('COMPLETED|0:0'),state
s=json.loads((root/'results/one_frame_causal_summary.json').read_text());assert s['original_count']==10 and s['one_frame_diagnostic_count']==11
assert s['all_earlier_observations_boxes_and_events_exact'] and s['frame_specific_intervention_is_diagnostic_not_a_deployment_rule']
files=[root/p for p in ['results/one_frame_causal_summary.json','results/one_frame_causal_trace.json.gz','tools/probe_one_frame.py',
 'protocol/one_frame_causal_v1.json','logs/one-frame-130641.out','logs/one-frame-130641.err']]
manifest=root/'causal_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps([{'file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],indent=2)+'\n')
a=root/'causal_delivery_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz') as tar:
 for f in [*files,manifest]:tar.add(f,arcname=f.relative_to(root).as_posix(),recursive=False)
print(json.dumps({'archive':str(a.resolve()),'bytes':a.stat().st_size,'sha256':hashlib.sha256(a.read_bytes()).hexdigest(),'members':len(files)+1}))
print(json.dumps({'status':s['status'],'before':s['original_count'],'diagnostic_after':s['one_frame_diagnostic_count'],'all_pre9550_states_exact':s['all_earlier_observations_boxes_and_events_exact']}))
PY
