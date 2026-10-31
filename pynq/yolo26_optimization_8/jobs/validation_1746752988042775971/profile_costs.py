"""Separate sampled profiling experiment; not substituted for formal E2E."""
import pathlib,sys,time,json,fcntl,os,ctypes
sys.dont_write_bytecode=True;os.environ['OMP_NUM_THREADS']='2'
R=pathlib.Path('/home/xilinx/jupyter_notebooks');D=R/'yolo26_optimization_8';sys.path[:0]=[str(D),str(D/'runtime_fast')]
import cv2,numpy as np
from native_graph import NativeGraph
from board_runtime import decode,stats
cv2.setNumThreads(2);O=D/'reports'/('sampled_profile_'+str(time.time_ns()));O.mkdir();rows=[];reference=None;lock=(R/'yolo26_stage_d/reports/accelerator_job.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);image=cv2.imread(str(D/'test_images/bus.jpg'))
for variant,plan in [('C',None),('D','plans/r224_all/resident_plan.bin')]:
 g=NativeGraph(224,options=4|32|64,plan=plan,firmware_manifest='hardware/accepted/firmware_manifest.json')
 try:
  fs=(ctypes.c_uint64*4)();g.lib.o8_features.argtypes=[ctypes.c_void_p,ctypes.c_void_p];g.lib.o8_features(g.handle,fs);samples=[];times=[];node_samples=[]
  for i in range(203):
   st=time.perf_counter();raw=g.run_image(image);decode(raw,image.shape,size=224);ms=(time.perf_counter()-st)*1000;v,n=g.detail()
   if reference is None:reference=raw.copy()
   assert np.array_equal(reference.view(np.uint32),raw.view(np.uint32)),'sampled profile must preserve output'
   if i>=3:times.append(ms)
   if v[14]:samples.append(v.tolist());node_samples.append(n.copy())
  np.save(O/f'{variant}_sampled_nodes.npy',np.array(node_samples));np.save(O/f'{variant}_last_wall_nodes.npy',g.profile);row=dict(variant=variant,sampled_frames=len(samples),sample_period=20,options=100,features=list(fs),E2E_screen_stats=stats(times),detail_sample_mean=np.mean(samples,axis=0).tolist(),detail_samples=samples,final_timers=g.timers.tolist());rows.append(row);print('O8_PROFILE_PASS',variant,len(samples),flush=True)
 finally:g.close()
(O/'summary.json').write_text(json.dumps(dict(status='PASS',scope='low-rate gather/sync sampled diagnostics; profile option perturbation retained; never replaces uninstrumented formal E2E',rows=rows),indent=2))
