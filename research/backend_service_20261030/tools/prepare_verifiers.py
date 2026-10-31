from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OLD=PROJECT/'async_highres_20261030/tools'
def copy(name,replacements=()):
 text=(OLD/name).read_text(encoding='utf-8')
 for a,b in replacements:
  assert a in text,(name,a);text=text.replace(a,b)
 f=ROOT/'tools'/name
 if f.exists():assert f.read_text(encoding='utf-8')==text;return
 f.write_text(text,encoding='utf-8')
copy('independent_geometry.py',[("['serial_input','async_input']","['idle_gate','low_priority_parallel']")])
pause=""" assert len(intervals)==len(rows)
 for interval,row in zip(intervals,rows):
  assert interval['slot']==row['slot'] and interval['pause_acknowledged_monotonic_ns']<=row['started_monotonic_ns']<=row['completed_monotonic_ns']<=interval['resume_sent_monotonic_ns'];pauses+=1"""
newpause=""" if run['policy']=='idle_gate':
  assert len(intervals)==len(rows)
  for interval,row in zip(intervals,rows):
   assert interval['slot']==row['slot'] and interval['pause_acknowledged_monotonic_ns']<=row['started_monotonic_ns']<=row['completed_monotonic_ns']<=interval['resume_sent_monotonic_ns'];pauses+=1
 else:assert intervals==[]
 assert b['execution_policy']==run['policy'] and b['actual_nice']==10 and b['actual_CPU_affinity']==[0,1]"""
copy('verify_board_results.py',[
 ('ALL_FOUR392_SLOT_SERIAL_ASYNC_HIGHRES_SAME_BOARD_REPEATS_COMPLETE','ALL_FOUR392_SLOT_IDLE_LOW_PRIORITY_BACKEND_SAME_BOARD_REPEATS_COMPLETE'),
 ("['serial_input','async_input']","['idle_gate','low_priority_parallel']"),(pause,newpause),
 ('FOUR_REAL_SERIAL_ASYNC_PYNQ_RUNS_RAW_COUNTER_BUFFER_PHOTO_INPUT_FEATURE_AND_RETRIEVAL_VERIFIED','FOUR_REAL_IDLE_PARALLEL_BACKEND_PYNQ_RUNS_RAW_COUNTER_BUFFER_PHOTO_INPUT_FEATURE_AND_RETRIEVAL_VERIFIED')])
copy('verify_producer_records.py',[("spec['policy']=='async_input'","spec['policy'] in ['idle_gate','low_priority_parallel']"),('producer_frames==784','producer_frames==1568')])
copy('actual_photo_panels.py',[("j['policy']=='serial_input'","j['policy']=='idle_gate'"),("j['policy']=='async_input'","j['policy']=='low_priority_parallel'"),
 ("'serial_input' if key in current else 'async_input'","'idle_gate' if key in current else 'low_priority_parallel'"),
 ("'serial':a,'async':b","'idle_gate':a,'low_priority_parallel':b"),('score_delta_async_minus_serial','score_delta_parallel_minus_idle'),('accepted_serial','accepted_idle_gate'),('accepted_async','accepted_low_priority_parallel')])
copy('verify_actual_panels.py')
copy('collect_results.py',[
 ('ALL_FOUR392_SLOT_SERIAL_ASYNC_HIGHRES_SAME_BOARD_REPEATS_COMPLETE','ALL_FOUR392_SLOT_IDLE_LOW_PRIORITY_BACKEND_SAME_BOARD_REPEATS_COMPLETE'),
 ('board_async_repeats.py','board_backend_repeats.py'),('async_highres_delivery_v1.tar.gz','backend_service_delivery_v1.tar.gz'),
 ("'board_producer_behavior_tests.json','collect_results.py'","'board_producer_behavior_tests.json','process_cpu.py','test_process_cpu.py','board_CPU_parser_test.json','collect_results.py'")])
copy('collect_launch.sh',[
 ('cow_research_async_highres_20261030','cow_research_backend_service_20261030'),
 ('ALL_FOUR392_SLOT_SERIAL_ASYNC_HIGHRES_SAME_BOARD_REPEATS_COMPLETE','ALL_FOUR392_SLOT_IDLE_LOW_PRIORITY_BACKEND_SAME_BOARD_REPEATS_COMPLETE')])
copy('collection_status.sh',[('cow_research_async_highres_20261030','cow_research_backend_service_20261030')])
copy('extract_delivery.py',[('async_highres_delivery_v1.tar.gz','backend_service_delivery_v1.tar.gz'),('board_async_repeats.py','board_backend_repeats.py')])
copy('final_board_read.sh',[
 ('cow_research_async_highres_20261030','cow_research_backend_service_20261030'),
 ('ALL_FOUR392_SLOT_SERIAL_ASYNC_HIGHRES_SAME_BOARD_REPEATS_COMPLETE','ALL_FOUR392_SLOT_IDLE_LOW_PRIORITY_BACKEND_SAME_BOARD_REPEATS_COMPLETE'),
 ('ASYNC_HIGHRES_PARENT_FOUR_WORKERS_AND_COLLECTOR_TERMINAL_ABSENT_O8_AND_SERVICES_READ','BACKEND_SERVICE_PARENT_FOUR_WORKERS_AND_COLLECTOR_TERMINAL_ABSENT_O8_AND_SERVICES_READ')])
print({'verification_and_collection_scripts_prepared':10,'old_phase_unchanged':True})
