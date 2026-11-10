from pathlib import Path
import json,os,subprocess,sys
p=Path(__file__).resolve().parent
def save(value):
 t=p/'software_status.writing';t.write_text(json.dumps(value)+'\n');t.replace(p/'software_status.json')
save({'status':'RUNNING','PID':os.getpid()})
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
 PYTHONPATH=str(p)+':/home/xilinx/jupyter_notebooks/cow_research_numpy_tracker_20261029/source/lap-0.5.13')
with (p/'software_tests.log').open('xb') as log:
 child=subprocess.run([sys.executable,'-m','unittest','discover','-s','counting','-t','.','-v'],
   cwd=p,env=env,stdout=log,stderr=subprocess.STDOUT)
save({'status':'COMPLETED' if child.returncode==0 else 'FAILED','exit_code':child.returncode,
      'new_model_forwards':0,'software_fixtures_only':True})
raise SystemExit(child.returncode)
