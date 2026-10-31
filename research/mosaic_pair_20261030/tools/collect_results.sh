set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
sacct -j 130621,130622,130628,130629,130630,130631,130632 -X --format=JobID,State,ExitCode,Elapsed,AllocCPUS -P
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import subprocess,json,hashlib,tarfile
root=Path('mosaic_pair_20261030')
for job in ['130621','130629','130630','130631','130632']:
 state=subprocess.check_output(['sacct','-j',job,'-X','--noheader','--format=State,ExitCode','-P'],text=True).strip();assert state.startswith('COMPLETED|0:0'),(job,state)
states=subprocess.check_output(['sacct','-j','130622','-X','--noheader','--format=JobID,State,ExitCode','-P'],text=True).splitlines()
assert len(states)==6 and all('|COMPLETED|0:0' in row for row in states),states
assert subprocess.check_output(['sacct','-j','130628','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip().startswith('FAILED|1:0')
summary=json.loads((root/'results/evaluation_v2/summary.json').read_text());assert summary['actual_source_image_forwards']==25350
freeze=json.loads((root/'results/all_six_checkpoints_frozen.json').read_text())
for row in freeze['models']:assert hashlib.sha256(Path(row['checkpoint']).read_bytes()).hexdigest()==row['sha256']
for row in json.loads((root/'results/evaluation_manifest_v2.json').read_text()):
 file=root/row['file'];assert file.stat().st_size==row['bytes'] and hashlib.sha256(file.read_bytes()).hexdigest()==row['sha256']
files=[root/'results/preflight.json',root/'results/all_six_checkpoints_frozen.json',root/'results/regression_diagnostic.json',root/'results/control_weight_reproduction.json',root/'results/evaluation_manifest_v2.json',
 *sorted((root/'results/training').rglob('*')),*sorted((root/'results/evaluation_v2').rglob('*')),*sorted((root/'results/media').rglob('*')),*sorted((root/'logs').glob('*'))]
files=[p for p in files if p.is_file()]
manifest=root/'results/final_transfer_manifest.json';assert not manifest.exists()
manifest.write_text(json.dumps([{'file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in files],indent=2)+'\n')
archive=root/'paired_results_delivery_v1.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for p in [manifest,*files]:tar.add(p,arcname=p.relative_to(root).as_posix(),recursive=False)
print(json.dumps({'archive':str(archive.resolve()),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'files':len(files)+1,
 'all6_training_main_jobs_completed':True,'training_stderr_all_clean':False,'failed_evaluation_preserved':True}))
PY
