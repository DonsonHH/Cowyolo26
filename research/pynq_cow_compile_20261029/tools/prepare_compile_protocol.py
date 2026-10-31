from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,random
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
manifest=PROJECT/'detector_factorial_20261029/input/prepared_manifest.json';images=json.loads(manifest.read_text())
train=sorted((r for r in images if r['actual_split']=='train'),key=lambda r:r['file_name']);assert len(train)==6809
rng=random.Random(710026);indices=rng.sample(range(len(train)),128);calibration=[]
for i,index in enumerate(indices):
    row=train[index];calibration.append({'order':i,'file_name':row['file_name'],'image_alias':row['image_alias'],'sha256':row['sha256'],
       'actual_split':'train','orientation_ccw_quarter_turns':i%4})
snapshot=json.loads((ROOT/'evidence/source_snapshot_manifest.json').read_text());extra=json.loads((ROOT/'evidence/additional_source_snapshot_manifest.json').read_text())
workspace=ROOT/'compiler_workspace';files=[{'relative_file':p.relative_to(workspace).as_posix(),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(workspace.rglob('*')) if p.is_file()]
p={'status':'FROZEN_BEFORE_OLD_SEED26_COMPILATION_QUALIFICATION','created_host_UTC':datetime.now(timezone.utc).isoformat(),
 'size':192,'source_checkpoint':REMOTE+'/cows2021_adaptation_20261027/results/training/seed26/weights/last.pt',
 'source_checkpoint_sha256':'51b342c474ba321a438b86512c63b8bbeb78d1b86e32b9961fdc21f4ff186a74',
 'model_classes':{'0':'cow'},'pipeline_qualification_only':True,'new_factorial_weights_used':False,
 'source_archive_sha256':snapshot['archive_sha256'],'compiler_modification_record_sha256':sha(ROOT/'evidence/compiler_modifications_v1.json'),
 'workspace_files':files,'source_label_manifest_sha256':sha(manifest),'calibration':calibration,
 'calibration_count':128,'calibration_selection':'PythonRandomseed710026samplewithoutreplacementfromsorted6809train;quarterturni%4,noimagefromvalidation/source/Toros.',
 'quantization':{'method':'MinMax','format':'QDQ','Conv_only_all':True,'per_output_channel_weights':True,
 'weight_type':'signedINT8','weight_symmetric':True,'activation_type':'signedINT8','activation_symmetric':False,'bias':'INT32',
 'CalibMaxIntermediateOutputs':15},
 'float_export':{'opset':17,'batch':1,'dynamic':False,'simplify':True,'nms':False,'device':'cpu'},
 'pc_integer_qualification_images':'First8calibrationtrainingimagesonly;FP32/referencefixedinteger/nativeC++allreported;notaccuracytest.',
 'native_output_parity_gate':{'score_max_absolute':.0001,'box_max_absolute_pixels':.002,'class_exact':True},
 'class_LUT_probe_all256_codes_for_1_and80_classes':True,
 'native_compile_flags':['-O3','-std=c++17','-shared','-fPIC','-fopenmp','-ffp-contract=off','queue_runtime.cpp','-o','native_queue_linux.so','-ldl'],
 'background_identity_added':False,'board_inference_in_this_stage':False,'source_Toros_or_final_image_pixels_used':False,
 'whole_goal_complete':False}
file=ROOT/'protocol/compile_v1.json';file.parent.mkdir(exist_ok=True);assert not file.exists();file.write_text(json.dumps(p,indent=2)+'\n')
print(json.dumps({'protocol_sha256':sha(file),'workspace_files':len(files),'calibration_train_images':128,'size':192}))
