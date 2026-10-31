from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
from collections import defaultdict
import json,hashlib,tarfile,math
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
record=load(ROOT/'evidence/collection_v2.json');assert record['exit_code']==0;m=json.loads(record['stdout']);a=ROOT/'input_cost_delivery_v2.tar.gz'
assert a.stat().st_size==m['bytes'] and sha(a)==m['sha256']
out=ROOT/'delivery_v2';out.mkdir(exist_ok=False)
with tarfile.open(a) as tar:
 members=tar.getmembers();assert len(members)==m['members']
 for item in members:
  name=PurePosixPath(item.name);assert item.isfile() and not name.is_absolute() and '..' not in name.parts
  f=out.joinpath(*name.parts).resolve();assert f.is_relative_to(out.resolve()) and not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(item).read())
for r in load(out/'result_manifest.json'):assert sha(out/r['file'])==r['sha256'] and (out/r['file']).stat().st_size==r['bytes']
p=load(out/'protocol.json');s=load(out/'results/record.json');t=load(out/'results/terminal.json');final=load(out/'final_state.json')
assert sha(out/'protocol.json')==sha(ROOT/'protocol/run_v2.json') and sha(out/'board_benchmark_v2.py')==p['runner_sha256']==sha(ROOT/'tools/board_benchmark_v2.py')
assert s['status']==t['status']=='ALL256_JPEG_READ_CASES128_REAL_O8_AFTER_READS_AND16_RAW_IMAGES_COMPLETE' and t['record_sha256']==sha(out/'results/record.json')
assert s['actual_O8_forwards']==128 and s['actual_qualification_forwards']==8 and s['actual_warmups']==2 and len(s['rows'])==256
assert t['close_error'] is None and not final['proc_exists'] and final['lock_available'] and final['services']=={'22':True,'9090':True} and final['PL_bit_sha256']==p['O8_bit_sha256']
for mode in p['modes']:assert load(out/'results'/('rows_'+mode+'.json'))==[r for r in s['rows'] if r['mode']==mode]
keys=set();groups=defaultdict(list);sources={r['frame0']:r for r in p['source_rows']};old=np.load(PROJECT/'pynq_mosaic192_eval_20261030/board_delivery/results/original/all_raw.npy',mmap_mode='r')
with np.load(out/'results/all16_actual_raw.npz') as ar:
 assert set(ar['frame0'])==set(sources);raws={int(f):raw for f,raw in zip(ar['frame0'],ar['raw'])}
 for frame,raw in raws.items():assert raw.tobytes()==old[frame//5].tobytes()
 for row in s['rows']:
  key=tuple(row[k] for k in ['mode','repeat','frame0','method','cache_request']);assert key not in keys;keys.add(key)
  r=sources[row['frame0']];assert row['JPEG_bytes']==r['camera_bytes'] and row['JPEG_sha256']==r['camera_sha256']
  assert row['JPEG_wall_ms']>=0 and row['JPEG_process_CPU_ms']>=0 and row['device_read_sectors_delta']>=0
  for k in ['residency_before','residency_after']:
   c=row[k];assert c['pages']==math.ceil(r['camera_bytes']/c['page_size']) and 0<=c['resident_pages']<=c['pages']
  if row['mode']=='after_actual_O8':assert row['actual_raw_sha256']==hashlib.sha256(raws[row['frame0']][None].tobytes()).hexdigest() and row['network_ms']>0
  else:assert row['network_ms'] is None and row['actual_raw_sha256'] is None
  assert row['process_IO_bytes_unavailable'] is True and row['pickle_bytes_length']>row['JPEG_bytes']
  groups[(row['mode'],row['method'],row['cache_request'])].append(row)
summary=[]
for (mode,method,cache),rows in sorted(groups.items()):
 assert len(rows)==32
 item={'mode':mode,'method':method,'cache_request':cache,'rows':len(rows)}
 for key in ['JPEG_wall_ms','JPEG_process_CPU_ms','freeze_to_immutable_bytes_ms','pickle_bytes_wall_ms','instrumented_outer_wall_ms']:
  values=[r[key] for r in rows];item[key]={'mean':float(np.mean(values)),'P50':float(np.quantile(values,.5)),'P95':float(np.quantile(values,.95)),'min':min(values),'max':max(values)}
 item.update({'all_before_pages_resident':sum(r['residency_before']['resident_pages']==r['residency_before']['pages'] for r in rows),
  'before_nonresident_pages_total':sum(r['residency_before']['pages']-r['residency_before']['resident_pages'] for r in rows),
  'after_nonresident_pages_total':sum(r['residency_after']['pages']-r['residency_after']['resident_pages'] for r in rows),
  'device_read_sectors_total':sum(r['device_read_sectors_delta'] for r in rows),'positive_device_read_delta_cases':sum(r['device_read_sectors_delta']>0 for r in rows),
  'minor_faults_total':sum(r['minor_fault_delta'] for r in rows),'major_faults_total':sum(r['major_fault_delta'] for r in rows)})
 summary.append(item)
assert len(keys)==256 and len(groups)==8
result={'status':'ALL256_READ_CASES128_REAL_O8_PARITIES_RESIDENCY_AND_TIMING_GROUPS_RECOMPUTED','created_UTC':datetime.now(timezone.utc).isoformat(),
 'source_images':16,'read_cases':256,'read_mode_cases':128,'actual_O8_measured_forwards':128,'actual_O8_qualification_forwards':8,'actual_O8_warmups':2,
 'all16_raw_images_byte_equal_to_prior_full_O8':True,'all128_case_raw_hashes_exact':True,'groups':summary,
 'whole_device_IO_not_our_process_IO':True,'new_periodic_counting_or_identity_run':False,'original_full_5FPS_failure_fixed':False,'policy_adopted':False,
 'parent_terminal_and_absent':True,'known_O8_and_services_retained':True,'failed_v1_new_forwards':0,'failed_v1_rows':0,'new_training_updates':0,'whole_goal_complete':False,
 'archive_sha256':m['sha256'],'archive_members':m['members']}
f=ROOT/'results/independent_verification.json';assert not f.exists();f.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps([{'mode':r['mode'],'method':r['method'],'cache':r['cache_request'],'mean_wall_ms':r['JPEG_wall_ms']['mean'],'mean_CPU_ms':r['JPEG_process_CPU_ms']['mean'],'resident_before_all':r['all_before_pages_resident'],'nonresident_before_total':r['before_nonresident_pages_total'],'read_sector_cases':r['positive_device_read_delta_cases']} for r in summary]))
