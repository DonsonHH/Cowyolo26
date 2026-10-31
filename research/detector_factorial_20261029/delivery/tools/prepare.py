from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def main():
    old=PROJECT/'cows2021_adaptation_20261027';p=load(old/'protocol/detector_v1.json')
    freeze=load(PROJECT/'orientation_validation_20261027/input/source_checkpoint_freeze.json')
    directory=ROOT/'input';directory.mkdir(exist_ok=False)
    sources={'baseline_detector_v1.json':old/'protocol/detector_v1.json','baseline_checkpoint_freeze.json':PROJECT/'orientation_validation_20261027/input/source_checkpoint_freeze.json',
    'prepared_manifest.json':old/'delivery/results/labels_v1/prepared_image_label_manifest.json','loader_summary.json':old/'delivery/results/labels_v1/summary.json',
    'baseline_effective_args.yaml':old/'delivery/results/training/seed26/args.yaml'}
    for name,src in sources.items():shutil.copyfile(src,directory/name)
    shutil.copyfile(old/'tools/observed_trainer.py',ROOT/'tools/observed_trainer.py')
    kwargs={**p['train_kwargs'],'rect':False,'multi_scale':0.0,'degrees':0.0}
    kwargs.pop('imgsz')
    kwargs.update({'warmup_epochs':3.0,'warmup_momentum':.8,'warmup_bias_lr':.1,'nbs':64,
                   'hsv_h':.015,'hsv_s':.7,'hsv_v':.4,'translate':.1,'scale':.5,'shear':0.,'perspective':0.,
                   'flipud':0.,'fliplr':.5,'bgr':0.,'mosaic':1.,'mixup':0.,'cutmix':0.,'copy_paste':0.})
    groups=[{'name':'G640_plain','imgsz':640,'right_angle':False},{'name':'G320_rot90','imgsz':320,'right_angle':True},{'name':'G640_rot90','imgsz':640,'right_angle':True}]
    conditions=[{'array_index':i*3+j,'condition_id':g['name']+'_seed'+str(seed),'group':g['name'],'imgsz':g['imgsz'],'right_angle':g['right_angle'],
    'seed':seed,'expected_initial_state_digest':next(r['initial_state_digest'] for r in freeze['conditions'] if r['seed']==seed)}
    for i,g in enumerate(groups) for j,seed in enumerate([26,27,28])]
    protocol={'status':'FROZEN_BEFORE_NEW_AUGMENTATION_PREFLIGHT_OR_TRAINING','version':1,'created_UTC':datetime.now(timezone.utc).isoformat(),
    'source_weights': '/share/home/renly/projects/idcoo_research_20261026/models/yolo26n.pt','source_weights_sha256':p['source_weights_sha256'],
    'source_data_yaml':'/share/home/renly/projects/idcoo_research_20261026/cows2021_adaptation_20261027/data_v1/data.yaml',
    'historical_original_group':'320noextra-right-angle3seedcontrols,weightsandinitialdigestsretained;notnewcontemporaryruns.',
    'baseline_checkpoint_conditions':freeze['conditions'],'conditions':conditions,'epochs':10,'train_kwargs_common':kwargs,
    'train_images':6809,'validation_images':1571,'train_annotation_rows':8888,'validation_annotation_rows':1864,
    'expected_batches_per_epoch':213,'expected_batches_per_run':2130,'expected_training_images_per_run':68090,
    'rotation':'Afterstandardtrainpreprocess,squareNCHWfloat image90degCCWintegerpermutations;xywhnormalizedsync;Uniformk0..3perimage;nointerpolation.',
    'rotation_rng':'SeparateCPUTorchGeneratorseed710026+trainseed;unaugmentedbranchdrawsnorandomvalues;noconsumptionofbaselineglobalstream.',
    'no_extra_rotation_does_not_change_standard_preprocess':True,'validation_rotation_augmented':False,
    'preflight':'ExactCPU/CUDAimage-and-maskboxoracle,all4turns,arbitrarybatch_idx,emptylabels,area/4turninverse;3realtrainersx2optimizerstepsdiscarded.',
    'checkpoint_rule':'All9fixedepoch10last.pt;best.ptarchivedonly;freezeall9beforecurrentnewsource/Torosoradditionalbenchmarkinference.',
    'all_seed_and_group_results_retained':True,'source_Toros_pseudolabels_used':False,'count_based_model_selection_allowed':False,
    'input_sha256':{f.name:sha(f) for f in sorted(directory.iterdir())},'implementation_sha256':{n:sha(ROOT/'tools'/n) for n in ['common.py','observed_trainer.py','rotation_training.py']},
    'previous_pair_final_sha256':sha(PROJECT/'detector_torso_pairs_20261029/results/final_review.json'),
    'data_geometry_definition':p['object_definition'],'library':p['library'],'maximum_concurrent_GPU_jobs':3,
    'evaluation_plan':{'development_images':'Same1571datevalidationimages,320/640native/CW90rectTrue;all9plusoldcontrols.',
    'video':'Original0historysource8912..10873accepted12totalandpreviousToros6events;samecountingchain;nohistoricalfalsepromotion.',
    'new_candidate_final_images_allowed':False,'server_speed_is_board_speed':False},
    'runtime_pipeline_changed':False,'FPGA_execution_verified':False,'whole_goal_complete':False}
    save(ROOT/'protocol/training_v1.json',protocol)
    print(json.dumps({'protocol_sha256':sha(ROOT/'protocol/training_v1.json'),'candidates':9,'batch':32,'epochs':10,'concurrentGPUlimit':3}))
if __name__=='__main__':main()
