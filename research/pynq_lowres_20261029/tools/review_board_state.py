from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,csv,io
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def record_body(p):
    r=load(p);body=''.join(m['content'].get('text','') for m in r.get('messages',[]) if m['type']=='stream')
    return r,json.loads(body) if body.strip() else None
record,board=record_body(ROOT/'evidence/board_inventory.json');assert record['own_kernel_removed'] and board['pynq_version']=='3.1.1'
assert board['machine']=='armv7l' and '503464' in board['memory_selected'][0]
launch_record,launch=record_body(ROOT/'evidence/benchmark_launch02.json');assert launch['PID']==8082 and launch_record['own_kernel_removed']
release=ROOT/'board_source_snapshot/yolo26_optimization_8/reports/final_delivery/candidate_pareto.csv'
rows=list(csv.DictReader(io.StringIO(release.read_text(encoding='utf-8-sig'))));historical=[]
for size in ['192','256']:
    r=next(r for r in rows if r['variant']=='D' and r['size']==size)
    historical.append({'size':int(size),'engine':'O8resident','record_type':'historical_read_not_live_remeasurement',
    'mean_ms':float(r['mean_ms']),'p95_ms':float(r['P95_ms']),'maximum_ms':float(r['max_ms']),'FPS':float(r['FPS']),
    'background_identity_active':False,'source_scope':r['scope'],'source_path':str(release.resolve()),'source_sha256':sha(release)})
old=load(ROOT/'board_source_snapshot/yolo26_optimization_6/runs/r320_fixed100/result.json')
s=old['fixed_statistics']['total_ms']
historical.append({'size':320,'engine':'O6legacy_different_engine','record_type':'historical_read_not_live_remeasurement',
'mean_ms':s['mean'],'p95_ms':s['p95'],'maximum_ms':s['max'],'FPS':1000/s['mean'],'background_identity_active':False,
'source_path':str((ROOT/'board_source_snapshot/yolo26_optimization_6/runs/r320_fixed100/result.json').resolve()),
'source_sha256':sha(ROOT/'board_source_snapshot/yolo26_optimization_6/runs/r320_fixed100/result.json')})
kernels=[]
for file in sorted((ROOT/'evidence').glob('*.json')):
    r=load(file)
    if 'own_kernel_id' in r:
        assert r['own_kernel_removed'] is True
        kernels.append({'record':file.name,'kernel_id':r['own_kernel_id'],'removed':True,'error':r['error']})
status={'status':'LIVE_INVENTORY_CONFIRMED_BOARD_BENCHMARK_LAUNCHED_TERMINAL_UNOBSERVED_SERVICES_UNREACHABLE',
'created_UTC':datetime.now(timezone.utc).isoformat(),'board_IP':'192.168.2.99','Jupyter_port':9090,'COM_port':'COM6',
'PYNQ_version':board['pynq_version'],'OS_image_version_label':'PynqLinux3.0CarlisleUbuntu22.04','kernel':board['uname'][2],
'Python':board['python'],'architecture':board['machine'],'memory_total_KiB':503464,'opencv':board['opencv_version'],
'board_inventory_sha256':sha(ROOT/'evidence/board_inventory.json'),'board_inventory_was_live':True,
'initial_PL_bitfile_metadata':board['current_PL_bitfile'],'initial_IP_names_saved_without_claiming_programmed_image_identity':True,
'own_benchmark_PID':8082,'launch_record_sha256':sha(ROOT/'evidence/benchmark_launch02.json'),
'own_benchmark_terminal_state':'NOT_OBSERVED','own_benchmark_restart_count':0,'own_benchmark_results_retrieved':False,
'current_PL_bitfile_after_benchmark':'UNKNOWN_NOT_READ_BACK','hardware_programming_instructions_in_launched_script':True,
'no_further_PL_load_or_reboot_after_observation_loss':True,'user_board_state_question_pending':True,
'initial_large_ws_upload_failed_no_launch_marker_then_HTTP_upload_verified':True,
'latest_TCP_revalidation':load(ROOT/'evidence/connectivity_revalidation02.json'),
'serial_read':load(ROOT/'evidence/serial_prompt01.json'),'SSH_observation':load(ROOT/'evidence/ssh_probe01.json'),
'unknown_root_cause':'Service/process/hardware/power state not determined; temporalassociationnotcausalproof.',
'past_performance_records':historical,'historical256and320_use_distinct_engine_conditions':True,
'new_lowres_cow_weights_deployed':False,'actual_live5FPS_measurement_available':False,
'foreground_and_background_joint5FPS_proven':False,'reused_auth_material_persisted':False,'own_Jupyter_kernels':kernels,
'whole_goal_complete':False}
out=ROOT/'results/board_state_review.json';assert not out.exists();out.write_text(json.dumps(status,indent=2)+'\n')
print(json.dumps({'status':status['status'],'own_PID':8082,'terminal':'unobserved','historical':[{k:r[k] for k in ['size','engine','mean_ms','FPS']} for r in historical],'own_kernels_removed':len(kernels),'new5FPS_proof':False}))
