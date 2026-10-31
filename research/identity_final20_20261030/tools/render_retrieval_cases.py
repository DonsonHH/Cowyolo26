"""Post-score explanation panels, all20 IDs and every primary accept/error case."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,math
import numpy as np
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'delivery/results/evaluation'
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=load(ROOT/'protocol/run_v1.json');allrows=load(OUT/'all_decisions.json');a={r['source_index']:r for r in allrows if r['model']=='old_C'and r['policy']=='primary_cal10_fold0'};b={r['source_index']:r for r in allrows if r['model']=='new_C_domain_seed26'and r['policy']=='primary_cal10_fold0'}
chosen={i for i,r in b.items()if r['accepted']}|{i for i,r in a.items()if r['accepted']and(not r['is_known']or r['predicted_id']!=r['identity'])}
for identity in p['roles']['registered']+p['roles']['unknown']:
 options=[i for i,r in b.items()if r['identity']==identity]
 if not any(i in chosen for i in options):chosen.add(min(options,key=lambda i:b[i]['score'])if b[options[0]]['is_known']else max(options,key=lambda i:b[i]['score']))
chosen=sorted(chosen);out=ROOT/'results/retrieval_panels';out.mkdir(exist_ok=False);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',17);small=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',15)
features={}
for model in['old_C','new_C_domain_seed26']:
 with np.load(OUT/model/'all_features.npz')as archive:features[model]=archive['normalized'].astype(float)
manifest=[]
def drawphoto(canvas,path,box):
 with Image.open(path)as image:image=image.convert('RGB');image.thumbnail((box[2]-box[0],box[3]-box[1]));canvas.paste(image,(box[0]+(box[2]-box[0]-image.width)//2,box[1]+(box[3]-box[1]-image.height)//2))

for page in range(math.ceil(len(chosen)/4)):
 canvas=Image.new('RGB',(1260,1120),'#f8f9fa');draw=ImageDraw.Draw(canvas);draw.text((20,15),'Final20 primary results: author query ID and each encoder highest-scoring gallery reference',font=font,fill='#172127')
 for position,index in enumerate(chosen[4*page:4*page+4]):
  source=p['images'][index];y=60+position*250;query=ROOT/source['local_relative_file'];kind='KNOWN'if source['is_known']else'UNKNOWN'
  draw.text((20,y),f"Query #{index}: {kind} ID{source['publisher_identity']}",font=font,fill='#172127');draw.text((20,y+23),source['date'],font=small,fill='#4d555b');drawphoto(canvas,query,(20,y+48,400,y+230));refs={}
  for col,(model,row)in enumerate([('old_C',a[index]),('new_C_domain_seed26',b[index])],1):
   gallery=[j for j,r in enumerate(p['images'])if r['purpose']=='gallery'and r['publisher_identity']==row['predicted_id']];best=max(gallery,key=lambda j:float(np.dot(features[model][index],features[model][j])));ref=ROOT/p['images'][best]['local_relative_file']
   tag=('C'if row['is_known']and row['predicted_id']==row['identity']else'W'if row['is_known']else'FA')if row['accepted']else'U'
   x=20+410*col;draw.text((x,y),f"{'Old'if col==1 else'New'}: ID{row['predicted_id']} score {row['score']:.3f}",font=font,fill='#172127');draw.text((x,y+23),('ACCEPT '+tag)if row['accepted']else'REJECT',font=small,fill='#b64c45'if tag in['W','FA']else'#238774'if tag=='C'else'#4d555b');drawphoto(canvas,ref,(x,y+48,x+380,y+230));refs[model]={'gallery_index':best,'reference_sha256':sha(ref),'candidate':row['predicted_id'],'score':row['score'],'tag':tag}
  manifest.append({'query_index':index,'publisher_ID':source['publisher_identity'],'query_sha256':sha(query),'references':refs})
 draw.text((20,1082),'Selected after scoring for explanation. Curated same-scene crops; C/W/U/FA refer to image queries.',font=small,fill='#4d555b');canvas.save(out/f'page{page+1}.png')
result={'status':'ALL20_ID_EXPLANATION_AND_ALL_PRIMARY_NEW_ACCEPTS_OLD_WRONG_ACCEPTS_RENDERED','created_UTC':datetime.now(timezone.utc).isoformat(),'selected_queries':chosen,'case_count':len(chosen),'unique_publisher_IDs':len({r['publisher_ID']for r in manifest}),'new_primary_accepts_covered':all(i in chosen for i,r in b.items()if r['accepted']),'old_primary_wrong_accepts_covered':all(i in chosen for i,r in a.items()if r['accepted']and(not r['is_known']or r['predicted_id']!=r['identity'])),'selection_is_posthoc_explanation_not_model_selection':True,'rows':manifest,'pages':[{'file':str(path.resolve()),'sha256':sha(path)}for path in sorted(out.glob('*.png'))],'new_model_forwards':0}
(ROOT/'results/retrieval_panel_manifest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'cases':len(chosen),'pages':len(result['pages']),'IDs':result['unique_publisher_IDs']}))
