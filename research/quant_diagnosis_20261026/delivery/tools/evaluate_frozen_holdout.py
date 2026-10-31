from pathlib import Path
from collections import defaultdict,Counter
import hashlib,json,os,sys
import numpy as np
import onnxruntime as ort
from PIL import Image,ImageOps,ImageDraw
PROJECT=Path('/share/home/renly/projects/idcoo_research_20261026');ROOT=PROJECT/'quant_diagnosis'
sys.path.insert(0,str(PROJECT/'identity_training/tools'))
from identity_metrics import summarise,cluster_intervals

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    OUT=ROOT/'results/future_holdout';OUT.mkdir(parents=True,exist_ok=False)
    pp=ROOT/'protocol/future_comparison_frozen.json';p=json.loads(pp.read_text());stage=json.loads((ROOT/'catalog/future_holdout/stage_complete.json').read_text())
    assert sha(pp)==stage['frozen_protocol_sha256']
    manifest=json.loads((ROOT/'catalog/future_holdout/image_manifest.json').read_text());assert len(manifest)==90
    assert sha(ROOT/'catalog/future_holdout/image_manifest.json')==stage['manifest_sha256']
    assert sha(ROOT/'results/mixed/candidate_and_thresholds_frozen.json')==p['mixed_validation_freeze_sha256']
    previous=json.loads((PROJECT/'identity_training/results/input_audit/manifest.json').read_text())+json.loads((PROJECT/'identity_baseline/results/image_audit/audited_manifest.json').read_text())
    old_ids={r['identity'] for r in previous};old_pixels={r['pixel_sha256'] for r in previous}
    assert not old_ids&set(p['roles']['registered_ids']+p['roles']['unknown_ids'])
    images={};pixels=defaultdict(list);audited=[]
    for row in manifest:
        path=ROOT/row['relative_path'];assert sha(path)==row['sha256'] and path.stat().st_size==row['bytes']
        with Image.open(path) as im:im.load();im=im.convert('RGB');w,h=im.size;pixels_hash=hashlib.sha256(w.to_bytes(4,'big')+h.to_bytes(4,'big')+im.tobytes()).hexdigest();images[row['relative_path']]=im.copy()
        assert row['identity'] in p['roles'][row['role']] and row['source_url'].endswith('_1.jpg')
        assert pixels_hash not in old_pixels
        pixels[pixels_hash].append(row);audited.append({**row,'width':w,'height':h,'pixel_sha256':pixels_hash})
    assert all(len({r['split'] for r in group})==1 for group in pixels.values())
    for identity in p['roles']['registered_ids']:assert sum(r['identity']==identity and r['split']=='gallery' for r in audited)==5
    for identity in p['roles']['registered_ids']+p['roles']['unknown_ids']:assert sum(r['identity']==identity and r['split']=='query' for r in audited)==5
    (OUT/'audited_manifest.json').write_text(json.dumps(audited,indent=2))
    audit={'images':len(audited),'fully_decoded':True,'new_IDs_outside_previous_cohorts':True,'no_pixel_duplicates_with_old_cohorts':True,
           'no_cross_role_exact_pixel_duplicates':True,'minimum_side':min(min(r['width'],r['height']) for r in audited),
           'frozen_protocol_sha256':sha(pp),'identity_counts':{'registered':6,'unknown':6},'graph_forward_started':False}
    (OUT/'input_audit_before_inference.json').write_text(json.dumps(audit,indent=2));audit_hash=sha(OUT/'input_audit_before_inference.json')
    gallery_rows=[r for r in audited if r['split']=='gallery'];query_rows=[r for r in audited if r['split']=='query']
    def tensor(row):
        im=ImageOps.pad(images[row['relative_path']],(224,224),method=Image.Resampling.BILINEAR,color=(127,127,127),centering=(.5,.5))
        value=np.asarray(im).transpose(2,0,1).astype(np.float32)/np.float32(255)
        value=(value-np.array([.485,.456,.406],np.float32)[:,None,None])/np.array([.229,.224,.225],np.float32)[:,None,None]
        return np.ascontiguousarray(value[None])
    g_inputs=[tensor(r) for r in gallery_rows];q_inputs=[tensor(r) for r in query_rows]
    ids=sorted(p['roles']['registered_ids']);results=[]
    for condition in p['conditions']:
        graph=Path(condition['model_path']);assert sha(graph)==condition['model_sha256']
        opts=ort.SessionOptions();opts.intra_op_num_threads=2;opts.inter_op_num_threads=1
        runtime=ort.InferenceSession(str(graph),sess_options=opts,providers=['CPUExecutionProvider'])
        g=np.concatenate([runtime.run(None,{'images':t})[0] for t in g_inputs]);q=np.concatenate([runtime.run(None,{'images':t})[0] for t in q_inputs])
        similarity=q.astype(float)@g.astype(float).T
        scores=np.stack([similarity[:,[i for i,r in enumerate(gallery_rows) if r['identity']==identity]].max(1) for identity in ids],axis=1)
        predictions=[]
        for r,values in zip(query_rows,scores):
            best=int(np.argmax(values));predictions.append({'relative_path':r['relative_path'],'identity':r['identity'],
                'is_known':r['role']=='registered_ids','predicted_id':ids[best],'similarity':float(values[best]),'accepted':bool(values[best]>=condition['threshold'])})
        metrics=summarise(predictions);directory=OUT/condition['name'];directory.mkdir()
        np.savez_compressed(directory/'embeddings.npz',gallery=g,query=q)
        (directory/'predictions.json').write_text(json.dumps(predictions,indent=2))
        record={**condition,'metrics':metrics,'identity_cluster_intervals':cluster_intervals(metrics['per_identity'])}
        (directory/'summary.json').write_text(json.dumps(record,indent=2));results.append(record)
        print(json.dumps({'condition':condition['name'],'C':metrics['known_correct_accepted_C'],'W':metrics['known_wrong_accepted_W'],
                          'U':metrics['known_rejected_U'],'top1':metrics['known_closed_top1_correct'],'unknown_false_accepts':metrics['unknown_false_accepts']}),flush=True)
        del runtime
    assert sha(pp)==stage['frozen_protocol_sha256'] and sha(OUT/'input_audit_before_inference.json')==audit_hash
    (OUT/'feature_index.json').write_text(json.dumps({'gallery':gallery_rows,'query':query_rows,'identity_order':ids},indent=2))
    # Visual review occurs after all fixed predictions; never changes selection.
    sheet=Image.new('RGB',(960,6*175),'white');draw=ImageDraw.Draw(sheet)
    for i,identity in enumerate(ids):
        gs=[r for r in gallery_rows if r['identity']==identity];qs=[r for r in query_rows if r['identity']==identity]
        for j,row in enumerate([gs[2],qs[0],qs[2]]):
            sheet.paste(ImageOps.contain(images[row['relative_path']],(315,145)),(j*320,i*175+25))
            draw.text((j*320+3,i*175+4),f'ID {identity} '+('registered Aug14' if j==0 else 'query Aug20'),fill='black')
    sheet.save(OUT/'registered_source_contact.jpg',quality=92)
    summary={'status':'FROZEN_NEW_IDENTITY_HOLDOUT_COMPLETE','job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(pp),
             'selected_recipe':p['selected_recipe'],'audit':audit,'conditions':results,'all_declared_models_reported':True,
             'thresholds_recalibrated_on_holdout':False,'scope':p['scope'],'whole_goal_complete':False}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2))
if __name__=='__main__':main()
