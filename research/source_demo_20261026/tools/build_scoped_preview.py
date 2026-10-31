"""Replay preserved actual detector outputs over user-selected original frames only."""
from pathlib import Path
from collections import defaultdict
import csv, hashlib, json, os, shutil, sys
import cv2
from PIL import Image, ImageDraw

PROJECT=Path('/share/home/renly/projects/idcoo_research_20261026')
ROOT=PROJECT/'source_demo'
sys.path.insert(0,str(PROJECT/'phase2/tools'))
from zone_counter import ZoneCounter


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def save(path,value):Path(path).write_text(json.dumps(value,indent=2),encoding='utf-8')


def main():
    cv2.setNumThreads(2)
    out=ROOT/'results/preview';out.mkdir(parents=True,exist_ok=False)
    (out/'native_checks').mkdir();(out/'inputs').mkdir()
    protocol=ROOT/'protocol/source_scope_v1.json';p=json.loads(protocol.read_text())
    first,last=p['first_frame_inclusive'],p['last_frame_inclusive']
    assert (first,last)==(8912,10873)
    source=PROJECT/'data/multicam_samples/camera1/2023-08-14T12-54-48.mp4'
    assert sha(source)==p['source_sha256']
    specs=[('generic','Official YOLO26n',PROJECT/'results/multicam_count_dev',PROJECT/'models/yolo26n.pt',
            '9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef'),
           ('pilot','OpenCows2020 5-epoch pilot',PROJECT/'results/multicam_count_finetuned_dev',
            PROJECT/'results/detection_pilot/five_epoch_dev/weights/best.pt',
            '9b38f145a01585908fa9f1c44f3b00e4fb43f3cdf7f1fe2c8c387252ce47e81b')]
    histories={};conditions=[]
    for name,title,directory,weights,digest in specs:
        assert sha(weights)==digest
        cache=directory/'tracks.csv'; rows=list(csv.DictReader(cache.open()))
        by_frame=defaultdict(list)
        for row in rows:
            f=int(row['source_frame']);assert f%5==0 and abs(float(row['time_s'])-f/25)<1e-6
            if first<=f<=last:by_frame[f].append(row)
        for f in by_frame:
            ids=[r['track_id'] for r in by_frame[f]];assert len(ids)==len(set(ids))
        histories[name]={'rows':by_frame,'counter':ZoneCounter(),'current':[],'events':[],'last_tick':None}
        shutil.copy2(cache,out/'inputs'/f'{name}_tracks.csv')
        shutil.copy2(directory/'summary.json',out/'inputs'/f'{name}_inference_summary.json')
        conditions.append({'name':name,'title':title,'weights':str(weights),'weights_sha256':digest,
                           'track_cache_sha256':sha(cache),'original_inference_summary':json.loads((directory/'summary.json').read_text()),
                           'inference_is_reused_actual_artifact':True,'fresh_inference_this_render':False})
    cap=cv2.VideoCapture(str(source));assert cap.isOpened()
    assert (cap.get(cv2.CAP_PROP_FPS),int(cap.get(3)),int(cap.get(4)))==(25.,2560,1440)
    assert cap.set(cv2.CAP_PROP_POS_FRAMES,first)
    assert round(cap.get(cv2.CAP_PROP_POS_FRAMES))==first
    writers={name:cv2.VideoWriter(str(out/f'{name}_transfer.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),25.,(1280,720))
             for name in ['source','generic','pilot']}
    assert all(w.isOpened() for w in writers.values())
    chosen=[first,8995,9310,9420,9700,9900,10835,last]
    contacts={};native_checks=[];frames=0
    for f in range(first,last+1):
        assert round(cap.get(cv2.CAP_PROP_POS_FRAMES))==f
        ok,image=cap.read();assert ok,f
        small=cv2.resize(image,(1280,720),interpolation=cv2.INTER_AREA)
        source_view=small.copy()
        cv2.putText(source_view,f'Source frame {f} | {f/25:.2f}s',(22,36),cv2.FONT_HERSHEY_SIMPLEX,.8,(245,245,245),2)
        writers['source'].write(source_view)
        if f in [first,last]:
            path=out/'native_checks'/f'source_f{f}.png';assert cv2.imwrite(str(path),image)
            native_checks.append({'source_frame':f,'native_pixels_sha256':hashlib.sha256(image[:,:,::-1].tobytes()).hexdigest(),
                                  'png':path.name,'png_sha256':sha(path)})
        for name,title,*_ in specs:
            h=histories[name]
            if f%5==0:
                h['current']=h['rows'].get(f,[]);h['last_tick']=f
                positions={int(r['track_id']):(float(r['y1'])+float(r['y2']))/2/1440 for r in h['current']}
                for event in h['counter'].update(f/25,positions):h['events'].append({**event,'source_frame':f})
            view=small.copy()
            for x in [.34,.75]:cv2.line(view,(round(x*1280),0),(round(x*1280),719),(0,177,255),2)
            for y in [.4,.6]:cv2.line(view,(round(.34*1280),round(y*720)),(round(.75*1280),round(y*720)),(0,177,255),2)
            for r in h['current']:
                x1,y1,x2,y2=[round(float(r[k])/2) for k in ['x1','y1','x2','y2']]
                cv2.rectangle(view,(x1,y1),(x2,y2),(112,237,149),2)
                cv2.putText(view,f'track {r["track_id"]} {float(r["confidence"]):.2f}',(x1,max(70,y1-8)),cv2.FONT_HERSHEY_SIMPLEX,.65,(112,237,149),2)
            down=sum(r['direction']=='A->B' for r in h['events']);up=sum(r['direction']=='B->A' for r in h['events'])
            cv2.rectangle(view,(0,0),(1280,57),(18,24,28),-1)
            cv2.putText(view,title,(20,27),cv2.FONT_HERSHEY_SIMPLEX,.75,(240,242,240),2)
            cv2.putText(view,f'Source f{f} ({f/25:.2f}s) | last sample {h["last_tick"]} | down {down} up {up}',
                        (20,49),cv2.FONT_HERSHEY_SIMPLEX,.57,(212,225,222),1)
            cv2.rectangle(view,(0,688),(1280,720),(18,24,28),-1)
            cv2.putText(view,'5 Hz actual cached detections; boxes held until next sample. Track IDs are not cow identities.',
                        (20,709),cv2.FONT_HERSHEY_SIMPLEX,.57,(212,225,222),1)
            writers[name].write(view)
            if f in chosen:contacts[(name,f)]=Image.fromarray(cv2.cvtColor(view,cv2.COLOR_BGR2RGB))
        frames+=1
    cap.release()
    for writer in writers.values():writer.release()
    assert frames==p['frames']==1962
    summary=[]
    for condition in conditions:
        h=histories[condition['name']]
        save(out/f'{condition["name"]}_predicted_events.json',h['events'])
        summary.append({**condition,'predicted_A_to_B':sum(r['direction']=='A->B' for r in h['events']),
                        'predicted_B_to_A':sum(r['direction']=='B->A' for r in h['events']),
                        'scoped_tracked_sample_frames':len(h['rows']),
                        'prediction_not_independent_accuracy':True})
    sheet=Image.new('RGB',(1280,8*206),(20,26,30));draw=ImageDraw.Draw(sheet)
    for i,f in enumerate(chosen):
        for j,name in enumerate(['generic','pilot']):sheet.paste(contacts[(name,f)].resize((640,360)).resize((356,200)),(j*640,i*206))
        draw.text((1010,i*206+80),f'source {f}',fill='white')
    sheet.save(out/'comparison_contact.jpg',quality=94)
    media=[]
    for name in writers:
        file=out/f'{name}_transfer.mp4';reader=cv2.VideoCapture(str(file));count=0
        assert reader.isOpened() and reader.get(5)==25
        while reader.read()[0]:count+=1
        reader.release();assert count==1962
        media.append({'name':name,'file':file.name,'frames':count,'fps':25,'duration_s':count/25,'bytes':file.stat().st_size,'sha256':sha(file)})
    save(out/'summary.json',{'status':'USER_SCOPED_ACTUAL_PREDICTION_PREVIEW_COMPLETE','job_id':os.environ['SLURM_JOB_ID'],
          'source_scope':p,'source_scope_sha256':sha(protocol),'frames_rendered_each':frames,'conditions':summary,'media':media,
          'native_checks':native_checks,'scope':'New rendering of preserved actual detections; no new training, no new inference or human labels. No PYNQ timing or field identity claim.'})
    print(json.dumps({'frames':frames,'conditions':[{k:r[k] for k in ['name','predicted_A_to_B','predicted_B_to_A']} for r in summary]}),flush=True)


if __name__=='__main__':main()
