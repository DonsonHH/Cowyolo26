from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=json.loads((ROOT/'protocol/lost_v1.json').read_text(encoding='utf-8'));check=json.loads((ROOT/'results/local_verification.json').read_text(encoding='utf-8'))
assert check['counter_paths']==12 and check['files']==77
source=(PROJECT/'secondstage_iou_20261028/tools/render_media.py').read_text(encoding='utf-8')
source=source.replace('/secondstage_iou_20261028','/lost_recovery_20261028').replace("check['event_paths']==12 and check['files']==71","check['counter_paths']==12 and check['files']==77")
source=source.replace("c['variant']!='secondstage_iou'","c['variant']!='allow_lost_iou'")
source=source.replace('Secondstage IoU only | same full640 5Hz + handoff','Lost low-score recovery | same IoU cost + handoff')
source=source.replace('Development control. Firststage and counter unchanged. Predicted track ID is not cow identity.',
                      'Development control. Same firststage, IoU gate and counter. Lost recovery needs an actual detection.')
source=source.replace("[9355,9365,9375,9420,10873]","[9355,9365,9375,9420,9700,10873]")
target=ROOT/'tools/render_media.py';assert not target.exists();target.write_text(source,encoding='utf-8')
source=(PROJECT/'secondstage_iou_20261028/tools/render_media.slurm').read_text(encoding='utf-8').replace('/secondstage_iou_20261028','/lost_recovery_20261028').replace('cow-secondstage-media','cow-lost-media')
target=ROOT/'tools/render_media.slurm';assert not target.exists();target.write_text(source,encoding='utf-8',newline='\n')
for name in ['submit_media.sh','status_media.sh']:
    source=(PROJECT/'secondstage_iou_20261028/tools'/name).read_text(encoding='utf-8').replace('/secondstage_iou_20261028','/lost_recovery_20261028').replace('SECONDSTAGE_MEDIA_JOB_ID','LOST_MEDIA_JOB_ID')
    target=ROOT/'tools'/name;assert not target.exists();target.write_text(source,encoding='utf-8')
media={'source_video':'/share/home/renly/projects/idcoo_research_20261026/data/multicam_samples/camera1/2023-08-14T12-54-48.mp4',
       'source_sha256':p['source_sha256'],'local_verification_sha256':sha(ROOT/'results/local_verification.json'),
       'source_scope_inclusive':[8912,10873],'counter_main':'sameconfirmationhandoff','allseeds':[26,27,28],
       'snapshots':[9355,9365,9375,9420,9700,10873],'new_inference':False}
target=ROOT/'protocol/render_v1.json';assert not target.exists();target.write_text(json.dumps(media,indent=2),encoding='utf-8')
print(json.dumps({'render_sha256':sha(ROOT/'tools/render_media.py'),'bound_verification_sha256':media['local_verification_sha256']}))
