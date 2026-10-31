from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=PROJECT/'pynq_lowres_20261029';prior=json.loads((old/'protocol/board_benchmark_v1.json').read_text())
recovery=json.loads((old/'results/recovered_board_state01.json').read_text())
assert recovery['prior_PID8082']['exit_code']==1 and recovery['services']['output']=='active\nactive\n'
firmware=json.loads((old/'board_source_snapshot/yolo26_optimization_8/hardware/accepted/firmware_manifest.json').read_text())
p={'status':'FROZEN_BEFORE_RECOVERED_BOARD_PROBE_OR_PROFILE','created_host_UTC':datetime.now(timezone.utc).isoformat(),
   'supersedes_interrupted_protocol_sha256':sha(old/'protocol/board_benchmark_v1.json'),'sizes':[192,256,320],
   'recovered_boot_id':recovery['boot_id'].strip(),'source_root':'/home/xilinx/jupyter_notebooks/cow_research_lowres_20261029',
   'source_images':prior['source_images'],'runtime_files':prior['runtime_files'],'target_frontend_fps':5,'per_frame_budget_ms':200,
   'warmups':2,'formal_samples_each_size':32,'distinct_source_photos':12,'fixed_E010_repeats':20,'probe_samples':1,
   'order':['probe192','formal192','formal256','formal320'],'maximum_hardware_processes':1,'cv2_threads':1,'OMP_NUM_THREADS':2,'OPENBLAS_NUM_THREADS':2,
   'O8_bit_sha256':firmware['bit']['sha256'],'O8_hwh_sha256':firmware['hwh']['sha256'],
   'engines':{'192':'O8resident','256':'O8resident','320':'O6legacy'},
   'timing_scope':'DecodednativeBGR->squareletterboxandquantization->actualFPGA/ARMfullnetwork->copyraw->decode;JPEGread/CWrotationseparateandcombined.',
   'sampling_or_server_speed_not_used_as_hardware_measurement':True,'camera_acquisition_measured':False,
   'background_identity_active':False,'current_cow_finetuned_checkpoint_loaded':False,'current12_count_accuracy_measured':False,
   'output_rule':'DurableatomicJSONperstageandrow;fsyncrawandJSON;oneprofileperprocess;nosilentresumeoroverwrites.',
   'permission_context':'UserexplicitlyrequiresactualPYNQ-Z2tests;existinghardwareassetsmaybeloadedunderexclusiveacceleratorlock.',
   'initial_firmware':recovery['PL_bitfile'],'initial_IP_names_do_not_establish_detector_firmware':True,
   'prior_interrupted_result_admitted_for_performance':False,'script_sha256':sha(ROOT/'tools/board_profile.py'),
   'whole_goal_complete':False}
target=ROOT/'protocol/board_v2.json';target.parent.mkdir(exist_ok=True);assert not target.exists();target.write_text(json.dumps(p,indent=2)+'\n')
(ROOT/'evidence').mkdir(exist_ok=True);(ROOT/'results').mkdir(exist_ok=True)
print(json.dumps({'protocol_sha256':sha(target),'script_sha256':p['script_sha256'],'all_sizes':[192,256,320]}))
