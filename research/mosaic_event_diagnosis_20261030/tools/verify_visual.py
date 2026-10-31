from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
v=load(ROOT/'results/visual_manifest.json');assert v['panels']==9 and sha(v['file'])==v['sha256']
with Image.open(v['file']) as im:
    im.load();assert im.size==(1540,1690)
    for i,row in enumerate(v['source_records']):
        assert sha(row['native_file'])==row['native_sha256'] and sha(row['new_input_path'])==row['new_input_sha256']
        with Image.open(row['new_input_path']) as new,Image.open(row['old_input_path']) as old:
            assert new.convert('RGB').tobytes()==old.convert('RGB').tobytes()
            exact=new.convert('RGB').resize((384,384),Image.Resampling.NEAREST)
            y=114+i*505+40;assert im.crop((735,y,1119,y+384)).tobytes()==exact.tobytes()
result={'status':'THREE_NATIVE_SOURCES_AND_OLD_NEW_SHARED_INPUT_PANEL_BYTES_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),
    'actual_image_file':v['file'],'actual_image_sha256':v['sha256'],'actually_viewed':True,'panels_actually_viewed':9,
    'exact_shared_input_panels':3,'references_are_old_model_outputs_not_GT':True,'new_network_forwards':0,'whole_goal_complete':False}
f=ROOT/'results/visual_review.json';assert not f.exists();f.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
