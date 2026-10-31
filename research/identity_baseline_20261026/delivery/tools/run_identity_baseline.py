"""Frozen ImageNet encoder + gallery retrieval; threshold precedes eval access."""
from pathlib import Path
import csv,hashlib,json,os,time
from datetime import datetime,timezone
import numpy as np
from PIL import Image,ImageOps,ImageDraw
import torch,torchvision
from torchvision.models import mobilenet_v3_small,MobileNet_V3_Small_Weights
from identity_metrics import calibrate_threshold,summarise,cluster_intervals

ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/identity_baseline');OUT=ROOT/'results/embedding_baseline'
OUT.mkdir(parents=True,exist_ok=False)
audit=json.loads((ROOT/'results/image_audit/summary.json').read_text());assert audit['status']=='PASS'
protocol=json.loads((ROOT/'protocol/identity_pilot_v1.json').read_text())
companion_hash=hashlib.sha256((ROOT/'protocol/aggregation_v1.json').read_bytes()).hexdigest()
assert hashlib.sha256((ROOT/'protocol/identity_pilot_v1.json').read_bytes()).hexdigest()==audit['protocol_sha256']
manifest=json.loads((ROOT/'results/image_audit/audited_manifest.json').read_text())
checkpoint=ROOT/'models/mobilenet_v3_small-047dcff4.pth'
assert hashlib.sha256(checkpoint.read_bytes()).hexdigest()==protocol['embedding']['weights_sha256']
assert torch.cuda.is_available()
torch.manual_seed(26);np.random.seed(26);torch.set_num_threads(4)
torch.backends.cudnn.benchmark=False;torch.backends.cudnn.deterministic=True
original=mobilenet_v3_small(weights=None)
original.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True))
encoder=torch.nn.Sequential(original.features,original.avgpool,torch.nn.Flatten()).eval().cuda()
for parameter in encoder.parameters():parameter.requires_grad_(False)
preprocess=MobileNet_V3_Small_Weights.IMAGENET1K_V1.transforms()
parameter_count=sum(p.numel() for p in encoder.parameters())

def encode(entries):
    vectors=[]
    with torch.inference_mode():
        for i in range(0,len(entries),32):
            batch=[]
            for r in entries[i:i+32]:
                with Image.open(ROOT/r['relative_path']) as im:batch.append(preprocess(im.convert('RGB')))
            feature=encoder(torch.stack(batch).cuda())
            vectors.append(torch.nn.functional.normalize(feature,p=2,dim=1).cpu().numpy())
    return np.concatenate(vectors)

gallery=[r for r in manifest if r['split']=='gallery'];cal=[r for r in manifest if r['split']=='calibration']
assert len(gallery)>0 and len(cal)>0
start=time.perf_counter();g=encode(gallery);cv=encode(cal)
identities=sorted({r['identity'] for r in gallery});indices={identity:[i for i,r in enumerate(gallery) if r['identity']==identity] for identity in identities}
def score(vectors,entries):
    # Scores are computed in NumPy float64 from saved float32 embeddings, so
    # independent scoring is reproducible at threshold equality.
    similarity=vectors.astype(np.float64)@g.astype(np.float64).T
    values=np.stack([similarity[:,indices[identity]].max(1) for identity in identities],axis=1)
    order=np.argsort(-values,axis=1,kind='stable');rows=[]
    for i,entry in enumerate(entries):
        j=int(order[i,0]);rows.append({'relative_path':entry['relative_path'],'identity':entry['identity'],
          'cohort':entry['cohort'],'split':entry['split'],'day':entry['day'],'is_known':entry['cohort']=='known',
          'predicted_id':identities[j],'similarity':float(values[i,j]),'second_similarity':float(values[i,order[i,1]])})
    return rows,values
calrows,calmatrix=score(cv,cal)
threshold=calibrate_threshold([r['similarity'] for r in calrows],[r['predicted_id'] for r in calrows],[r['identity'] for r in calrows],[r['is_known'] for r in calrows])
threshold.update(frozen_at_utc=datetime.now(timezone.utc).isoformat(),protocol_sha256=audit['protocol_sha256'],
                 evaluation_features_computed=False,calibration_paths=[r['relative_path'] for r in cal],
                 calibration_score_sha256=hashlib.sha256(calmatrix.tobytes()).hexdigest())
threshold_path=OUT/'frozen_threshold.json';threshold_path.write_text(json.dumps(threshold,indent=2))
threshold_digest=hashlib.sha256(threshold_path.read_bytes()).hexdigest()
print(json.dumps({'threshold_frozen':True,**{k:v for k,v in threshold.items() if k!='calibration_paths'}}),flush=True)
evaluation=[r for r in manifest if r['split']=='evaluation']
ev=encode(evaluation);evalrows,evalmatrix=score(ev,evaluation)
assert hashlib.sha256(threshold_path.read_bytes()).hexdigest()==threshold_digest
for row in calrows+evalrows:row['accepted']=row['similarity']>=threshold['threshold']
calresult=summarise(calrows);evalresult=summarise(evalrows)
intervals=cluster_intervals(evalresult['per_identity'])
np.savez_compressed(OUT/'embeddings.npz',gallery=g,calibration=cv,evaluation=ev)
(OUT/'embedding_index.json').write_text(json.dumps({'gallery':gallery,'calibration':cal,'evaluation':evaluation,'gallery_identity_order':identities},indent=2))
for split,rows in [('calibration',calrows),('evaluation',evalrows)]:
    with (OUT/f'{split}_predictions.csv').open('w',newline='') as f:w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (OUT/f'{split}_scores.json').write_text(json.dumps(rows,indent=2))
torch.save(encoder.cpu().state_dict(),OUT/'feature_encoder_float32.pt')
errors=[r for r in evalrows if r['is_known'] and r['predicted_id']!=r['identity']][:12]
sheet=Image.new('RGB',(960,max(1,len(errors))*150),'white');draw=ImageDraw.Draw(sheet)
for i,row in enumerate(errors):
    refs=[r for r in gallery if r['identity']==row['predicted_id']];correct_refs=[r for r in gallery if r['identity']==row['identity']]
    for j,item in enumerate([row,refs[len(refs)//2],correct_refs[len(correct_refs)//2]]):
        with Image.open(ROOT/item['relative_path']) as im:sheet.paste(ImageOps.contain(im.convert('RGB'),(315,120)),(j*320,i*150+25))
        draw.text((j*320+3,i*150+4),['query ID '+row['identity'],'pred gallery '+row['predicted_id'],'correct gallery '+row['identity']][j],fill='black')
if errors:sheet.save(OUT/'example_identity_errors.jpg',quality=92)
result={'job_id':os.environ['SLURM_JOB_ID'],'status':'COMPLETED_PUBLIC_CROP_BASELINE','protocol_sha256':audit['protocol_sha256'],
        'predeclared_companion_protocol_sha256':companion_hash,
        'weights_sha256':protocol['embedding']['weights_sha256'],'model':'Frozen ImageNet MobileNetV3-small features + avgpool, no cattle training',
        'feature_dimensions':int(g.shape[1]),'encoder_parameters':parameter_count,'encoder_float32_state_bytes':(OUT/'feature_encoder_float32.pt').stat().st_size,
        'pure_int8_parameter_bytes_estimate':parameter_count,'preprocess':str(preprocess),'threshold':threshold['threshold'],
        'threshold_file_sha256':threshold_digest,'calibration':calresult,'evaluation':evalresult,'evaluation_identity_cluster_intervals':intervals,
        'gallery_identities':len(identities),'gallery_images':len(gallery),'calibration_images':len(cal),'evaluation_images':len(evaluation),
        'torch':torch.__version__,'torchvision':torchvision.__version__,'server_device':torch.cuda.get_device_name(0),
        'total_elapsed_s':time.perf_counter()-start,'scope':protocol['scope'],
        'interpretation':'Curated-crop image-query baseline; ImageNet weights are not a cow identity registry. Gallery binds public anonymous IDs. No end-to-end event, RFID, high-resolution capture or PYNQ performance is established.'}
(OUT/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k not in ['calibration','evaluation','evaluation_identity_cluster_intervals']},indent=2),flush=True)
print(json.dumps({'evaluation':{k:v for k,v in evalresult.items() if k!='per_identity'},'cluster_intervals':intervals},indent=2),flush=True)
