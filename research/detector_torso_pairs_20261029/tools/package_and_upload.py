from pathlib import Path
import json,hashlib,tarfile,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    paths=[]
    for folder in ['data','input','protocol','tools']:
        paths.extend(sorted(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts))
    paths.append(ROOT/'results/geometry_preflight.json')
    members=[{'relative_file':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in paths]
    manifest=ROOT/'input/staging_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps(members,indent=2)+'\n')
    archive=ROOT/'stage_inputs.tar.gz';assert not archive.exists()
    with tarfile.open(archive,'w:gz') as tar:
        for p in [*paths,manifest]:tar.add(p,arcname=p.relative_to(ROOT).as_posix(),recursive=False)
    evidence=ROOT/'evidence';evidence.mkdir(exist_ok=True)
    (evidence/'input_transfer.json').write_text(json.dumps({'archive':str(archive.resolve()),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(paths)+1},indent=2)+'\n')
    print(json.dumps({'archive_sha256':sha(archive),'bytes':archive.stat().st_size,'members':len(paths)+1}),flush=True)
    subprocess.run([sys.executable,str(PROJECT/'data_audit_20261026/tools/remote_bridge.py'),'put',str(archive),REMOTE+'/detector_torso_pairs_20261029_inputs.tar.gz'],check=True)
    cmd="""set -euo pipefail
test "$(id -un)" = renly
test "$(hostname)" = mu01
test "$HOME" = /share/home/renly
cd /share/home/renly/projects/idcoo_research_20261026
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,json,tarfile
project=Path('/share/home/renly/projects/idcoo_research_20261026');archive=project/'detector_torso_pairs_20261029_inputs.tar.gz'
assert hashlib.sha256(archive.read_bytes()).hexdigest()=='ARCHIVE_SHA'
out=project/'detector_torso_pairs_20261029';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    for item in tar.getmembers():
        assert item.isfile() and not item.name.startswith('/') and '..' not in Path(item.name).parts
        target=(out/item.name).resolve();assert target.is_relative_to(out.resolve());target.parent.mkdir(parents=True,exist_ok=True)
        assert not target.exists();target.write_bytes(tar.extractfile(item).read())
for row in json.loads((out/'input/staging_manifest.json').read_text()):
    file=out/row['relative_file'];assert file.stat().st_size==row['bytes'] and hashlib.sha256(file.read_bytes()).hexdigest()==row['sha256']
(out/'logs').mkdir(exist_ok=False)
print('STAGE_VERIFIED')
PY
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%R'
sbatch --parsable detector_torso_pairs_20261029/tools/study.slurm
""".replace('ARCHIVE_SHA',sha(archive))
    script=ROOT/'tools/submit_generated.sh';assert not script.exists();script.write_text(cmd,encoding='utf-8',newline='\n')
    subprocess.run([sys.executable,str(PROJECT/'data_audit_20261026/tools/remote_bridge.py'),'run',str(script),'--output',str(evidence/'submit.txt')],check=True)
if __name__=='__main__':main()
