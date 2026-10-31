from pathlib import Path
import hashlib,json,shutil
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
path=ROOT/'results/case_figure_record.json';record=json.loads(path.read_text(encoding='utf-8'));assert record['visual_QA']=='PENDING'
assert len(record['source_images'])==12 and len(record['figures'])==1
for row in record['source_images']+record['figures']:
    f=ROOT/'case_figures'/row['file'];assert sha(f)==row['sha256']
    with Image.open(f) as image:image.load();assert image.size==((2560,1440) if row in record['source_images'] else (1920,1552))
backup=ROOT/'results/case_figure_record_before_visual.json';assert not backup.exists();shutil.copyfile(path,backup)
record.update(visual_QA='PASS',manual_notes=[
 'Allfour ROIrecovery cases, before/recovery/nextframe panels viewed together; selected pinkboxes are actual outputs.',
 'seed28 ID105 low recovery at9365 is followed by no target output at9370, matching the interrupted B streak.',
 'The other three selected recoveries occur near the upper A region; recoveredID129 and ID136 have interrupted observations there.',
 'Panels do not prove physicalID correctness or exclude association switches; no independent truth assigned.'])
path.write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps({'visual_QA':'PASS','native_images':12,'all_ROI_cases':4}))
