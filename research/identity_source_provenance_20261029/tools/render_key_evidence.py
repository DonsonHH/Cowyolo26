from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    rows=load(ROOT/'refined_delivery/results/geometry_refined/top_results.json');art=load(ROOT/'refined_delivery/results/geometry_refined/artifacts.json')
    verification=load(ROOT/'results/photometry_and_event_link_verification.json');end=load(ROOT/'endpoint_delivery/results/endpoint_check/summary.json')
    out=ROOT/'results/source_review';font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',21);title=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',27)
    small=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',18)
    def fitted(path,size):
        with Image.open(path) as im:picture=ImageOps.contain(im.convert('RGB'),size,method=Image.Resampling.LANCZOS)
        panel=Image.new('RGB',size,'#1f2937');panel.paste(picture,((size[0]-picture.width)//2,(size[1]-picture.height)//2));return panel
    sheet=Image.new('RGB',(1440,1235),'#111827');d=ImageDraw.Draw(sheet)
    d.text((15,13),'Published ID009 gallery and original source: same-passage overlap evidence',font=title,fill='white')
    d.text((15,53),'Published Aug14 camera1 crop | Native frame + geometric projection | Original-source rewarp',font=small,fill='#cbd5e1')
    panels=[]
    for j,i in enumerate([1,2,3]):
        row,item=rows[i],art[i];best=row['top'][0];y=95+j*355;gallery=Path(row['gallery']['local_path'])
        native=ROOT/'refined_delivery'/item['native_source'];warp=ROOT/'refined_delivery'/item['rewarp_file']
        d.text((15,y),f"{row['gallery']['filename']}  ->  source frame0 {best['source_frame0']}  |  NCC {best['NCC']:.6f}",font=font,fill='#bbf7d0')
        sheet.paste(fitted(gallery,(520,255)),(15,y+36));sheet.paste(fitted(warp,(620,255)),(808,y+36))
        with Image.open(native) as im:
            picture=im.convert('RGB');draw=ImageDraw.Draw(picture)
            draw.line([tuple(p) for p in best['mapped_native_corners']]+[tuple(best['mapped_native_corners'][0])],fill='#86efac',width=8)
            picture=ImageOps.contain(picture.crop((870,0,1920,1440)),(240,290),method=Image.Resampling.LANCZOS)
        panel=Image.new('RGB',(240,290),'#1f2937');panel.paste(picture,((240-picture.width)//2,(290-picture.height)//2));sheet.paste(panel,(552,y+36))
        d.text((15,y+330),f"Inliers {best['inliers']}/{best['ratio_matches']}; mean channel error {best['mean_absolute_BGR_error']:.3f}/255; source track102",font=small,fill='white')
        panels.append({'template_index':i,'gallery_path':str(gallery.resolve()),'gallery_sha256':sha(gallery),
            'source_path':str(native.resolve()),'source_sha256':sha(native),'warp_path':str(warp.resolve()),'warp_sha256':sha(warp),
            'source_frame0':best['source_frame0'],'NCC':best['NCC']})
    d.text((15,1172),'E010 query uses frame9745 from this passage. This gallery/query pair cannot support independent identity accuracy.',font=small,fill='#fca5a5')
    d.text((15,1205),'Geometric/pixel evidence, without the Re-ID encoder. No official ear-tag or independent human ID verification.',font=small,fill='#cbd5e1')
    target=out/'ID009_same_passage_source_evidence_v2.jpg';assert not target.exists();sheet.save(target,quality=95)
    core={'path':str(target.resolve()),'sha256':sha(target),'panels':9,'source_records':panels}
    sheet=Image.new('RGB',(1440,865),'#111827');d=ImageDraw.Draw(sheet)
    d.text((15,12),'Post-search endpoint check: preserve failures and boundary rejection',font=title,fill='white')
    endpoint_panels=[]
    for j,r in enumerate(end['endpoint_results']):
        y=75+j*345;i=r['template_index'];gallery=Path(r['gallery']['local_path']);warp=ROOT/'endpoint_delivery'/r['rewarp_file']
        native=ROOT/'endpoint_delivery'/r['native_source_file'];photo=r['diagnostic_photometric']
        d.text((15,y),f"{r['gallery']['filename']} at predictedframe {r['predicted_source_frame0']} | geometry {'PASS' if r['match']['geometry_pass'] else 'REJECT'} | diagnostic NCC {photo['NCC']:.6f}",font=font,fill='#fbbf24')
        sheet.paste(fitted(gallery,(620,245)),(15,y+34));sheet.paste(fitted(warp,(620,245)),(740,y+34))
        reason='Weak endpoint: pixels do not establish exact source frame.' if i==0 else 'Pixel match is strong; only3/4 projected corners inimage. Original geometry rejection is retained.'
        d.text((15,y+293),reason,font=small,fill='#fca5a5')
        endpoint_panels.append({'template_index':i,'gallery_path':str(gallery.resolve()),'gallery_sha256':sha(gallery),
            'warp_path':str(warp.resolve()),'warp_sha256':sha(warp),'native_path':str(native.resolve()),'native_sha256':sha(native)})
    d.text((15,805),'The sequence rule was hypothesized after three high-correlation matches; not a universal filename-to-frame rule.',font=small,fill='#cbd5e1')
    d.text((15,835),'No image is accepted as human identity truth by this endpoint experiment.',font=small,fill='#cbd5e1')
    target=out/'sequence_endpoints_failures_preserved_v2.jpg';assert not target.exists();sheet.save(target,quality=95)
    endpoints={'path':str(target.resolve()),'sha256':sha(target),'panels':4,'source_records':endpoint_panels}
    record={'status':'READABLE_SAME_PASSAGE_SOURCE_AND_ENDPOINT_FAILURE_FIGURES_CREATED','core':core,'endpoints':endpoints,
        'actual_visual_review_required':True,'data_split_admission_decision':'CurrentE010/Aug14ID009gallery excluded from independent identity evaluation.',
        'source_identity_truth_promoted':False,'new_identity_model_forwards':0,'whole_goal_complete':False}
    path=ROOT/'results/key_evidence_figures_v2.json';assert not path.exists();path.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k not in ['core','endpoints']}))
if __name__=='__main__':main()
