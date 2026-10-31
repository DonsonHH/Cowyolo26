from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text())

observations=[];files=[]
for p in sorted((ROOT/'evidence').glob('status*.json')):
 row=load(p);files.append(p)
 if row.get('status')!='PRIVILEGED_UART_COMMAND_FINISHED' or row.get('exit_code')!=0:continue
 for line in row['output'].splitlines():
  try:record=json.loads(line)
  except json.JSONDecodeError:continue
  if record.get('status')=='SAME_ACTUAL_TRIGGER_PAIR_TASK_READONLY_OBSERVATION':
   observations.append({'source_file':p.relative_to(ROOT).as_posix(),'host_UTC':row['created_UTC'],'data':record})
assert observations
latest=max(observations,key=lambda r:r['host_UTC']);latest_cases=latest['data']['cases']
assert [r['run']for r in latest_cases]==['r1_old','r1_new','r2_new']
assert [r['source_down_count']for r in latest_cases]==[10,10,8]
progress=max((r for r in observations if r['data'].get('progress')),key=lambda r:r['data']['progress']['actual_O8_forwards'])
assert progress['data']['progress']['actual_O8_forwards']==1451 and progress['data']['progress']['run']=='r2_old'and progress['data']['progress']['processed_slots_this_case']==350
plan=load(ROOT/'protocol/run_v1.json');assert sha(ROOT/'protocol/run_v1.json')=='4217824d2964e56218c566a73096a2f282c94020f3176c74bf86cef9a270513c'
for r in plan['payload_files']:assert sha(ROOT/'payload'/r['file'])==r['sha256']
assert load(ROOT/'evidence/binary_upload_v2_terminal.json')['tty_restored_verified']
serial=load(ROOT/'evidence/access_diagnosis01_serial.json');net=load(ROOT/'evidence/access_diagnosis01_network.json')
assert serial['observed_bytes']==0 and all(not r['connected']for r in net['results'])
result={'status':'PARTIAL_HOST_OBSERVATIONS_PRESERVED_AFTER_USER_CONFIRMED_POWER_OR_CONNECTION_CHANGE_NOT_FINAL_RESULT',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'protocol_SHA256':sha(ROOT/'protocol/run_v1.json'),'original_experiment_PID':10099,
 'source_boot_id':'9ecd4ca1-edd1-45f8-aa09-dfac2a089f2f','latest_successful_observation_host_UTC':latest['host_UTC'],
 'observed_complete_case_summaries':latest_cases,'last_progress_run':progress['data']['progress']['run'],
 'last_progress_case_processed_frames_lower_bound':350,'timed_O8_calls_observed_lower_bound':1451,
 'observed_first3_background_jobs':sum(r['actual_background_jobs']for r in latest_cases),'fourth_case_terminal_observed':False,
 'original_results_archive_obtained':False,'full_raw_outputs_obtained':False,'actual_photo_or_feature_files_obtained':False,
 'full_independent_numeric_or_counter_verification_complete':False,'user_confirmed_access_change':'User replied that power was turned off or connections moved; exact time and whether SD writes completed were not stated.',
 'current_PC_ethernet_last_observed':{'IPv4':'192.168.3.13','prefix_length':24,'origin':'DHCP','gateway':'192.168.3.1'},
 'previous_direct_board_PC_IPv4':'192.168.2.1','network_configuration_changed_by_agent':False,
 'original_experiment_restarted':False,'board_reset_or_model_reload_requested_by_agent':False,
 'result_files_lost_claimed':False,'source_completion_or_failure_inferred_from_access_loss':False,
 'new_independent_ID_or_count_GT':False,'new_model_forwards_by_this_audit':0,'whole_goal_complete':False,
 'evidence_files':[{'file':p.relative_to(ROOT).as_posix(),'sha256':sha(p)}for p in files]+[
 {'file':p.relative_to(ROOT).as_posix(),'sha256':sha(p)}for p in sorted((ROOT/'evidence').glob('access_diagnosis01*.json'))]}
p=ROOT/'results/partial_observation_v1.json';assert not p.exists();p.write_bytes(json.dumps(result,ensure_ascii=False,indent=2).encode()+bytes([10]))
print(json.dumps({'status':result['status'],'observed_case_counts':[r['source_down_count']for r in latest_cases],'last_fourth_case_progress_lower_bound':350,'timed_detection_calls_observed_lower_bound':1451,'new_model_forwards':0},ensure_ascii=False))
