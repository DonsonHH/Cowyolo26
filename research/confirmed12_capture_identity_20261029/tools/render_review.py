from pathlib import Path
from PIL import Image,ImageDraw,ImageFont,ImageOps
import hashlib,json,numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    replay=ROOT/'delivery/results/replay';events=load(replay/'events.json');gallery=load(replay/'gallery_vectors.json')
    out=ROOT/'results/review_images';out.mkdir(exist_ok=False)
    font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',19)
    small=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',16)
    title=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',24)
    def fitted(path,size):
        with Image.open(path) as im:
            image=ImageOps.contain(im.convert('RGB'),size,method=Image.Resampling.LANCZOS)
        panel=Image.new('RGB',size,'#1f2937');panel.paste(image,((size[0]-image.width)//2,(size[1]-image.height)//2));return panel
    short={'A_official_frozen':'A','B_letterbox_frozen':'B','C_letterbox_trained_seed26':'C26','C_letterbox_trained_seed27':'C27','C_letterbox_trained_seed28':'C28'}
    pages=[]
    for page in range(4):
        sheet=Image.new('RGB',(1320,980),'#111827');draw=ImageDraw.Draw(sheet)
        draw.text((14,12),f'Accepted count version: native capture and real query results ({page+1}/4)',font=title,fill='white')
        draw.text((14,47),'Native photo + box | Oriented crop before model-specific preprocessing | Frozen scores',font=small,fill='#cbd5e1')
        records=[]
        for j,e in enumerate(events[page*3:page*3+3]):
            y=84+j*290;s=e['selected_snapshot'];native=replay/s['native_path'];crop=replay/s['oriented_path']
            draw.text((14,y),f'{e["event_id"]} | passage {e["frame0"]} | selected source {s["frame0"]}',font=font,fill='white')
            with Image.open(native) as im:
                image=im.convert('RGB');d=ImageDraw.Draw(image);d.rectangle(s['box'],outline='#86efac',width=8)
                image=image.resize((420,236),Image.Resampling.LANCZOS)
            sheet.paste(image,(14,y+30));sheet.paste(fitted(crop,(420,236)),(448,y+30))
            any_pass=e['status']=='CANDIDATE_THRESHOLD_PASSED_UNVERIFIED'
            draw.text((888,y+30),'UNVERIFIED CANDIDATE' if any_pass else 'ALL FIVE REJECT',font=font,fill='#fbbf24' if any_pass else '#cbd5e1')
            for i,c in enumerate(e['worker_result']['conditions']):
                symbol='>=' if c['passes_frozen_threshold'] else '< '
                text=f"{short[c['condition']]} ID{c['candidate_anonymous_id']}: {c['cosine_similarity']:.4f} {symbol}{c['frozen_threshold']:.4f}"
                draw.text((888,y+65+i*28),text,font=small,fill='#fbbf24' if c['passes_frozen_threshold'] else 'white')
            draw.text((888,y+220),'Source-cow identity unverified',font=small,fill='#fca5a5')
            records.append({'event_id':e['event_id'],'native_path':str(native.resolve()),'native_sha256':sha(native),
                            'oriented_path':str(crop.resolve()),'oriented_sha256':sha(crop),'event_source_frame0':e['frame0'],
                            'selected_source_frame0':s['frame0'],'status':e['status']})
        target=out/f'events_page_{page+1}.jpg';sheet.save(target,quality=95)
        pages.append({'path':str(target.resolve()),'sha256':sha(target),'event_rows':records,'image_panels':6})
    rows=[]
    for event in events:
        for result in event['worker_result']['conditions']:
            if not result['passes_frozen_threshold']:continue
            selected=[(i,result['gallery_image_cosines'][i]) for i,r in enumerate(gallery['entries']) if r['identity']==result['candidate_anonymous_id']]
            index,value=max(selected,key=lambda r:r[1]);reference=gallery['entries'][index]
            image=PROJECT/'identity_training_20261026/delivery'/reference['relative_path'];assert sha(image)==reference['sha256']
            rows.append({'event':event,'result':result,'gallery_index':index,'gallery_image':image,'reference':reference})
    assert len(rows)==3
    sheet=Image.new('RGB',(1320,1090),'#111827');draw=ImageDraw.Draw(sheet)
    draw.text((14,12),'Threshold crossings: query crop and nearest registered image',font=title,fill='white')
    draw.text((14,47),'Public anonymous IDs only. These selected comparisons are not verified source-cow identities.',font=small,fill='#fca5a5')
    matches=[]
    for j,item in enumerate(rows):
        e,c=item['event'],item['result'];s=e['selected_snapshot'];query=replay/s['oriented_path'];y=88+j*315
        label=f"{e['event_id']} | {short[c['condition']]} | ID{c['candidate_anonymous_id']} | score {c['cosine_similarity']:.6f} / threshold {c['frozen_threshold']:.6f}"
        draw.text((14,y),label,font=font,fill='#fbbf24')
        draw.text((14,y+30),'Actual oriented query crop',font=small,fill='white')
        draw.text((674,y+30),'Nearest image of the candidate ID',font=small,fill='white')
        sheet.paste(fitted(query,(630,240)),(14,y+56));sheet.paste(fitted(item['gallery_image'],(630,240)),(674,y+56))
        matches.append({'event_id':e['event_id'],'condition':c['condition'],'candidate_anonymous_id':c['candidate_anonymous_id'],
            'similarity':c['cosine_similarity'],'threshold':c['frozen_threshold'],
            'query_path':str(query.resolve()),'query_sha256':sha(query),
            'gallery_index':item['gallery_index'],'gallery_path':str(item['gallery_image'].resolve()),'gallery_sha256':sha(item['gallery_image']),
            'gallery_metadata':item['reference'],'verified_source_identity':False})
    draw.text((14,1050),'A threshold crossing is a candidate to review; no official ear-tag or health record is inferred.',font=small,fill='#cbd5e1')
    target=out/'passing_candidates_and_gallery.jpg';sheet.save(target,quality=95)
    summary=load(replay/'summary.json');times=[e['worker_result']['finished_wall_ns']-e['worker_result']['started_wall_ns'] for e in events]
    wait=[e['worker_result']['started_wall_ns']-e['enqueue_wall_ns'] for e in events]
    stopped=next(m for m in load(replay/'worker_messages.json') if m['kind']=='stopped')
    runtime={'clock':'server monotonic_ns; cached-observation functional replay, not PYNQ timing',
             'service_5_conditions_ms':{'minimum':min(times)/1e6,'median':float(np.median(times))/1e6,'p95':float(np.percentile(times,95))/1e6,'maximum':max(times)/1e6},
             'wait_ms':{'minimum':min(wait)/1e6,'median':float(np.median(wait))/1e6,'p95':float(np.percentile(wait,95))/1e6,'maximum':max(wait)/1e6},
             'parent_peak_RSS_KiB':summary['parent_peak_RSS_KiB'],'worker_peak_RSS_KiB':stopped['maximum_rss_kib'],
             'retained_snapshot_bytes':summary['snapshot_bank_peak_bytes'],'retained_snapshot_budget_excludes_models_decoder_and_object_overhead':True,
             'source_decode_and_capture_host_elapsed_s':(summary['frontend_EOF_wall_ns']-summary['frontend_start_wall_ns'])/1e9}
    record={'status':'12_EVENT_CAPTURE_CONTACTS_AND_THREE_THRESHOLD_CANDIDATE_COMPARISONS_RENDERED',
            'pages':pages,'candidate_comparison_path':str(target.resolve()),'candidate_comparison_sha256':sha(target),
            'candidate_comparisons':matches,'image_panels':30,'sheet_count':5,'runtime_observations':runtime,
            'actual_visual_review_required':True,'source_identity_accuracy':None,'whole_goal_complete':False}
    dest=ROOT/'results/review_images_record.json';assert not dest.exists();dest.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k not in ['pages','candidate_comparisons']}))
if __name__=='__main__':main()
