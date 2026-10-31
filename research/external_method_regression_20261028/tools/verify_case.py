from pathlib import Path,PurePosixPath
import hashlib,json,tarfile
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    r=load(ROOT/'results/case_delivery_record.json');archive=ROOT/'results/case_delivery.tar.gz';dest=ROOT/'case_delivery';assert not dest.exists()
    assert sha(archive)==r['sha256'] and archive.stat().st_size==r['bytes']
    with tarfile.open(archive,'r:gz') as tf:
        raw=tf.extractfile('delivery_manifest.json').read();assert hashlib.sha256(raw).hexdigest()==r['manifest_sha256']
        items=json.loads(raw);expected={a['path']:a for a in items};members=tf.getmembers()
        assert len(items)==len(expected)==r['manifest_files']==19 and len(members)==r['archive_members']==20
        assert {m.name for m in members}==set(expected)|{'delivery_manifest.json'}
        for m in members:
            name=PurePosixPath(m.name);assert m.isfile() and not name.is_absolute() and '..' not in name.parts and ':' not in m.name
            path=dest.joinpath(*name.parts).resolve();assert path.is_relative_to(dest.resolve());data=tf.extractfile(m).read()
            if m.name in expected:assert len(data)==expected[m.name]['bytes'] and hashlib.sha256(data).hexdigest()==expected[m.name]['sha256']
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);assert sha(path)==hashlib.sha256(data).hexdigest()
    record=load(dest/'results/case/render_record.json');assert len(record['images'])==15 and record['frames']==[110,112,120,125,130]
    for row in record['images']:
        f=dest/'results/case'/row['path'];assert sha(f)==row['sha256'] and f.stat().st_size==row['bytes']
        with Image.open(f) as image:image.load();assert image.size==((1920,1080) if f.name.startswith('native') else (1280,720))
    out=ROOT/'figures';out.mkdir(exist_ok=True);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    sheet=Image.new('RGB',(1920,780),'white');draw=ImageDraw.Draw(sheet)
    for i,variant in enumerate(['secondstage_iou','allow_lost_iou']):
        for j,frame in enumerate([112,120,125]):
            f=dest/f'results/case/{variant}_f{frame}.jpg'
            with Image.open(f) as image:image.load();sheet.paste(image.resize((640,360)),(j*640,i*390))
            draw.text((j*640+8,i*390+364),f'{"PureIoU" if i==0 else "Allow Lost"} | frame{frame} | {frame/30:.3f}s',font=font,fill='black')
    contact=out/'pilot_new_match_case.jpg';sheet.save(contact,quality=93)
    native=Image.new('RGB',(1920,780),'white');draw=ImageDraw.Draw(native)
    for i,frame in enumerate(record['frames']):
        with Image.open(dest/f'results/case/native_f{frame}.jpg') as image:image.load();native.paste(image.resize((640,360)),((i%3)*640,(i//3)*390))
        draw.text(((i%3)*640+8,(i//3)*390+364),f'Native source | frame{frame} | {frame/30:.3f}s',font=font,fill='black')
    nc=out/'native_case_frames.jpg';native.save(nc,quality=93)
    causal=load(ROOT/'results/pilot_case_states.json');changed=next(c for c in causal['conditions'] if c['variant']=='allow_lost_iou')
    assert changed['events_for_target_ID']==[{'time_s':125/30,'track_id':1,'direction':'B->A','frame':125}]
    state={s['frame']:s for s in changed['states']}
    assert state[112]['handoff_state']['origin']=='B' and state[120]['observed_axis']<.4 and state[121]['observed_axis'] is None
    assert [state[f]['handoff_state']['streak'] for f in [123,124,125]]==[1,2,3]
    outrecord={'status':'NINETEEN_CASE_FILES_15_IMAGES_DECODED_AND_STATE_CASE_BOUND','files':19,'images_full_decoded':15,
       'native_source_images':5,'main_overlay_panels':6,'component_replays_exact':3,
       'source_sha256':record['source_sha256'],'figures':[{'file':f.name,'sha256':sha(f)} for f in [contact,nc]],
       'manual_visual_QA':'PENDING','same_numeric_ID_not_identity_proof':True,'new_independent_test':False}
    target=ROOT/'results/case_local_verification.json';assert not target.exists();target.write_text(json.dumps(outrecord,indent=2),encoding='utf-8');print(json.dumps(outrecord))
if __name__=='__main__':main()
