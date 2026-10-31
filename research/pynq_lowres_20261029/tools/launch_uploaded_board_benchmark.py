from pathlib import Path
import json,hashlib,tarfile,os,sys,subprocess
root=Path('/home/xilinx/jupyter_notebooks/cow_research_lowres_20261029');archive=root/'board_inputs.tar.gz'
assert archive.is_file() and hashlib.sha256(archive.read_bytes()).hexdigest()=='97714eeb8267cf3d6c7a34b4f6b302550f53fc036a3ba1c32c7e4a9ad568edad'
assert not (root/'launch.json').exists() and not (root/'results').exists()
with tarfile.open(archive) as tar:
    for m in tar.getmembers():
        assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
        target=(root/m.name).resolve();assert str(target).startswith(str(root.resolve())+'/');assert not target.exists()
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(m).read())
protocol=json.loads((root/'protocol.json').read_text())
for r in protocol['source_images']:assert hashlib.sha256((root/r['file']).read_bytes()).hexdigest()==r['sha256']
assert hashlib.sha256((root/'protocol.json').read_bytes()).hexdigest()=='b18fc2792de129e482ba9a74adbbe8358545c52c075e51c6f23feb71c0d90d11'
log=open(root/'benchmark.log','xb');env=os.environ.copy();env['OMP_NUM_THREADS']='2';env['OPENBLAS_NUM_THREADS']='2'
child=subprocess.Popen([sys.executable,'-u',str(root/'board_existing_benchmark.py')],stdout=log,stderr=subprocess.STDOUT,cwd=str(root),env=env,start_new_session=True)
result={'status':'OWN_BOARD_BENCHMARK_PROCESS_STARTED','PID':child.pid,'root':str(root),'python':sys.executable,
'input_archive_SHA256':hashlib.sha256(archive.read_bytes()).hexdigest(),'input_archive_bytes':archive.stat().st_size}
(root/'launch.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
