"""Independently verify conditional timing with string-window search, then render one case."""
from pathlib import Path
from itertools import product
import hashlib,json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def font(n):return ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
def main():
    ref_path=ROOT/'reference/assistant_event_timing_v2.json';data=load(ref_path);manual_path=ROOT/'input/manual_center_ranges_v1.json';manual=load(manual_path)
    assert data['manual_input_sha256']==sha(manual_path)
    scenarios=0;samples=0;outside=[]
    for event,row in zip(data['events'],manual['rows']):
        assert event['reference_ID']==row['reference_ID'];states=[]
        for obs,(frame,lo,hi) in zip(event['observations'],row['samples']):
            assert obs['frame0']==frame and obs['native_centre_y_working_range']==[lo,hi]
            label='B' if min(lo,hi)>864 else 'N' if max(lo,hi)<=864 else 'U';assert label==obs['state'];states.append(label)
            assert sha(Path(obs['source_image_path']))==obs['source_sha256'];samples+=1
        unknown=[i for i,c in enumerate(states) if c=='U'];actual=set()
        for bits in product('NB',repeat=len(unknown)):
            resolved=states.copy()
            for i,b in zip(unknown,bits):resolved[i]=b
            position=''.join(resolved).find('BBB');assert position>=0
            frame=row['samples'][position+2][0];actual.add(frame);scenarios+=1
            original=next(r for r in event['scenarios'] if r['uncertain_samples_as_B']==[b=='B' for b in bits])
            assert original['resolved_states']==resolved and original['first_three_B_completion_frame0']==frame
        assert sorted(actual)==event['possible_completion_frames0_under_manual_ranges']
        assert event['completion_frame0_hull']==[min(actual),max(actual)]
        assert abs(event['completion_hull_width_s']-(max(actual)-min(actual))/25)<1e-12
        if not event['all_grid_candidates_inside_previous_review_target']:outside.append(event['reference_ID'])
        assert event['independently_accepted'] is False and event['exact_human_accepted_event_frame0'] is None
    assert samples==68 and scenarios==40 and outside==['R03']
    contacts=load(ROOT/'results/native_timing/manifest.json');decoded=[]
    for seq in contacts['sequences']:
        for r in seq['source_rows']:assert sha(Path(r['source_path']))==r['source_sha256']
        for page in seq['pages']:
            p=Path(page['path']);assert sha(p)==page['sha256']
            with Image.open(p) as im:im.load();assert im.size==(1360,1710)
            decoded.append({'path':str(p),'sha256':sha(p)})
    assert len(decoded)==23 and sum(len(r['source_rows']) for r in contacts['sequences'])==172
    selected=next(e for e in data['events'] if e['reference_ID']=='R03');sequence=next(s for s in contacts['sequences'] if s['reference_ID']=='R03')
    x1,x2=600,1050;top,bottom=250,1400;panel_w,panel_h=460,670
    sheet=Image.new('RGB',(1380,1500),'#111827');d=ImageDraw.Draw(sheet)
    d.text((14,8),'R03: uncertainty in a manual torso-centre reading propagates into completion time',font=font(24),fill='white')
    d.text((14,42),'Cyan: y=864 | Pink bracket: assistant working range, NOT measured truth or model prediction',font=font(22),fill='#fbbf24')
    for i,obs in enumerate(selected['observations']):
        with Image.open(obs['source_image_path']) as im:
            view=im.convert('RGB').crop((x1,top,x2,bottom)).resize((430,570))
        draw=ImageDraw.Draw(view)
        for y in [400,600,800,864,1000,1200]:
            py=(y-top)*570/(bottom-top);draw.line([(0,py),(429,py)],fill='#22dacd' if y==864 else '#cbd5e1',width=2 if y==864 else 1)
            draw.text((3,py),str(y),font=font(16),fill='white',stroke_width=1,stroke_fill='black')
        lo,hi=obs['native_centre_y_working_range'];ya=(lo-top)*570/(bottom-top);yb=(hi-top)*570/(bottom-top)
        draw.line([(260,ya),(260,yb)],fill='#ff42b6',width=6);draw.line([(244,ya),(276,ya)],fill='#ff42b6',width=4);draw.line([(244,yb),(276,yb)],fill='#ff42b6',width=4)
        x=(i%3)*panel_w;y=95+(i//3)*panel_h
        d.text((x+10,y),f"Source frame0 {obs['frame0']} | {obs['state']}",font=font(24),fill='white')
        d.text((x+10,y+31),f'Working centre y: [{lo}, {hi}]',font=font(22),fill='#ff85cd');sheet.paste(view,(x+15,y+70))
    d.text((14,1435),'N = outside destination, U = boundary uncertain, B = destination. First BBB may end at2715,2720,2725.',font=font(22),fill='#fbbf24')
    dest=ROOT/'results/R03_manual_interval_timing.png';assert not dest.exists();sheet.save(dest)
    result={'status':'CONDITIONAL_TIMING_RECOMPUTED_BY_INDEPENDENT_STRING_WINDOW_SEARCH','timing_draft_sha256':sha(ref_path),
            'manual_input_sha256':sha(manual_path),'candidate_events':12,'sample_intervals_checked':samples,'binary_scenarios_checked':scenarios,
            'old_review_target_exceeded_by':['R03'],'timing_candidate_sets_total':sum(len(e['possible_completion_frames0_under_manual_ranges']) for e in data['events']),
            'widths_s':{e['reference_ID']:e['completion_hull_width_s'] for e in data['events']},'native_ruler_pages_fully_decoded':23,
            'source_ruler_panels':172,'plot_path':str(dest),'plot_sha256':sha(dest),'pages':decoded,
            'visual_acceptance_pending':True,'assistant_ranges_are_not_calibrated_measurements':True,
            'independent_human_acceptance_received':False,'eligible_for_final_scoring':False,'new_model_predictions':0,'whole_goal_complete':False}
    out=ROOT/'results/independent_verification.json';assert not out.exists();out.write_bytes((json.dumps(result,indent=2)+'\n').encode());print(json.dumps({k:v for k,v in result.items() if k!='pages'}),flush=True)
if __name__=='__main__':main()
