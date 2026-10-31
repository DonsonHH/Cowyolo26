"""Build source-bound native sequence rulers; no inference or automatic labels."""
from pathlib import Path
import hashlib,json,math
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
UP=PROJECT/'overhead_positive_reference_20261028'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def font(n):return ImageFont.truetype('C:/Windows/Fonts/arial.ttf',n)
def main():
    src=UP/'reference/assistant_event_draft_v1.json';assert sha(src)=='35a6e0d5b4454cc2a6e6057c750f84cd6cf5d02f5d3fc73c4c1683c80b149bb7'
    draft=json.loads(src.read_text(encoding='utf-8'));focused=json.loads((UP/'focused_delivery/results/focused/summary.json').read_text(encoding='utf-8'))
    bound={(w['name'],r['frame0']):r for w in focused['windows'] for r in w['samples']}
    out=ROOT/'results/native_timing';out.mkdir(parents=True,exist_ok=True);assert not any(out.iterdir())
    x_windows={'R01':[480,1050],'R02':[200,850],'R03':[600,1050],'R04':[150,850],
               'R05':[580,1050],'R06':[580,1050],'R07':[580,1050],'R08':[580,1050],
               'R09':[580,1050],'R10':[200,850],'R11':[200,850],'R12':[200,850]}
    records=[]
    for r in draft['candidates']:
        ID=r['reference_ID'];a,b=r['destination_transition_review_frame0_interval'];frames=list(range(a-25,b+11,5));panels=[];rows=[]
        x1,x2=x_windows[ID];top,bottom=250,1400
        for frame in frames:
            path=UP/'focused_delivery'/bound[(r['window'],frame)]['file'];assert sha(path)==bound[(r['window'],frame)]['sha256']
            with Image.open(path) as im:
                im.load();assert im.size==(1050,1440);view=im.convert('RGB').crop((x1,top,x2,bottom)).resize((320,500))
            draw=ImageDraw.Draw(view)
            for y in [400,500,600,700,800,864,900,1000,1100,1200,1300]:
                py=(y-top)*500/(bottom-top);color='#1de8dc' if y==864 else '#cbd5e1'
                draw.line([(0,py),(319,py)],fill=color,width=2 if y==864 else 1)
                draw.rectangle([0,py,39,py+15],fill='black');draw.text((2,py),str(y),font=font(13),fill=color)
            panel=Image.new('RGB',(340,550),'#111827');d=ImageDraw.Draw(panel)
            d.text((6,4),f'{ID} | frame0 {frame}',font=font(21),fill='white');d.text((6,28),f'{frame/25:.2f}s | native y ruler',font=font(18),fill='#fbbf24');panel.paste(view,(10,50));panels.append(panel)
            rows.append({'frame0':frame,'time_s_nominal':frame/25,'source_path':str(path),'source_sha256':sha(path),'native_crop_x_range':x_windows[ID],
                         'native_crop_y_range':[top,bottom],'native_pixel_coordinate_convention':'Coordinates refer to original image; source crop top y is0. Image ruler is a display transform.'})
        pages=[]
        for page,start in enumerate(range(0,len(panels),12)):
            chosen=panels[start:start+12];sheet=Image.new('RGB',(1360,1710),'#111827');d=ImageDraw.Draw(sheet)
            d.text((10,6),f'{ID}: original torso timing review; cyan y=864; manual ranges pending',font=font(24),fill='white')
            for i,panel in enumerate(chosen):sheet.paste(panel,((i%4)*340,60+(i//4)*550))
            dest=out/f'{ID}_page_{page+1:02d}.jpg';sheet.save(dest,quality=96)
            pages.append({'path':str(dest),'sha256':sha(dest),'frame0_list':frames[start:start+12]})
        records.append({'reference_ID':ID,'window':r['window'],'previous_review_target':[a,b],'expanded_source_frames0':frames,
                        'source_rows':rows,'pages':pages,'visual_review':'PENDING'})
    result={'status':'TWELVE_NATIVE_PIXEL_RULER_SEQUENCES_PREPARED','original_draft_sha256':sha(src),'source_sha256':draft['source_sha256'],
            'new_model_predictions':0,'sequences':records,'total_panels':sum(len(r['source_rows']) for r in records),
            'manual_intervals_not_yet_assigned':True,'eligible_for_scoring':False,'whole_goal_complete':False}
    (out/'manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'sequences':len(records),'panels':result['total_panels'],'pages':sum(len(r['pages']) for r in records)}),flush=True)
if __name__=='__main__':main()
