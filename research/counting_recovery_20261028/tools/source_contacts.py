from pathlib import Path
import hashlib,json,shutil,subprocess
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
frames=[8912,9000,9100,9200,9290,9345,9420,9500,9550,9600,9650,9700,9800,9900,10000,10200,10500,10873]
source=PROJECT/'phase3_diagnosis_20261026/inputs/multicam_original.mp4'
folder=ROOT/'source_contacts';folder.mkdir(exist_ok=True);assert not list(folder.glob('*.jpg'))
selection='+'.join(f'eq(n,{f})' for f in frames)
command=[shutil.which('ffmpeg'),'-v','error','-nostdin','-n','-i',str(source),'-vf',f"select='{selection}',scale=640:360",'-fps_mode','vfr','-frames:v',str(len(frames)),str(folder/'selected_%02d.jpg')]
result=subprocess.run(command,capture_output=True);(ROOT/'results/source_contact_decode_v2.log').write_bytes(result.stderr)
assert result.returncode==0
files=sorted(folder.glob('selected_*.jpg'));assert len(files)==len(frames)
sheet=Image.new('RGB',(3*640,6*390),'white');draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',20)
for i,(path,frame) in enumerate(zip(files,frames)):
    with Image.open(path) as im:im.load();assert im.size==(640,360);picture=im.copy()
    x=(i%3)*640;y=(i//3)*390;sheet.paste(picture,(x,y));draw.text((x+8,y+363),f'Source {frame} | {frame/25:.2f}s | no model overlay',font=font,fill='black')
target=folder/'fixed_source_frames.jpg';sheet.save(target,quality=90)
(ROOT/'results/source_contact_record.json').write_text(json.dumps({'source_frames':frames,'sequential_decode':True,'independent_human_reference':False,
    'selection':'Frozenbaselineuncountedtrackletsanduniformcontext, all selectedbeforecandidate output',
    'contact_sha256':hashlib.sha256(target.read_bytes()).hexdigest()},indent=2),encoding='utf-8')
print(str(target))
