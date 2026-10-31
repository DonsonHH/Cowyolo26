from pathlib import Path
from PIL import Image,ImageOps,ImageDraw,ImageFont
import hashlib,json,numpy as np
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    rows=load(ROOT/'refined_delivery/results/geometry_refined/top_results.json');art=load(ROOT/'refined_delivery/results/geometry_refined/artifacts.json')
    out=ROOT/'results/source_review';out.mkdir(exist_ok=False)
    title=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',25)
    font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',18);small=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',16)
    def fit(path,size):
        with Image.open(path) as im:picture=ImageOps.contain(im.convert('RGB'),size,method=Image.Resampling.LANCZOS)
        canvas=Image.new('RGB',size,'#1f2937');canvas.paste(picture,((size[0]-picture.width)//2,(size[1]-picture.height)//2));return canvas
    pages=[]
    for page in range(6):
        sheet=Image.new('RGB',(1440,1780),'#111827');draw=ImageDraw.Draw(sheet)
        ID=rows[page*5]['gallery']['published_anonymous_ID']
        draw.text((15,12),f'All frozen gallery crops: published ID{ID}; geometric source audit ({page+1}/6)',font=title,fill='white')
        draw.text((15,49),'Published crop | Best native-source candidate + projected outline | Source rewarp',font=font,fill='#cbd5e1')
        cells=[]
        for i,(row,item) in enumerate(zip(rows[page*5:page*5+5],art[page*5:page*5+5])):
            y=90+i*329;best=row['top'][0];gallery=Path(row['gallery']['local_path']);native=ROOT/'refined_delivery'/item['native_source']
            geometry=best['geometry_pass'];draw.text((15,y),f"Template{row['template_index']:02d}: {row['gallery']['filename']} | nativeframe {best['source_frame0']} | {'GEOMETRY CANDIDATE' if geometry else 'REJECTED GEOMETRY'}",font=font,fill='#bbf7d0' if geometry else '#fca5a5')
            sheet.paste(fit(gallery,(520,245)),(15,y+30))
            with Image.open(native) as im:
                picture=im.convert('RGB');d=ImageDraw.Draw(picture)
                if 'mapped_native_corners' in best:
                    d.line([tuple(p) for p in best['mapped_native_corners']]+[tuple(best['mapped_native_corners'][0])],fill='#86efac' if geometry else '#f87171',width=7)
                picture=ImageOps.contain(picture.crop((870,0,1920,1440)),(240,275),method=Image.Resampling.LANCZOS)
            source_panel=Image.new('RGB',(240,275),'#1f2937');source_panel.paste(picture,((240-picture.width)//2,(275-picture.height)//2));sheet.paste(source_panel,(552,y+30))
            warp=None
            if 'rewarp_file' in item:
                warp=ROOT/'refined_delivery'/item['rewarp_file'];sheet.paste(fit(warp,(620,245)),(808,y+30))
            else:draw.text((830,y+115),'No fitted transform / no rewarp',font=font,fill='#fca5a5')
            ncc=f'{best["NCC"]:.6f}' if best['NCC'] is not None else 'not scored'
            text=f"Inliers {best['inliers']}/{best['ratio_matches']}; NCC {ncc}; hull {best['template_inlier_hull_fraction']:.3f}"
            draw.text((15,y+285),text,font=small,fill='white')
            cells.append({'template_index':row['template_index'],'anonymous_ID':ID,'gallery_path':str(gallery.resolve()),'gallery_sha256':sha(gallery),
                'source_native_path':str(native.resolve()),'source_native_sha256':sha(native),'rewarp_path':str(warp.resolve()) if warp else None,
                'rewarp_sha256':sha(warp) if warp else None,'source_frame0':best['source_frame0'],'geometry_pass':geometry,'NCC':best['NCC']})
        draw.text((15,1750),'Source-crop candidates only; not independent cow-identity ground truth. Rejected matches are shown, not adopted.',font=small,fill='#cbd5e1')
        target=out/f'gallery_ID{ID}_all5.jpg';sheet.save(target,quality=95)
        pages.append({'path':str(target.resolve()),'sha256':sha(target),'template_rows':cells,'panels':15})
    record={'status':'ALL30_GALLERY_CROPS_SOURCE_CANDIDATES_AND_REJECTED_MATCHES_RENDERED_IN6PAGES',
        'pages':pages,'template_rows':30,'review_panel_slots':90,'fitted_warp_panels':sum(r['rewarp_path'] is not None for p in pages for r in p['template_rows']),
        'empty_unfitted_panel_slots':sum(r['rewarp_path'] is None for p in pages for r in p['template_rows']),
        'actual_visual_review_required':True,'identity_truth_promoted':False}
    path=ROOT/'results/source_review_record.json';assert not path.exists();path.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k!='pages'}))
if __name__=='__main__':main()
