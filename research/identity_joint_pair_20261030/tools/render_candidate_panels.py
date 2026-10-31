"""Show all ten unchanged photos and old/new candidates; identity GT is unknown."""
from pathlib import Path
import hashlib,json
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
plan=load(ROOT/'protocol/run_v1.json');jobs=load(ROOT/'results/actual_job_rows.json')
fontpath=Path('C:/Windows/Fonts/arial.ttf');font=ImageFont.truetype(str(fontpath),21);small=ImageFont.truetype(str(fontpath),17)
with np.load(PROJECT/'pynq_identity_ncnn_20261029/board_delivery/vectors_results_v3/all_normalized_features.npz')as a:oldgallery=a['new_gallery'].astype(float)
with np.load(ROOT/'board_delivery/results/identity_qualification/all_features.npz')as a:newgallery=a['normalized'][:30].astype(float)
galleryrows=plan['identity_reference_images'][:30];out=ROOT/'results/candidate_panels';out.mkdir(exist_ok=False);records=[]

def thumb(canvas,path,box):
 with Image.open(path)as image:image=image.convert('RGB');image.thumbnail((box[2]-box[0],box[3]-box[1]));canvas.paste(image,(box[0]+(box[2]-box[0]-image.width)//2,box[1]+(box[3]-box[1]-image.height)//2))

for page in range(5):
 canvas=Image.new('RGB',(1140,680),'#f8f9fa');draw=ImageDraw.Draw(canvas);draw.text((24,15),'Same fixed photos: old/new top candidates (identity ground truth unavailable)',fill='#172127',font=font)
 for rownum,i in enumerate(range(page*2,page*2+2)):
  top=65+rownum*295;old=next(j for j in jobs if j['repeat']==1 and j['identity_model']=='old'and j['fixed_job_index']==i);new=next(j for j in jobs if j['repeat']==1 and j['identity_model']=='new'and j['fixed_job_index']==i);photo=Path(old['photo_file']);assert sha(photo)==old['photo_sha256']==new['photo_sha256']
  draw.text((22,top),f"Photo {i}: source frame {old['source_frame0']}",font=small,fill='#172127');thumb(canvas,photo,(20,top+28,345,top+255));references={}
  for column,(model,job,gallery)in enumerate([('old',old,oldgallery),('new',new,newgallery)],1):
   folder=ROOT/'board_delivery/results'/job['run']/'background';record=load(folder/'record.json')['jobs'][i]
   with np.load(folder/record['vector_file'])as a:feature=a['normalized'].astype(float)
   candidates=[k for k,r in enumerate(galleryrows)if r['identity']==job['predicted_id']];winner=max(candidates,key=lambda k:float(np.dot(feature,gallery[k])));ref=Path(galleryrows[winner]['local_image']);x=column*375
   caption=f"{model}: ID{job['predicted_id']}  score {job['similarity']:.3f}  "+('ACCEPT'if job['accepted']else'REJECT')
   draw.text((x,top),caption,font=small,fill='#172127');thumb(canvas,ref,(x,top+28,x+345,top+255));references[model]={'candidate':job['predicted_id'],'accepted':job['accepted'],'reference_image':str(ref),'reference_sha256':sha(ref),'gallery_index':winner}
  records.append({'fixed_job_index':i,'photo_sha256':sha(photo),'references':references,'identity_GT_known':False})
 draw.text((24,652),'Reference photos are Aug19; source event is Aug14. Retrospective retrieval; no ID correctness claim.',font=small,fill='#4d555b');p=out/f'page{page+1}.png';canvas.save(p)
v={'status':'ALL10_UNCHANGED_PHOTOS_OLD_NEW_CANDIDATES_AND_MAX_REFERENCE_BINDINGS_RENDERED','pages':[{'file':str(p.resolve()),'sha256':sha(p)}for p in sorted(out.glob('*.png'))],'rows':records,'panel_labels_are_candidate_outputs_not_ground_truth':True,'model_forwards':0};p=ROOT/'results/candidate_panel_manifest.json';assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n');print(json.dumps({'pages':5,'rows':10}))
