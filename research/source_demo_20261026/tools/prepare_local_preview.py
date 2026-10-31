"""Browser media, endpoint pixels, independent event replay, and final derivatives."""
from pathlib import Path
from collections import defaultdict
import concurrent.futures, csv, hashlib, json, shutil, subprocess
import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent
SOURCE=BASE/'phase3_diagnosis_20261026/inputs/multicam_original.mp4'
DELIVERY=ROOT/'delivery/results/preview'
OUT=ROOT/'previews'
FFMPEG=shutil.which('ffmpeg');FFPROBE=shutil.which('ffprobe')
assert FFMPEG and FFPROBE


def run(command,log):
    result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    Path(log).write_bytes(result.stderr)
    assert result.returncode==0,(command,result.stderr.decode(errors='replace')[-2000:])
    return result.stdout


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def independent_events(rows,first,last):
    byframe=defaultdict(list)
    for r in rows:
        byframe[int(r['source_frame'])].append(r)
    states={};events=[]
    for f in range(((first+4)//5)*5,last+1,5):
        active={int(r['track_id']):r for r in byframe.get(f,[])}
        for tid,rec in states.items():
            if tid not in active:rec['candidate']=None;rec['streak']=0
        for tid,row in active.items():
            p=(float(row['y1'])+float(row['y2']))/2880
            if not 0<=p<=1:continue
            rec=states.setdefault(tid,{'origin':None,'candidate':None,'streak':0,'last':-100000})
            if f-rec['last']>50:rec.update(origin=None,candidate=None,streak=0)
            rec['last']=f;zone='A' if p<.4 else 'B' if p>.6 else None
            if zone is None:rec.update(candidate=None,streak=0);continue
            rec['streak']=rec['streak']+1 if zone==rec['candidate'] else 1;rec['candidate']=zone
            if rec['streak']>=3 and rec['origin']!=zone:
                if rec['origin'] is not None:events.append({'source_frame':f,'time_s':f/25,'track_id':tid,'direction':rec['origin']+'->'+zone})
                rec['origin']=zone
    return events


def prepare(name):
    source=DELIVERY/f'{name}_transfer.mp4'
    for extension in ['mp4','webm']:
        dest=OUT/f'{name}_f8912-10873.{extension}'
        assert not dest.exists()
        encoding=(['-c:v','libx264','-preset','veryfast','-crf','25','-pix_fmt','yuv420p','-movflags','+faststart'] if extension=='mp4'
                  else ['-c:v','libvpx-vp9','-deadline','realtime','-cpu-used','7','-crf','36','-b:v','0','-row-mt','1','-pix_fmt','yuv420p'])
        run([FFMPEG,'-hide_banner','-nostdin','-n','-i',str(source),'-an','-threads','2',*encoding,str(dest)],ROOT/'results'/f'{name}_{extension}_encode.log')
    outputs=[]
    for extension in ['mp4','webm']:
        dest=OUT/f'{name}_f8912-10873.{extension}'
        info=json.loads(run([FFPROBE,'-v','error','-count_frames','-show_entries','stream=codec_name,width,height,avg_frame_rate,nb_read_frames:format=duration','-of','json',str(dest)],ROOT/'results'/f'{name}_{extension}_probe.log'))
        stream=info['streams'][0]
        assert stream['nb_read_frames']=='1962' and (stream['width'],stream['height'])==(1280,720)
        assert stream['avg_frame_rate']=='25/1' and abs(float(info['format']['duration'])-78.48)<.01
        run([FFMPEG,'-v','error','-nostdin','-xerror','-i',str(dest),'-f','null','-'],ROOT/'results'/f'{name}_{extension}_decode.log')
        outputs.append({'path':str(dest),'sha256':sha(dest),'bytes':dest.stat().st_size,'frames':1962,'fps':25,'duration_s':78.48,
                        'full_decode':'PASS','codec':stream['codec_name']})
    thumb=OUT/f'{name}_source9420.jpg'
    run([FFMPEG,'-v','error','-nostdin','-n','-ss',str((9420-8912)/25),'-i',str(OUT/f'{name}_f8912-10873.webm'),'-frames:v','1',str(thumb)],ROOT/'results'/f'{name}_thumbnail.log')
    return outputs


def main():
    OUT.mkdir(exist_ok=True)
    summary=json.loads((DELIVERY/'summary.json').read_text())
    assert summary['frames_rendered_each']==1962
    p=summary['source_scope'];assert p['first_frame_inclusive']==8912 and p['last_frame_inclusive']==10873
    events=[]
    for name in ['generic','pilot']:
        rows=list(csv.DictReader((DELIVERY/'inputs'/f'{name}_tracks.csv').open()))
        got=independent_events(rows,8912,10873)
        actual=json.loads((DELIVERY/f'{name}_predicted_events.json').read_text())
        assert got==actual,(name,got,actual)
        events.append({'model':name,'events':len(got),'independent_replay':'PASS','rows':got})
    endpoint_checks=[]
    for ordinal,f in enumerate([8912,10873]):
        server=DELIVERY/'native_checks'/f'source_f{f}.png'
        with Image.open(server) as b:
            b=b.convert('RGB');assert b.size==(2560,1440)
            digest=hashlib.sha256(b.tobytes()).hexdigest();reference=np.asarray(b).astype(np.int16)
        expected=next(r['native_pixels_sha256'] for r in summary['native_checks'] if r['source_frame']==f)
        assert digest==expected
        neighbours=[]
        for j,delta in enumerate([-1,0,1]):
            local=OUT/f'sequential_neighbour_{ordinal*3+j+1:02d}.png'
            assert local.exists(), 'Use full sequential FFmpeg select by frame number, not fast timestamp seeking'
            with Image.open(local) as im:
                assert im.size==(2560,1440)
                difference=np.asarray(im.convert('RGB')).astype(np.int16)-reference
            neighbours.append({'source_frame':f+delta,'mean_squared_RGB_error':float(np.square(difference.astype(float)).mean()),
                               'mean_absolute_RGB_error':float(np.abs(difference).mean()),'max_absolute_RGB_error':int(np.abs(difference).max()),
                               'bitwise_RGB_equal':bool((difference==0).all())})
        best=min(neighbours,key=lambda r:r['mean_squared_RGB_error'])
        assert best['source_frame']==f and sum(r['mean_squared_RGB_error']==best['mean_squared_RGB_error'] for r in neighbours)==1
        endpoint_checks.append({'source_frame':f,'best_of_independently_sequentially_decoded_neighbours':best['source_frame'],
                                'pixel_sha256_preserved_native_png':digest,'neighbour_comparison':neighbours,
                                'RGB_bitwise_parity':best['bitwise_RGB_equal'],
                                'scope':'Frame-content alignment check; cross-decoder RGB colour output is not bitwise identical'})
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        media=[r for group in pool.map(prepare,['generic','pilot']) for r in group]
    record={'status':'FRAME_ALIGNMENT_EVENTS_AND_FOUR_DERIVATIVES_VERIFIED_RGB_DIFFERENCES_RETAINED','scope':p,'native_endpoint_checks':endpoint_checks,
            'independent_event_checks':events,'media':media,'truth_accuracy_claim':False}
    (ROOT/'results/local_preview_verification.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    # Serve only compact derivatives; retain verified archived transfers separately.
    destination=BASE/'phase3_diagnosis_20261026/inputs'
    for name in ['generic','pilot']:
        for extension in ['webm','mp4']:
            source=OUT/f'{name}_f8912-10873.{extension}'
            target=destination/source.name
            assert not target.exists();shutil.copyfile(source,target);assert sha(source)==sha(target)
    manifest={'scope':p,'models':summary['conditions'],'events':events,'media':media,'verification_status':record['status']}
    (BASE/'phase3_diagnosis_20261026/annotation_workbench/model_preview_data.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps({'status':record['status'],'media':media,'events':[(r['model'],r['events']) for r in events]}),flush=True)


if __name__=='__main__':main()
