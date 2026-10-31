"""Host-confirmed failed job recovery from unchanged delivered artifacts."""
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
from collections import Counter
import json,hashlib,tarfile
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def encode(value):
    if isinstance(value,np.generic):return value.item()
    if isinstance(value,np.ndarray):return value.tolist()
    raise TypeError(type(value).__name__)
def save(p,v):assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,default=encode,indent=2)+'\n',encoding='utf-8')
log=(ROOT/'evidence/loader_collection.txt').read_text(encoding='utf-8')
assert '130619|FAILED|1:0|' in log and '130620|FAILED|1:0|' in log
record=json.loads(next(line for line in log.splitlines() if line.startswith('{')))
archive=ROOT/'loader_failed_delivery_v1.tar.gz'
assert sha(archive)==record['sha256'] and archive.stat().st_size==record['bytes']
dest=ROOT/'loader_delivery';assert not dest.exists();dest.mkdir()
with tarfile.open(archive) as tar:
    members=tar.getmembers();assert len(members)==record['files']
    for m in members:
        name=PurePosixPath(m.name);assert m.isfile() and not name.is_absolute() and '..' not in name.parts
        target=dest.joinpath(*name.parts).resolve();assert target.is_relative_to(dest.resolve()) and not target.exists()
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(m).read())
manifest=load(dest/'results/failed_loader_artifact_manifest.json')
for r in manifest:
    file=dest/r['file'];assert sha(file)==r['sha256'] and file.stat().st_size==r['bytes']
old=dest/'results/loader';rows=load(old/'objects.json');images=load(old/'images.json');batches=load(old/'batches.json')
assert len(images)==6809 and len(batches)==213 and [r['batch'] for r in batches]==list(range(213))
assert sum(r['images'] for r in batches)==6809 and sum(r['label_rows'] for r in batches)==len(rows)
assert len({(r['batch'],r['image_in_batch']) for r in images})==6809
assert all(sum(r['batch']==i for r in images)==b['images'] for i,b in enumerate(batches))
for r in rows:assert 0<=r['batch']<213 and 0<=r['image_in_batch']<batches[r['batch']]['images']
try:json.dumps({'counter':np.int64(2)})
except TypeError:red=True
else:red=False
assert red and json.loads(json.dumps({'counter':np.int64(2),'score':np.float32(.5)},default=encode))=={'counter':2,'score':.5}
summary={'status':'COMPLETE213_BATCH6809_IMAGE_LOADER_RECORDS_RECOVERED_LOCALLY_WITHOUT_REPLAY',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'failed_loader_job':'130619','failed_compute_recovery_job':'130620',
    'sacct_terminal_evidence_host':'mu01','sacct_compute_error_preserved':True,'protocol_sha256':sha(ROOT/'protocol/loader_v1.json'),
    'delivered_batches':213,'delivered_images':6809,'augmented_label_rows':len(rows),'rotation_counts':dict(Counter(r['rotation_turns'] for r in images)),
    'short_side_lt24':sum(r['short_side']<24 for r in rows),'short_side_lt16':sum(r['short_side']<16 for r in rows),
    'short_side_percentiles':np.percentile([r['short_side'] for r in rows],[0,10,25,50,75,90,100]).tolist(),
    'dark_AABB_proxy_median_le80':sum(r['Y_median']<=80 for r in rows),
    'low_contrast_AABB_proxy_le15':sum(r['absolute_median_contrast'] is not None and r['absolute_median_contrast']<=15 for r in rows),
    'overlap_AABB_min_fraction_ge01':sum(r['max_overlap_over_min_area']>=.1 for r in rows),
    'image_label_count_distribution':dict(Counter(r['label_count'] for r in images)),
    'dataset_transform_repr_observed':None,'actual_loader_workers_observed':None,'pin_memory_observed':None,
    'unpersisted_runtime_metadata_not_fabricated':True,'requested_loader_workers':2,
    'CPU_loader_not_formal_training_record':True,'worker_prefetch_not_counted_as_delivered':True,'anchor_file_not_all_mosaic_component_IDs':True,
    'new_loader_batches_in_recovery':0,'new_model_forwards':0,'new_training_updates':0,'whole_goal_complete':False}
out=ROOT/'results/loader_recovery_local';out.mkdir(exist_ok=False);save(out/'summary.json',summary)
save(out/'recovery_verification.json',{'original_artifact_files':manifest,'archive_sha256':record['sha256'],'archive_bytes':record['bytes'],
    'members':len(members),'numeric_serializer_red_reproduced_and_numpy_values_roundtrip_passed':True,
    'new_loader_batches':0,'new_model_forwards':0,'new_training_updates':0})
for r in manifest:assert sha(dest/r['file'])==r['sha256']
print(json.dumps(summary,default=encode))
