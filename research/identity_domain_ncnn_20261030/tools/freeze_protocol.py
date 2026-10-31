from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,tarfile

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_text(encoding='utf-8'))

domain=load(PROJECT/'identity_domain_adapt_20261030/protocol/run_v1.json');prior=load(PROJECT/'cows2021_identity_eval_20261030/protocol/run_v1.json')
acquisition=load(PROJECT/'cows2021_identity_eval_20261030/results/acquisition_v2.json');image_hashes={row['index']:row['sha256']for row in acquisition['records']}
records=[]
serverbase='/share/home/renly/projects/idcoo_research_20261026/'
for index,row in enumerate(prior['selected_images']):
 records.append({**row,'identity':row['identity_namespace'],'image_SHA256':image_hashes[index],
                 'image_path':serverbase+'cows2021_identity_eval_20261030/'+row['local_relative_file'],
                 'group':row['phase'],'source_index':index})
for index,row in enumerate(domain['MultiCam_retention_images']):
 records.append({**row,'source_index':index,'image_path':row['remote_path'],'image_SHA256':row['sha256'],'group':'retention',
                 'purpose':'gallery'if row['split']=='evaluation_gallery'else'query','is_known':row['role']=='evaluation_registered_ids'})
score=load(PROJECT/'identity_rejection_scores_20261030/results/all_methods_calibration_freeze.json')['primary']
assert score['method']=='absolute_cosine'and score['threshold']==.8707458695890389
references={group:serverbase+'identity_domain_adapt_20261030/results/evaluation/'+phase+'/C_domain_seed26/features.npz'for group,phase in[('calibration','calibration'),('evaluation','development'),('retention','retention')]}
reference_sha={group:sha(PROJECT/'identity_domain_adapt_20261030/delivery/results/evaluation'/phase/'C_domain_seed26/features.npz')for group,phase in[('calibration','calibration'),('evaluation','development'),('retention','retention')]}
plan={'status':'FROZEN_BEFORE_NEW_ENCODER_TORCHSCRIPT_OR_NCNN_CONVERSION','created_UTC':datetime.now(timezone.utc).isoformat(),
      'checkpoint':serverbase+'identity_domain_adapt_20261030/results/training/C_domain_seed26/last_encoder.pt',
      'checkpoint_sha256':'b435fb4599d307c0dd8bf3adccb42a466c271a3fdf23ab91d585d463b70cc912',
      'converter':'/share/home/renly/projects/idcoo_research_20261026/pynq_identity_ncnn_20261029/dependencies/pnnx/pnnx',
      'converter_sha256':'4db234cb90a27dc15e04e0d0edf5706c7a488ab8e6235cf8c146c6ec80fd9355',
      'body_module_sha256':sha(PROJECT/'pynq_identity_ncnn_20261029/tools/ncnn_encoder_v3.py'),
      'images':records,'groups':{'calibration':180,'evaluation':360,'retention':90},'reference_files':references,'reference_sha256':reference_sha,
      'eval_registered_IDs':['Cows2021_IdentificationTest:'+identity for identity in prior['roles']['evaluation_registered']],
      'new_Cows_threshold':score['threshold'],'original_MultiCam_threshold':domain['original_threshold'],
      'max_normalized_NCNN_vs_Torch_error':.0001,'max_1_minus_cosine_error':.00001,'max_Torch_vs_prior_normalized_error':.0002,
      'NCNN_threads':1,'convert_fp16':False,'expected_measured_Torch_image_forwards':630,'expected_measured_NCNN_image_forwards':630,
      'TorchScript_trace_check_trace':False,'converter_internal_probes_count_unknown_separate':True,
      'anchor_indices':[0,60,120,180,300,420,539,540,599,629],
      'calibration_threshold_endpoint_decision_changes_report_only':True,'all_development_Top1_and_decisions_exact_required':True,
      'new_training_updates':0,'new_board_forwards':0,'future20_ID_pixels_opened':False,
      'plan_sha256':sha(ROOT/'计划与验收.md'),'whole_goal_complete':False}
(ROOT/'protocol').mkdir(exist_ok=False);p=ROOT/'protocol/run_v1.json';p.write_text(json.dumps(plan,indent=2)+'\n')
dest=ROOT/'tools/frozen_body_tensor.py';assert not dest.exists();dest.write_bytes((PROJECT/'pynq_identity_ncnn_20261029/tools/ncnn_encoder_v3.py').read_bytes())
execution={'created_UTC':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(p),'code_hashes':{path.name:sha(path)for path in(ROOT/'tools').glob('*')if path.suffix in['.py','.slurm']}}
p=ROOT/'protocol/execution_v1.json';p.write_text(json.dumps(execution,indent=2)+'\n')
archive=ROOT/'export_input_v1.tar.gz';assert not archive.exists()
paths=[path for sub in['tools','protocol']for path in(ROOT/sub).iterdir()if path.is_file()]
with tarfile.open(archive,'w:gz')as tar:
 for path in paths:tar.add(path,arcname=path.relative_to(ROOT).as_posix(),recursive=False)
record={'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(paths),'protocol_sha256':execution['protocol_sha256'],'new_model_forwards':0}
p=ROOT/'evidence/input_bundle.json';assert not p.exists();p.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
