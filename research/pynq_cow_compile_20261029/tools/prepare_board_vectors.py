from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,tarfile
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
q=ROOT/'delivery/results/qualification_v2';s=json.loads((q/'summary.json').read_text());assert s['all_native_CPU_parity_gates_pass'] is True
out=ROOT/'board_payload';out.mkdir(exist_ok=False)
files=[]
for relative in ['compiled/program/graph.bin','compiled/program/program.json']:
    file=q/relative;destination=out/'program'/file.name;destination.parent.mkdir(exist_ok=True);shutil.copyfile(file,destination);files.append(destination)
for name in ['resident_plan.bin','resident_plan.json']:
    destination=out/'resident_plan'/name;destination.parent.mkdir(exist_ok=True);shutil.copyfile(q/'resident_plan_all'/name,destination);files.append(destination)
for i in range(8):
    destination=out/'vectors'/('parity_train_'+str(i)+'.npz');destination.parent.mkdir(exist_ok=True);shutil.copyfile(q/destination.name,destination);files.append(destination)
script=out/'board_cow_vectors.py';shutil.copyfile(ROOT/'tools/board_cow_vectors.py',script);files.append(script)
p={'status':'FROZEN_BEFORE_ACTUAL_BOARD_COW_VECTOR_QUALIFICATION','created_host_UTC':datetime.now(timezone.utc).isoformat(),
 'size':192,'class_count':1,'model_checkpoint_sha256':s['checkpoint_sha256'],'qualification_summary_sha256':sha(q/'summary.json'),
 'expected_O8_bit_sha256':'5da7a73bf52fd5153e25de5c28a40e2080c29e960d767008e0e804ec527bbfd8',
 'parity_gate':{'box_max_absolute_pixels':.002,'score_max_absolute':.0001,'classes_exact':True},
 'vectors':8,'warmups':2,'all_input_images_from_train_calibration':True,'source_video_Toros_or_development_validation_images_used':False,
 'real_video_count_accuracy_claimed':False,'background_identity_active':False,'expected_model_forwards':10,
 'existing_O8_hardware_must_already_be_loaded':True,'new_bitstream_programming':False,'original_O8_directory_modified':False,
 'payload_files':[{'file':f.relative_to(out).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files],
 'whole_goal_complete':False}
protocol=ROOT/'protocol/board_vectors_v1.json';assert not protocol.exists();protocol.write_text(json.dumps(p,indent=2)+'\n')
shutil.copyfile(protocol,out/'protocol.json');files.append(out/'protocol.json')
archive=ROOT/'board_vectors_payload.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
    for file in files:tar.add(file,arcname=file.relative_to(out).as_posix(),recursive=False)
record={'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files),'protocol_sha256':sha(protocol)}
file=ROOT/'evidence/board_payload_staging.json';assert not file.exists();file.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
