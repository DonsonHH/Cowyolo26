from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OLD=PROJECT/'causal_photo_20261030/tools'
def copy(name,changes=()):
 text=(OLD/name).read_text(encoding='utf-8')
 for before,after in changes:
  assert text.count(before)>=1,(name,before);text=text.replace(before,after)
 f=ROOT/'tools'/name
 if f.exists():assert f.read_text(encoding='utf-8')==text;return
 f.write_text(text,encoding='utf-8')
copy('independent_geometry.py',[("selection['policy']=='causal_ring'","selection['policy'] in ['serial_input','async_input']")])
copy('verify_board_results.py',[
 ('ALL_SIX392_SLOT_CAUSAL_PHOTO_SAME_BOARD_REPEATS_COMPLETE','ALL_FOUR392_SLOT_SERIAL_ASYNC_HIGHRES_SAME_BOARD_REPEATS_COMPLETE'),
 ("s['warmup_forwards']==12","s['warmup_forwards']==8"),
 ("if run['policy']=='causal_ring':","if run['policy'] in ['serial_input','async_input']:"),
 ('len(cases)==6','len(cases)==4'),('ticks==6*1783+rawchecks','ticks==4*1783+rawchecks'),('paths==12','paths==8'),
 ("'actual_O8_warmups':12","'actual_O8_warmups':8"),
 ('SIX_REAL_PYNQ_CAUSAL_PHOTO_RUNS_RAW_COUNTER_BUFFER_SELECTION_PHOTO_INPUT_FEATURE_AND_RETRIEVAL_VERIFIED','FOUR_REAL_SERIAL_ASYNC_PYNQ_RUNS_RAW_COUNTER_BUFFER_PHOTO_INPUT_FEATURE_AND_RETRIEVAL_VERIFIED')])
copy('actual_photo_panels.py',[
 ("j['policy']=='current_frame'","j['policy']=='serial_input'"),("j['policy']=='causal_ring'","j['policy']=='async_input'"),
 ("'current_frame' if key in current else 'causal_ring'","'serial_input' if key in current else 'async_input'"),
 ("'current':a,'causal':b","'serial':a,'async':b"),
 ('score_delta_causal_minus_current','score_delta_async_minus_serial'),('accepted_current','accepted_serial'),('accepted_causal','accepted_async')])
copy('verify_actual_panels.py')
copy('collect_results.py',[
 ('SIX_RUN_PARENT_AND_FOUR_IDENTITY_WORKERS_TERMINAL_ABSENT_O8_RETAINED','FOUR_RUN_PARENT_AND_FOUR_IDENTITY_WORKERS_TERMINAL_ABSENT_O8_RETAINED'),
 ('ALL_SIX392_SLOT_CAUSAL_PHOTO_SAME_BOARD_REPEATS_COMPLETE','ALL_FOUR392_SLOT_SERIAL_ASYNC_HIGHRES_SAME_BOARD_REPEATS_COMPLETE'),
 ("s['warmup_forwards']==12","s['warmup_forwards']==8"),("len(s['cases'])==6","len(s['cases'])==4"),
 ("'board_causal_repeats.py'","'board_async_repeats.py'"),
 ("'causal_selector.py','collect_results.py'","'causal_selector.py','jpeg_producer.py','test_producer.py','board_producer_behavior_tests.json','collect_results.py'"),
 ('causal_photo_delivery_v1.tar.gz','async_highres_delivery_v1.tar.gz')])
copy('collect_launch.sh',[
 ('cow_research_causal_photo_20261030','cow_research_async_highres_20261030'),
 ('ALL_SIX392_SLOT_CAUSAL_PHOTO_SAME_BOARD_REPEATS_COMPLETE','ALL_FOUR392_SLOT_SERIAL_ASYNC_HIGHRES_SAME_BOARD_REPEATS_COMPLETE')])
copy('collection_status.sh',[('cow_research_causal_photo_20261030','cow_research_async_highres_20261030')])
copy('extract_delivery.py',[
 ('causal_photo_delivery_v1.tar.gz','async_highres_delivery_v1.tar.gz'),
 ("('board_causal_repeats.py','tools/board_causal_repeats.py')","('board_async_repeats.py','tools/board_async_repeats.py')")])
copy('final_board_read.sh',[
 ('cow_research_causal_photo_20261030','cow_research_async_highres_20261030'),
 ('ALL_SIX392_SLOT_CAUSAL_PHOTO_SAME_BOARD_REPEATS_COMPLETE','ALL_FOUR392_SLOT_SERIAL_ASYNC_HIGHRES_SAME_BOARD_REPEATS_COMPLETE'),
 ('CAUSAL_PHOTO_PARENT_FOUR_WORKERS_AND_COLLECTOR_TERMINAL_ABSENT_O8_AND_SERVICES_READ','ASYNC_HIGHRES_PARENT_FOUR_WORKERS_AND_COLLECTOR_TERMINAL_ABSENT_O8_AND_SERVICES_READ')])
print({'created_verification_and_collection_scripts':10,'old_phase_unchanged':True})
