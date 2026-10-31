from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=PROJECT/'crossdate_gallery_20261029';study=load(old/'protocol/study_v2.json');index=load(old/'delivery/results/study_v2/index.json')
condition=next(c for c in study['conditions'] if c['name']=='C_letterbox_trained_seed26')
groups={'old_gallery':index['gallery_sets']['old_Aug14'],'new_gallery':index['gallery_sets']['new_Aug19'],
        'labelled_query':index['labelled_queries'],'real_event_query':index['real_event_queries']}
assert sum(len(v) for v in groups.values())==132
file=ROOT/'input/images.json';assert not file.exists();file.write_text(json.dumps(groups,indent=2)+'\n')
shutil.copyfile(old/'input/training_primitives.py',ROOT/'input/training_primitives.py')
baseline=old/'delivery/results/study_v2/C_letterbox_trained_seed26/embeddings.npz'
shutil.copyfile(baseline,ROOT/'input/prior_embeddings.npz')
p={'status':'FROZEN_BEFORE_ENCODER_NCNN_EXPORT_OR_INFERENCE','created_UTC':datetime.now(timezone.utc).isoformat(),
 'encoder_condition':condition,'choice':'Fixedseed26toalignfrontenddeployment;notnewlyselectedbyretrievalsuccess.',
 'architecture':'torch.nn.Sequential(MobileNetV3small.features,avgpool,Flatten);576rawfeatures',
 'input_shape':[1,3,224,224],'FP32_weights_and_arithmetic':True,'pnnx_export_fp16':False,
 'source_staging_sha256':sha(ROOT/'evidence/source_staging.json'),
 'reference_protocol_sha256':sha(old/'protocol/study_v2.json'),'prior_embedding_sha256':sha(baseline),
 'input_image_groups':[{'name':k,'count':len(v)} for k,v in groups.items()],
 'input_module_sha256':sha(ROOT/'input/training_primitives.py'),'image_manifest_sha256':sha(file),
 'max_normalized_embedding_absolute_error':.0001,'maximum_1_minus_cosine_error':.00001,
 'prior_Torch_normalized_embedding_tolerance':.0002,'all_gallery_top1_and_threshold_decisions_exact_required':True,
 'registered_IDs':study['registered_IDs'],'fixed_threshold':condition['threshold'],
 'old_Aug14_gallery_is_leakage_control_only':True,'new_Aug19_gallery_is_retrospective_to_Aug14_video':True,
 'real_event_query_verified_identity_labels':False,'identity_accuracy_newly_proven':False,'new_training_updates':0,
 'expected_measured_real_image_forwards':{'TorchCPU':132,'ncnnCPU':132},'export_trace_and_converter_probe_forwards_separate':True,
 'board_compilation_or_forward_in_this_stage':False,'whole_goal_complete':False}
file=ROOT/'protocol/encoder_v1.json';assert not file.exists();file.write_text(json.dumps(p,indent=2)+'\n')
print(json.dumps({'images':132,'encoder_sha256':condition['checkpoint_sha256'],'protocol_sha256':sha(file)}))
