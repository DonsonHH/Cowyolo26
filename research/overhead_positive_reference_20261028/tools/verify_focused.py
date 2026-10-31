from pathlib import Path,PurePosixPath
import hashlib,json,subprocess,tarfile
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    expected=json.loads((ROOT/'evidence/focused_archive_record.json').read_text(encoding='utf-8'));archive=ROOT/'focused_delivery.tar.gz'
    assert archive.stat().st_size==expected['archive_bytes'] and sha(archive)==expected['archive_sha256']
    out=ROOT/'focused_delivery';out.mkdir(exist_ok=False)
    with tarfile.open(archive) as t:
        members=t.getmembers()
        for m in members:
            n=PurePosixPath(m.name);assert m.isfile() and not n.is_absolute() and '..' not in n.parts
        t.extractall(out,filter='data')
    s=json.loads((out/'results/focused/summary.json').read_text(encoding='utf-8'));p=json.loads((ROOT/'protocol/focused_review_v1.json').read_text(encoding='utf-8'))
    assert s['protocol_sha256']==sha(ROOT/'protocol/focused_review_v1.json') and s['source_sha256']==p['source_sha256']
    images=[];media=[]
    for window,spec in zip(s['windows'],p['windows']):
        assert window['name']==spec['name']
        assert [r['frame0'] for r in window['samples']]==list(range(spec['start_frame0'],spec['end_frame0_exclusive'],5))
        for r in [*window['samples'],*window['contact_pages']]:
            f=out/r['file'];assert sha(f)==r['sha256']
            with Image.open(f) as im:im.load();size=im.size
            if 'native_crop_size' in r:assert list(size)==r['native_crop_size']
            images.append({'path':str(f),'sha256':sha(f),'size':size})
        m=out/window['movie'];assert sha(m)==window['movie_sha256']
        proc=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-count_frames','-show_entries','stream=width,height,r_frame_rate,nb_read_frames','-of','json',str(m)],capture_output=True,check=True)
        assert not proc.stderr;probe=json.loads(proc.stdout)['streams'][0]
        assert (probe['width'],probe['height'],probe['r_frame_rate'])==(480,700,'5/1') and int(probe['nb_read_frames'])==spec['sample_frames']
        media.append({'path':str(m),'sha256':sha(m),'full_decoded_frames':int(probe['nb_read_frames'])})
    assert s['sample_images']==625 and s['contact_images']==125 and len(images)==637 and len(media)==3
    result={'status':'FOCUSED_CROPS_CONTACTS_AND_THREE_MEDIA_HASHES_AND_FULL_DECODES_VERIFIED','archive_files':len(members),
            'sample_images':625,'one_Hz_contact_panels':125,'contact_pages':12,'all_rasters_decoded':len(images),
            'full_video_decode_frames':sum(r['full_decoded_frames'] for r in media),'media':media,'images':images,
            'models_used':False,'event_reference_available':False,'visual_review_pending':True,'whole_goal_complete':False}
    target=ROOT/'results/focused_verification.json';assert not target.exists();target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['media','images']}),flush=True)
if __name__=='__main__':main()
