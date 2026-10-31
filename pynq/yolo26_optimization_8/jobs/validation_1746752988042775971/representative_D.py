import pathlib,sys,os,time,json,hashlib,fcntl,traceback,shutil
sys.dont_write_bytecode=True;os.environ['OMP_NUM_THREADS']='2'
R=pathlib.Path('/home/xilinx/jupyter_notebooks');D=R/'yolo26_optimization_8';sys.path[:0]=[str(D),str(D/'runtime_fast')]
import numpy as np,cv2
from native_graph import NativeGraph
from board_runtime import decode,annotate,stats
cv2.setNumThreads(2);inputs=json.loads((D/'test_images/representative100.json').read_text());chosen=json.loads((D/'selected_candidates.json').read_text());base=D/'reports/representative_A_B_1746749722398861404';O=D/'reports'/('representative_D_resumed_'+str(time.time_ns()));O.mkdir();records=[];resume=D/'reports/representative_D_1746752619997064150'
if resume.exists():
 for p in resume.glob('r*_per_image.jsonl'):shutil.copy2(p,O/p.name)
lock=(R/'yolo26_stage_d/reports/accelerator_job.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
try:
 for size in (192,224,256):
  prior=O/f'r{size}_per_image.jsonl';oldrows=list(map(json.loads,prior.read_text().splitlines())) if prior.exists() else [];done={r['image_id'] for r in oldrows};assert len(done)==len(oldrows) and done<=set(r['id'] for r in inputs['images']);rows=[{k:v for k,v in r.items() if k!='tensor_hashes'} for r in oldrows]
  if len(done)==100:
   rec=json.loads((resume/f'r{size}_summary.json').read_text());records.append(rec);(O/f'r{size}_summary.json').write_text(json.dumps(rec,indent=2));print('O8_REUSED_COMPLETED_REPRESENTATIVE',size,100,flush=True);continue
  selection=chosen[str(size)]['selection'];plan=f'plans/r{size}_{selection}/resident_plan.bin';refs={r['image_id']:r for r in map(json.loads,(base/f'r{size}_per_image.jsonl').read_text().splitlines())};g=NativeGraph(size,options=4,plan=plan,firmware_manifest='hardware/accepted/firmware_manifest.json');mirror=NativeGraph(size,options=4,plan=plan,firmware_manifest='hardware/accepted/firmware_manifest.json',debug_mirror=True)
  try:
   for i,item in enumerate(inputs['images']):
    if item['id'] in done:continue
    im=cv2.imread(str(D/'test_images/representative100'/item['file_name']));ref=refs[item['id']];expected_raw=np.load(base/f'r{size}_{item["id"]}_raw.npy');st=time.perf_counter();raw=g.run_image(im).copy();boxes=decode(raw,im.shape,size=size);ms=(time.perf_counter()-st)*1000
    assert np.array_equal(raw.view(np.uint32),expected_raw.view(np.uint32)) and np.array_equal(boxes,decode(expected_raw,im.shape,size=size)),(size,item['id'],'normal raw/boxes')
    actual=mirror.run_image(im).copy();assert np.array_equal(actual.view(np.uint32),expected_raw.view(np.uint32)),(size,item['id'],'mirror raw')
    hashes={};elements=0
    for n in mirror.meta['nodes']:
     for name in n['outputs']:
      v=mirror.tensor(name);h=hashlib.sha256(v.tobytes()).hexdigest();assert h==ref['tensor_hashes'][name],(size,item['id'],name);hashes[name]=h;elements+=v.size
    row=dict(size=size,image_id=item['id'],tensors=len(hashes),elements=elements,mismatches=0,D_E2E_ms=ms,A_E2E_ms=ref['E2E_ms']['A'],tensor_hashes=hashes,raw_sha256=hashlib.sha256(raw.tobytes()).hexdigest(),actual_midstream_mirror=True,detections=len(boxes));rows.append({k:v for k,v in row.items() if k!='tensor_hashes'})
    with (O/f'r{size}_per_image.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
    if i in (0,9,49,99):cv2.imwrite(str(O/f'r{size}_{item["id"]}_detected.jpg'),annotate(im,boxes))
    if (i+1)%20==0:print('O8_REPRESENTATIVE_D',size,i+1,'actual midstream + all411 tensors exact',flush=True)
   rec=dict(size=size,selection=selection,images=len(rows),tensors=sum(v['tensors'] for v in rows),elements=sum(v['elements'] for v in rows),mismatches=0,A=stats([v['A_E2E_ms'] for v in rows]),D=stats([v['D_E2E_ms'] for v in rows]),rows=rows);records.append(rec);(O/f'r{size}_summary.json').write_text(json.dumps(rec,indent=2))
  finally:g.close();mirror.close()
 result=dict(status='PASS',records=records,reference=str(base),resumed_from=str(resume) if resume.exists() else None,reused_verified_images=sum(1 for p in resume.glob('r*_per_image.jsonl') for _ in p.open()) if resume.exists() else 0,scope='100 distinct same real images each size; actual O8 mirror vs frozen O7 board tensor SHA; D timing normal non-mirror, phased representative comparison; retained SSH BrokenPipe run and its extra cold frame')
except BaseException:
 result=dict(status='FAIL',records=records,failure=traceback.format_exc());raise
finally:(O/'summary.json').write_text(json.dumps(result,indent=2));print('O8_REPRESENTATIVE_D_REPORT',O,flush=True)
