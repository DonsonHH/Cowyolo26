import pathlib,json,subprocess,sys,time,os,traceback
J=pathlib.Path(__file__).resolve().parent;D=J.parents[1];steps=['representative_D.py', 'long_and_camera_runs.py', 'profile_costs.py', 'board_recovery_test.py', 'rebuild_native_board.py'];records=[];P=D/'reports'/(J.name+'_status.json')
def save(status,**more):P.write_text(json.dumps(dict(status=status,job=str(J),PID=os.getpid(),steps=records,**more),indent=2))
try:
 for name in steps:
  log=J/(name+'.log');save('RUNNING',current=name,log=str(log))
  with log.open('w') as f:p=subprocess.run([sys.executable,'-B',str(J/name)],stdout=f,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL,env={**os.environ,'OMP_NUM_THREADS':'2','XILINX_XRT':'/usr','PYTHONDONTWRITEBYTECODE':'1'})
  records.append(dict(step=name,exit=p.returncode,log=str(log)));assert p.returncode==0,log.read_text()[-5000:]
 save('PASS')
except BaseException:save('FAIL',failure=traceback.format_exc());raise
