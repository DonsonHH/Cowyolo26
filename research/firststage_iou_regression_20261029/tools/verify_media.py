from pathlib import Path,PurePosixPath
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
import hashlib,json,subprocess,tarfile
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify_movie(row):
    path=ROOT/'media_delivery'/row['path'];assert sha(path)==row['sha256']
    proc=subprocess.run(['ffprobe','-v','error','-threads','2','-count_frames','-select_streams','v:0','-show_entries',
         'stream=width,height,avg_frame_rate,nb_read_frames,codec_name','-of','json',str(path)],capture_output=True,text=True)
    assert proc.returncode==0 and not proc.stderr,proc.stderr
    stream=json.loads(proc.stdout)['streams'][0]
    assert [stream['width'],stream['height']]==row['dimensions'] and stream['avg_frame_rate']==str(row['fps'])+'/1'
    assert int(stream['nb_read_frames'])==row['frames'] and stream['codec_name']=='h264'
    strict=subprocess.run(['ffmpeg','-hide_banner','-v','error','-xerror','-threads','2','-i',str(path),'-an','-f','null','-'],capture_output=True,text=True)
    assert strict.returncode==0 and not strict.stderr,strict.stderr
    return {**row,'absolute_path':str(path.resolve()),'local_strict_full_decode':'PASS'}
def main():
    record=load(ROOT/'evidence/media_delivery_record.json');archive=ROOT/'media_delivery.tar.gz';dest=ROOT/'media_delivery'
    assert archive.stat().st_size==record['archive_bytes'] and sha(archive)==record['archive_sha256'] and not dest.exists()
    with tarfile.open(archive,'r:gz') as tf:
        rows=json.loads(tf.extractfile('media_delivery_manifest.json').read())['files'];expected={r['file']:r for r in rows};members=tf.getmembers()
        assert len(rows)==len(expected) and len(members)==record['files']==len(rows)+1
        assert {m.name for m in members}==set(expected)|{'media_delivery_manifest.json'}
        for m in members:
            name=PurePosixPath(m.name);assert m.isfile() and not name.is_absolute() and '..' not in name.parts and ':' not in m.name
            target=dest.joinpath(*name.parts).resolve();assert target.is_relative_to(dest.resolve());data=tf.extractfile(m).read()
            if m.name in expected:assert len(data)==expected[m.name]['bytes'] and hashlib.sha256(data).hexdigest()==expected[m.name]['sha256']
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
            assert sha(target)==hashlib.sha256(data).hexdigest()
    summary=load(dest/'results/media/summary.json');p=load(ROOT/'protocol/regression_v1.json');q=load(ROOT/'protocol/media_v1.json')
    assert sha(dest/'protocol/media_v1.json')==sha(ROOT/'protocol/media_v1.json')==summary['media_protocol_sha256']
    assert sha(dest/'tools/render.py')==sha(ROOT/'tools/render.py')
    assert len(summary['movies'])==9 and len(summary['case_sheets'])==31
    with ThreadPoolExecutor(max_workers=3) as pool:movies=list(pool.map(verify_movie,summary['movies']))
    assert sum(r['frames'] for r in movies)==summary['all_movie_frames_decoded']==8444
    raster=[]
    for row in summary['native_sources']+summary['case_sheets']:
        path=dest/row['path'];assert sha(path)==row['sha256']
        with Image.open(path) as im:im.verify()
        raster.append({'path':str(path.resolve()),'sha256':sha(path)})
    for case in summary['case_sheets']:
        assert sha(dest/case['native_path'])==case['native_sha256']
        source=next(s for s in p['sources'] if s['name']==case['source']);spec=q['videos'][source['scene']]
        assert case['sample_frame0']==case['frame0']-case['frame0']%source['stride']
        for item in case['counter_values']:
            folder=ROOT/'delivery/results'/(source['name']+'__'+item['variant'])
            events=load(folder/'handoff_events_all_history.json')
            selected=[e for e in events if spec['start_frame0']<=e['frame0']<=case['frame0'] and e['frame0']<spec['end_frame0_exclusive']]
            assert item['A_to_B']==sum(e['direction']=='A->B' for e in selected)
            assert item['B_to_A']==sum(e['direction']=='B->A' for e in selected)
    result={'status':'NINE_PAIRED_MEDIA_FULLY_DECODED_31_CASES_HASHES_AND_COUNT_OVERLAYS_VERIFIED',
            'archive_sha256':sha(archive),'archive_members':len(members),'manifest_files':len(rows),
            'movies':movies,'movie_count':9,'decoded_frames':8444,'rasters':raster,'raster_count':len(raster),
            'case_sheets':summary['case_sheets'],'native_source_images':len(summary['native_sources']),
            'case_panels':62,'actual_visual_review_required':True,'candidate_adopted':False,'whole_goal_complete':False}
    path=ROOT/'results/media_verification.json';assert not path.exists();path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['movies','rasters','case_sheets']}))
if __name__=='__main__':main()
