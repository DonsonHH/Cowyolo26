"""Read-only native evidence for a fragmented path and a confirmation handoff."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import csv,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(ROOT/'input'))
from zone_counter import ZoneCounter
from confirmation_counter import ConfirmationHandoffCounter
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):
    assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True)
    p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def state(counter,tid):
    item=counter.states.get(tid);return vars(item).copy() if item else None
def trace(model,targets,scope):
    folder=ROOT/'delivery/results'/model;obs=load(folder/'observations.json')
    base=ZoneCounter();candidate=ConfirmationHandoffCounter();rows=[]
    for row in obs:
        t=row['time_s'];positions={int(k):v for k,v in row['confirmed_positions'].items()}
        tentative={int(k):v for k,v in row['tentative_positions'].items()}
        b=base.update(t,positions);c=candidate.update(t,positions,tentative,row['confirmed_IDs'])
        if not scope[0]<=row['frame0']<=scope[1]:continue
        for tid in targets:
            counter=candidate.counters.get(tid)
            rows.append({'model':model,'frame0':row['frame0'],'track_ID':tid,
                         'confirmed_y':positions.get(tid),'tentative_y':tentative.get(tid),
                         'confirmed_only_state':state(base,tid),'handoff_state':state(counter,tid) if counter else None,
                         'admitted':[a for a in candidate.last_acceptances if a['track_id']==tid],
                         'baseline_events':[e for e in b if e['track_id']==tid],
                         'handoff_events':[e for e in c if e['track_id']==tid]})
    return rows
def main():
    out=ROOT/'results/case_diagnosis';out.mkdir(exist_ok=False)
    first=trace('seed26',[19,23],[2605,2680]);second=trace('seed27',[18],[2685,2720])
    lookup={(r['track_ID'],r['frame0']):r for r in first}
    assert lookup[19,2645]['handoff_state']['origin']=='A'
    assert [lookup[19,f]['confirmed_y'] for f in [2650,2655,2660]]==[None,None,None]
    assert lookup[23,2665]['tentative_y']>.6 and lookup[23,2670]['confirmed_y']>.6 and lookup[23,2675]['confirmed_y']>.6
    assert lookup[23,2675]['handoff_state']['origin']=='B' and not any(r['handoff_events'] for r in first)
    h={r['frame0']:r for r in second}
    assert h[2685]['tentative_y']<.4 and h[2690]['confirmed_y']<.4 and h[2695]['confirmed_y']<.4
    assert h[2695]['confirmed_only_state']['origin'] is None and h[2695]['handoff_state']['origin']=='A'
    assert h[2720]['baseline_events']==[] and len(h[2720]['handoff_events'])==1
    assert h[2720]['handoff_events'][0]['direction']=='A->B'
    frames=[2640,2645,2650,2655,2660,2665,2670,2675]
    folder=ROOT/'delivery/results/seed26'
    def read(name):
        with (folder/name).open(encoding='utf-8',newline='') as f:return list(csv.DictReader(f))
    raw=read('raw_detector_boxes.csv');post=read('post_tracker_boxes.csv')
    try:font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',25)
    except OSError:font=ImageFont.load_default()
    panels=[]
    for frame in frames:
        source=PROJECT/f'overhead_positive_reference_20261028/focused_delivery/results/focused/group_passage/ROI_{frame:05d}.jpg'
        with Image.open(source) as im:assert im.size==(1050,1440);picture=im.convert('RGB')
        draw=ImageDraw.Draw(picture)
        for gate in [576,864]:draw.line((0,gate,1049,gate),fill='#fbbf24',width=4)
        selected={}
        for rows,key,color,label in [(raw,'frame','#f87171','raw'),(post,'frame0','#86efac','ID')]:
            matching=[r for r in rows if int(r[key])==frame and .34<(float(r['x1'])+float(r['x2']))/5120<.75]
            selected[label]=matching
            for r in matching:
                x1,y1,x2,y2=[float(r[k]) for k in ['x1','y1','x2','y2']];x1-=870;x2-=870
                draw.rectangle((x1,y1,x2,y2),outline=color,width=4)
                name=f"{label} {r.get('track_id','')} {float(r['confidence']):.2f}"
                draw.text((max(0,x1),max(0,y1-28)),name,font=font,fill=color,stroke_width=1,stroke_fill='#111827')
        target=out/f'seed26_native_{frame:05d}.png';picture.save(target)
        panels.append({'frame0':frame,'source_path':str(source.resolve()),'source_sha256':sha(source),
                       'annotated_path':str(target.resolve()),'sha256':sha(target),
                       'raw_ROI_boxes':selected['raw'],'confirmed_ROI_boxes':selected['ID'],
                       'native_crop_xyxy':[870,0,1920,1440],'native_dimensions':[1050,1440]})
    sheets=[]
    for index in range(2):
        canvas=Image.new('RGB',(1086,1570),'#111827');draw=ImageDraw.Draw(canvas)
        draw.text((12,10),'seed26: native raw(red), confirmed(green)',font=font,fill='white')
        for j,panel in enumerate(panels[index*4:index*4+4]):
            x=12+(j%2)*537;y=50+(j//2)*754
            draw.text((x,y),f"frame0 {panel['frame0']}",font=font,fill='white')
            with Image.open(panel['annotated_path']) as im:canvas.paste(im.resize((525,720),Image.Resampling.LANCZOS),(x,y+30))
        target=out/f'seed26_gap_sheet_{index+1}.jpg';canvas.save(target,quality=94)
        sheets.append({'path':str(target.resolve()),'sha256':sha(target),'source_frames':[p['frame0'] for p in panels[index*4:index*4+4]]})
    record={'status':'READ_ONLY_TRACK_FRAGMENT_AND_HANDOFF_CAUSAL_STATES_RECONSTRUCTED',
            'seed26_fragment_IDs':[19,23],'seed26_target_origin_A_until_frame0':2645,
            'seed26_three_missing_sample_frames':[2650,2655,2660],
            'seed26_new_ID_B_only_confirmed_frames':[2670,2675],
            'seed26_visual_same_cow_link_authority':'assistant_case_hypothesis_requires_independent_review',
            'seed27_counter_only_event_added':{'frame0':2720,'track_ID':18,'direction':'A->B'},
            'seed27_origin_evidence_frames_handoff':[2685,2690,2695],
            'seed27_origin_evidence_frames_confirmed_only':[2690,2695],
            'seed26_states':first,'seed27_states':second,'native_panels':panels,'case_sheets':sheets,
            'models_or_outputs_changed':False,'reference_changed':False,'formal_scores_computed':False,
            'new_training_updates':0,'FPGA_execution_verified':False,'whole_goal_complete':False}
    save(ROOT/'results/case_diagnosis.json',record)
    print(json.dumps({k:v for k,v in record.items() if k not in ['seed26_states','seed27_states','native_panels','case_sheets']}))
if __name__=='__main__':main()
