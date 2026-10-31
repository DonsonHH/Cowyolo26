"""Check newly downloaded long-video ranges and safe extraction of native review media."""
from pathlib import Path,PurePosixPath
import hashlib,json,subprocess,tarfile
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))

def main():
    expected=load(ROOT/'evidence/native_archive_record.json');archive=ROOT/'native_review_delivery.tar.gz'
    assert archive.stat().st_size==expected['archive_bytes'] and sha(archive)==expected['archive_sha256']
    out=ROOT/'native_review_delivery';out.mkdir(exist_ok=False)
    with tarfile.open(archive) as t:
        members=t.getmembers()
        for m in members:
            n=PurePosixPath(m.name);assert m.isfile() and not n.is_absolute() and '..' not in n.parts
        t.extractall(out,filter='data')
    base=out/'results/native_review';summary=load(base/'summary.json');selection=ROOT/'protocol/selection_v1.json';source=load(ROOT/'input/video_ranges/manifest.json')
    assert summary['protocol_sha256']==source['protocol_sha256']==sha(selection)
    src=Path(source['local_path']);assert sha(src)==source['source_sha256']==summary['source_sha256']
    assert src.stat().st_size==source['source_bytes']==summary['source_bytes']
    actual=hashlib.sha256();rows=[r for r in source['range_reads'] if r['file'].startswith('part_')];offset=0
    for r in rows:
        f=ROOT/'input/video_ranges'/r['file'];assert sha(f)==r['sha256'] and f.stat().st_size==r['bytes']
        assert r['start']==offset and r['end_exclusive']-r['start']==r['bytes'] and r['object_bytes']==source['source_bytes']
        actual.update(f.read_bytes());offset=r['end_exclusive']
    assert actual.hexdigest()==source['source_sha256'] and offset==source['source_bytes']
    for r in source['range_reads']:
        assert r['Content-Range']==f"bytes {r['start']}-{r['end_exclusive']-1}/{r['object_bytes']}"
    image_rows=[*summary['overview_snapshots'],*summary['native_30s_anchors'],*summary['overview_pages']];images=[]
    for row in image_rows:
        f=base/row['file'];assert sha(f)==row['sha256']
        with Image.open(f) as im:im.load();size=im.size
        if 'image_size' in row:assert list(size)==row['image_size']
        images.append({'file':row['file'],'sha256':sha(f),'size':size})
    movie=base/summary['review_movie'];assert sha(movie)==summary['review_movie_sha256']
    proc=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-count_frames','-show_entries','stream=width,height,nb_read_frames,r_frame_rate','-of','json',str(movie)],capture_output=True,check=True)
    assert not proc.stderr;probe=json.loads(proc.stdout);v=probe['streams'][0]
    assert (v['width'],v['height'])==(480,700) and int(v['nb_read_frames'])==summary['review_movie_frames'] and v['r_frame_rate']=='5/1'
    result={'status':'NATIVE_LONG_SOURCE_RANGE_RECONSTRUCTION_AND_REVIEW_DELIVERY_VERIFIED','archive_files':len(members),
            'source_bytes':source['source_bytes'],'source_sha256':source['source_sha256'],'source_frames':summary['source_frames'],
            'range_chunks':len(rows),'images_fully_decoded':len(images),'images':images,
            'review_movie_sha256':sha(movie),'review_movie_full_decoded_frames':int(v['nb_read_frames']),
            'review_movie_duration_s':summary['review_movie_duration_s'],'source_duration_s':summary['duration_s'],
            'visual_QA_pending':True,'new_model_predictions':False,'event_reference_available':False,'whole_goal_complete':False}
    target=ROOT/'results/native_delivery_verification.json';target.parent.mkdir(exist_ok=True);assert not target.exists();target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='images'}),flush=True)

if __name__=='__main__':main()
