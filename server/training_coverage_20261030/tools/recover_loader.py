"""Recover terminal failed loader's completed records; never rerun its loader."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import json,hashlib,os,socket,subprocess
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
state=subprocess.check_output(['sacct','-j','130619','-X','--noheader','--format=State,ExitCode','-P'],text=True).strip()
assert state.startswith('FAILED|1:0'),state
old=ROOT/'results/loader';out=ROOT/'results/loader_recovered';assert not out.exists()
files=sorted(p for p in old.rglob('*') if p.is_file())
before={p.relative_to(ROOT).as_posix():sha(p) for p in files}
assert not (old/'summary.json').exists()
rows=load(old/'objects.json');images=load(old/'images.json');batches=load(old/'batches.json')
assert len(images)==6809 and len(batches)==213 and sum(r['label_rows'] for r in batches)==len(rows)
assert [r['batch'] for r in batches]==list(range(213))
assert sum(r['images'] for r in batches)==6809
assert Counter((r['batch'],r['image_in_batch']) for r in images).most_common(1)[0][1]==1
assert all(sum(r['batch']==i for r in images)==b['images'] for i,b in enumerate(batches))
for r in rows:
    assert 0<=r['batch']<213 and 0<=r['image_in_batch']<batches[r['batch']]['images']
for i in range(3):
    with np.load(old/'pixel_controls'/('batch'+str(i)+'.npz')) as ar:
        assert ar['RGB'].shape==(32,3,192,192)
        assert sha(old/'pixel_controls'/('batch'+str(i)+'.npz'))==before['results/loader/pixel_controls/batch'+str(i)+'.npz']
p=load(ROOT/'protocol/loader_v1.json')
summary={'status':'ONE_REAL_TRAIN_LOADER_EPOCH213_BATCHES6809_IMAGES_RECOVERED_WITHOUT_LOADER_RERUN',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'failed_loader_job':'130619','recovery_job':os.environ['SLURM_JOB_ID'],
    'protocol_sha256':sha(ROOT/'protocol/loader_v1.json'),'delivered_batches':213,'delivered_images':6809,'augmented_label_rows':len(rows),
    'rotation_counts':dict(Counter(r['rotation_turns'] for r in images)),
    'short_side_lt24':sum(r['short_side']<24 for r in rows),'short_side_lt16':sum(r['short_side']<16 for r in rows),
    'short_side_percentiles':np.percentile([r['short_side'] for r in rows],[0,10,25,50,75,90,100]).tolist(),
    'dark_AABB_proxy_median_le80':sum(r['Y_median']<=80 for r in rows),
    'low_contrast_AABB_proxy_le15':sum(r['absolute_median_contrast'] is not None and r['absolute_median_contrast']<=15 for r in rows),
    'overlap_AABB_min_fraction_ge01':sum(r['max_overlap_over_min_area']>=.1 for r in rows),
    'image_label_count_distribution':dict(Counter(r['label_count'] for r in images)),
    'dataset_transform_repr_observed':None,'actual_loader_workers_observed':None,'pin_memory_observed':None,
    'unpersisted_runtime_metadata_not_fabricated':True,'requested_loader_workers':2,
    'CPU_loader_not_formal_training_record':True,'worker_prefetch_not_counted_as_delivered':True,
    'anchor_file_not_all_mosaic_component_IDs':True,'validation_or_holdout_or_source_video_pixels':0,
    'new_loader_batches_in_recovery':0,'new_model_forwards':0,'new_training_updates':0,'whole_goal_complete':False}
out.mkdir();save(out/'summary.json',summary)
assert all(sha(ROOT/name)==digest for name,digest in before.items())
save(out/'original_files_unchanged.json',{'status':'ALL_FAILED_LOADER_FILES_HASH_UNCHANGED','files':[{'file':name,'sha256':digest} for name,digest in before.items()]})
save(ROOT/'results/loader_recovery_manifest.json',[{'file':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in [*files,*sorted(out.glob('*'))]])
print(json.dumps(summary),flush=True)
