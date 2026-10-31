from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil,tarfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
verified=load(ROOT/'results/ordered_reference_verification.json');assert verified['ordered_reference_exact']==24 and verified['old320_gate_failure_preserved']
q=ROOT/'delivery/s320/results/qualification';s=load(q/'summary.json');assert not s['all_native_CPU_parity_gates_pass']
out=ROOT/'board_payload_s320';out.mkdir(exist_ok=False);files=[]
for rel in ['compiled/program/graph.bin','compiled/program/program.json']:
 p=out/'program'/Path(rel).name;p.parent.mkdir(exist_ok=True);shutil.copyfile(q/rel,p);files.append(p)
for name in ['resident_plan.bin','resident_plan.json']:
 p=out/'resident_plan'/name;p.parent.mkdir(exist_ok=True);shutil.copyfile(q/'resident_plan_all'/name,p);files.append(p)
for i in range(8):
 old=q/('parity_train_'+str(i)+'.npz');orderedfile=ROOT/'numeric_delivery/results/ordered_reference'/('size320_vector'+str(i)+'.npz')
 with np.load(old) as a:x=a['input'];legacy=a['reference_integer_raw'];native=a['native_integer_raw'];fp32=a['FP32_raw']
 with np.load(orderedfile) as a:reference=a['ordered_reference'];assert reference.tobytes()==native.tobytes()
 file=out/'vectors'/old.name;file.parent.mkdir(exist_ok=True)
 np.savez_compressed(file,input=x,reference_integer_raw=reference,native_integer_raw=native,FP32_raw=fp32,legacy_numpy_reference_raw=legacy)
 files.append(file)
code=(ROOT/'tools/board_s256_vectors.py').read_text().replace('256','320')
file=ROOT/'tools/board_s320_vectors.py';file.write_text(code,newline='\n');shutil.copyfile(file,out/file.name);files.append(out/file.name)
protocol=load(ROOT/'protocol/board_s256_v1.json');protocol.update({'status':'FROZEN_BEFORE_S320_SAME_O8_BOARD_WITH_EXPLICIT_ORDERED_REFERENCE','created_host_UTC':datetime.now(timezone.utc).isoformat(),
 'size':320,'model_checkpoint_sha256':s['checkpoint_sha256'],'qualification_summary_sha256':sha(q/'summary.json'),
 'reference_contract':'INT32Convexactfixedrequant;nonconvMatMulFP32KorderedandSoftmaxC99expforderedFP32sum.',
 'ordered_reference_verification_sha256':sha(ROOT/'results/ordered_reference_verification.json'),
 'ordered_reference_protocol_sha256':sha(ROOT/'protocol/ordered_float_reference_v2.json'),
 'original_numpy_reference_failure_retained':True,'legacy_numpy_reference_all8_raw_passed':False,
 'new_model_weights_or_native_runtime_code':False,
 'payload_files':[{'file':p.relative_to(out).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]})
proto=ROOT/'protocol/board_s320_v1.json';proto.write_text(json.dumps(protocol,indent=2)+'\n');shutil.copyfile(proto,out/'protocol.json');files.append(out/'protocol.json')
archive=ROOT/'board_s320_payload.tar.gz'
with tarfile.open(archive,'w:gz') as tar:
 for file in files:tar.add(file,arcname=file.relative_to(out).as_posix(),recursive=False)
meta={'sha256':sha(archive),'bytes':archive.stat().st_size,'members':len(files),'protocol_sha256':sha(proto)}
(ROOT/'evidence/board_s320_payload.json').write_text(json.dumps(meta,indent=2)+'\n')
oldmeta=load(ROOT/'evidence/board_payload_s256_staging.json')
for source,name in [('s256_create_board_task.sh','s320_create_board_task.sh'),('s256_launch_board_vectors.sh','s320_launch_board_vectors.sh'),
 ('s256_status_board_vectors.sh','s320_status_board_vectors.sh'),('s256_collect_board_vectors.sh','s320_collect_board_vectors.sh')]:
 text=(ROOT/'tools'/source).read_text().replace('cow_research_o8_s256_qual_20261030','cow_research_o8_s320_qual_20261030').replace('board_s256_vectors.py','board_s320_vectors.py')
 text=text.replace(oldmeta['sha256'],meta['sha256']).replace(oldmeta['protocol_sha256'],meta['protocol_sha256'])
 text=text.replace("'size':256","'size':320").replace("'size': 256","'size': 320")
 (ROOT/'tools'/name).write_text(text,newline='\n')
print(json.dumps(meta))
