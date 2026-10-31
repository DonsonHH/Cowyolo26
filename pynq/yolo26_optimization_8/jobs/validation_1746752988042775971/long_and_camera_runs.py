import pathlib,time,subprocess,json,os,sys
sys.dont_write_bytecode=True
R=pathlib.Path('/home/xilinx/jupyter_notebooks');D=R/'yolo26_optimization_8';tag=str(time.time_ns());records=[];chosen=json.loads((D/'selected_candidates.json').read_text())
for label,size,fixed,camera in [('continuous1000',224,1000,0),('fast192_camera100',192,100,100),('flagship224_camera100',224,100,100),('quality256_fixed100',256,100,0)]:
 out=D/'reports'/f'{label}_{tag}';log=out.with_suffix('.log');selection=chosen[str(size)]['selection'];cmd=[sys.executable,'-B',str(D/'run_board.py'),'--size',str(size),'--fixed',str(fixed),'--camera',str(camera),'--warmups','3','--plan',f'plans/r{size}_{selection}/resident_plan.bin','--firmware-manifest','hardware/accepted/firmware_manifest.json','--output',str(out)]
 with log.open('w') as f:p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env={**os.environ,'OMP_NUM_THREADS':'2','PYTHONDONTWRITEBYTECODE':'1'})
 assert p.returncode==0,log.read_text()[-4000:]
 s=json.loads((out/'summary.json').read_text());assert s['status']=='PASS' and s['BO_stable'] and s['BO_returned_to_initial'];records.append(dict(label=label,size=size,output=str(out),status=s['status'],fixed_frames=len(s['fixed']),camera_frames=len(s['camera']),fixed_statistics=s.get('fixed_statistics'),camera_statistics=s.get('camera_statistics'),BO_stable=s['BO_stable'],BO_returned_to_initial=s['BO_returned_to_initial']));(D/'reports'/f'long_camera_progress_{tag}.json').write_text(json.dumps(records,indent=2));print('O8_STABILITY_PHASE_PASS',label,json.dumps({k:v for k,v in records[-1].items() if 'statistics' not in k}),flush=True)
(D/'reports'/f'long_camera_summary_{tag}.json').write_text(json.dumps(dict(status='PASS',records=records),indent=2));print('O8_LONG_CAMERA_ALL_PASS',flush=True)
