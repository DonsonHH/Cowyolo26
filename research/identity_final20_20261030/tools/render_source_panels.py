from pathlib import Path
import hashlib,json
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((ROOT/'protocol/run_v1.json').read_text());e=json.loads((ROOT/'protocol/execution_v1.json').read_text());indices=e['source_visual_indices']
out=ROOT/'results/source_panels';out.mkdir(exist_ok=False);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18);records=[]
for page in range(2):
 canvas=Image.new('RGB',(1100,620),'#f8f9fa');draw=ImageDraw.Draw(canvas);draw.text((24,15),'Final20: fixed source examples selected before pixel requests. All90 images retained.',font=font,fill='#172127')
 for pos,index in enumerate(indices[page*4:page*4+4]):
  row=p['images'][index];source=ROOT/row['local_relative_file'];x=20+(pos%2)*550;y=60+(pos//2)*275
  draw.text((x,y),f"index{index} ID{row['publisher_identity']} {row['purpose']} {row['date']}",font=font,fill='#172127')
  with Image.open(source)as image:image=image.convert('RGB');image.thumbnail((510,225));canvas.paste(image,(x+(510-image.width)//2,y+30+(225-image.height)//2))
  records.append({'index':index,'file':row['local_relative_file'],'sha256':sha(source)})
 target=out/f'page{page+1}.png';canvas.save(target)
result={'status':'EIGHT_PRESELECTED_FINAL_SOURCE_SAMPLES_RENDERED_WITHOUT_FILTERING','indices':indices,'records':records,'pages':[{'file':str(path.resolve()),'sha256':sha(path)}for path in sorted(out.glob('*.png'))],'new_model_forwards':0};(ROOT/'results/source_panel_manifest.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'panels':8,'pages':2,'model_forwards':0}))
