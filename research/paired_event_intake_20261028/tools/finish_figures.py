from pathlib import Path
import hashlib,json,shutil
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
path=ROOT/'results/exit_case_figure_record.json';r=json.loads(path.read_text(encoding='utf-8'));assert r['visual_QA']=='PENDING'
for row in r['source_files']+r['figures']:
    p=ROOT/'figures'/row['path'];assert sha(p)==row['sha256']
    with Image.open(p) as image:
        image.load()
        if row in r['source_files']:assert image.size==(2560,1440)
        else:assert image.size==(1920,788)
shutil.copyfile(path,ROOT/'results/exit_case_figure_record_before_visual_QA.json')
r.update(visual_QA='PASS',manual_visual_observations=[
 'Six nativeframes and two contact sheets inspected; orangeROI and gates unchanged.',
 'At9365 a lowscore box overlaps the darker moving object; at9370 the lowscore box is on a different/right-side extent.',
 'Dashedpink ID117 box is a lost Kalman state, never drawn or counted as an observed detection.',
 'Geometric overlap and visual case inspection do not certify physical identity correspondence or independent event truth.'])
path.write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps({'visual_QA':'PASS','native_frames':6,'contact_sheets':2}))
