from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,importlib.util,json,tarfile
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
remote='/share/home/renly/projects/idcoo_research_20261026/identity_joint_pair_20261030'
for name in['protocol','evidence','input']: (ROOT/name).mkdir(exist_ok=False)
spec=importlib.util.spec_from_file_location('body',PROJECT/'identity_domain_ncnn_20261030/tools/frozen_body_tensor.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
rows=[];tensors=[];groups=load(PROJECT/'pynq_identity_ncnn_20261029/input/images.json');old=load(PROJECT/'cpu_partition_free_20261030/protocol/run_v1.json')
bg=PROJECT/'backend_service_20261030/delivery/results/r1_idle_gate/background';jobs=load(bg/'record.json')['jobs'];assert len(jobs)==10
for i,image in enumerate(groups['new_gallery']):
 p=Path(image['local_path']);assert sha(p)==image['sha256']
 rows.append({'index':i,'purpose':'gallery','identity':image['identity'],'local_image':str(p),'image_sha256':sha(p),'board_image':f'/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029/images/new_gallery_{i:03d}.jpg'})
for i,(job,fixed)in enumerate(zip(jobs,old['fixed_jobs'])):
 assert job['source_frame0']==fixed['source_frame0'];p=bg/job['photo_file'];assert sha(p)==fixed['expected_prior_actual']['photo_sha256']
 rows.append({'index':30+i,'purpose':'query','identity':None,'local_image':str(p),'image_sha256':sha(p),'board_image':'/home/xilinx/jupyter_notebooks/cow_research_backend_service_20261030/results/r1_idle_gate/background/'+job['photo_file'],'fixed_job_index':i})
for row in rows:
 with Image.open(row['local_image'])as image:x=module.body_tensor(image)
 row['input_tensor_sha256']=hashlib.sha256(x.tobytes()).hexdigest();tensors.append(x)
 if row['purpose']=='query':assert row['input_tensor_sha256']==old['fixed_jobs'][row['fixed_job_index']]['expected_prior_actual']['input_tensor_sha256']
np.savez_compressed(ROOT/'input/input40.npz',input=np.stack(tensors))
plan={'status':'FROZEN40_INPUTS_BEFORE_NEW_CPU_OR_BOARD_MODEL_FORWARD','created_UTC':datetime.now(timezone.utc).isoformat(),'images':rows,'input_archive_sha256':sha(ROOT/'input/input40.npz'),
 'checkpoint':'/share/home/renly/projects/idcoo_research_20261026/identity_domain_adapt_20261030/results/training/C_domain_seed26/last_encoder.pt','checkpoint_sha256':'b435fb4599d307c0dd8bf3adccb42a466c271a3fdf23ab91d585d463b70cc912',
 'NCNN_param':'/share/home/renly/projects/idcoo_research_20261026/identity_domain_ncnn_20261030/results/export/encoder.ncnn.param','NCNN_param_sha256':'dd1a5af7c7f33b273508665f8332d3b48e847898981fc55989b2278022a98fe7',
 'NCNN_bin':'/share/home/renly/projects/idcoo_research_20261026/identity_domain_ncnn_20261030/results/export/encoder.ncnn.bin','NCNN_bin_sha256':'2a587d0fe293d244eb5632feb0e3665cf6091243198612b59363a6a7bb173252',
 'plan_sha256':sha(ROOT/'计划与验收.md'),'known_source_gallery_after_event_retroactive':True,'expected_Torch_image_forwards':40,'expected_NCNN_image_forwards':40,'new_training_updates':0,'future20_ID_pixels_opened':False,'whole_goal_complete':False}
target=ROOT/'protocol/cpu_reference_v1.json';target.write_bytes((json.dumps(plan,indent=2)+'\n').encode())
slurm=f'''#!/bin/bash
#SBATCH --job-name=cow-id-joint-ref
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output={remote}/logs/reference-%j.out
#SBATCH --error={remote}/logs/reference-%j.err
set -euo pipefail
export OMP_NUM_THREADS=4 OPENBLAS_NUM_THREADS=4 PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH=/share/home/renly/projects/idcoo_research_20261026/pynq_identity_ncnn_20261029/dependencies
cd {remote}
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -B -u tools/cpu_reference.py
''';(ROOT/'tools/reference.slurm').write_bytes(slurm.encode())
execution={'protocol_sha256':sha(target),'code_sha256':{name:sha(ROOT/name)for name in['tools/cpu_reference.py','tools/reference.slurm']}};(ROOT/'protocol/cpu_execution_v1.json').write_bytes((json.dumps(execution,indent=2)+'\n').encode())
archive=ROOT/'reference_input_v1.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz')as tar:
 for path,name in[(ROOT/'input/input40.npz','input40.npz'),(target,'protocol/cpu_reference_v1.json'),(ROOT/'protocol/cpu_execution_v1.json','protocol/cpu_execution_v1.json'),(ROOT/'tools/cpu_reference.py','tools/cpu_reference.py'),(ROOT/'tools/reference.slurm','tools/reference.slurm')]:tar.add(path,arcname=name,recursive=False)
v={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':5,'protocol_sha256':sha(target),'new_model_forwards':0};(ROOT/'evidence/reference_input_bundle.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v))
