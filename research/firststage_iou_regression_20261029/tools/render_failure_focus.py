"""Readable, source-bound selected-case figure, without changing predictions."""
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    cases=load(ROOT/'results/reference_case.json');out=ROOT/'results/failure_focus';out.mkdir(exist_ok=False)
    font=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',23);small=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',18)
    title=ImageFont.truetype('C:/Windows/Fonts/consola.ttf',27)
    canvas=Image.new('RGB',(1380,1110),'#111827');draw=ImageDraw.Draw(canvas)
    draw.text((18,14),'Official YOLO26n: original ID5 changes cow after the gap',font=title,fill='white')
    draw.text((18,52),'Selected Toros case; native source crop [650,200,1800,850]',font=small,fill='#cbd5e1')
    for x,text in [(18,'Original fused first stage'),(706,'Candidate: first stage pure IoU')]:
        draw.text((x,87),text,font=font,fill='white')
    rows=[];crop=[650,200,1800,850];scale=660/1150
    for row_index,frame in enumerate([153,167]):
        source=ROOT/f'media_delivery/results/media/native/toros_used_reverse_{frame:05d}.jpg';sy=132+row_index*445
        draw.text((18,sy-4),f'Source frame0 {frame} ({frame/30:.3f}s)',font=small,fill='white')
        for column,mode in enumerate(['original_fused','firststage_pure_IoU']):
            case=next(f for r in cases['paired_case_records'] if r['mode']==mode for f in r['frames'] if f['frame0']==frame)
            track=next(t for t in case['track_support'] if t['track_ID']==5);x=18+column*688
            with Image.open(source) as im:panel=im.crop(crop).resize((660,373),Image.Resampling.LANCZOS)
            pd=ImageDraw.Draw(panel)
            def transform(box):return [(box[0]-crop[0])*scale,(box[1]-crop[1])*scale,(box[2]-crop[0])*scale,(box[3]-crop[1])*scale]
            for ID,color in [(14,'#38bdf8'),(7,'#f472b6')]:
                box=transform(case['source_GT_boxes'][str(ID)]);pd.rectangle(box,outline=color,width=3)
                tx=max(2,min(480,box[0]));ty=max(0,box[1]-25)
                pd.text((tx,ty),f'Publisher {ID}',font=small,fill=color,stroke_width=1,stroke_fill='#111827')
            box=transform(track['native_xyxy']);pd.rectangle(box,outline='#86efac',width=4)
            canvas.paste(panel,(x,sy+25))
            text=f'Predicted ID5: best publisher support {track["best_publisher_ID"]}'
            draw.text((x,sy+405),text,font=small,fill='#bbf7d0')
            rows.append({'frame0':frame,'mode':mode,'native_path':str(source.resolve()),'native_sha256':sha(source),
                         'crop_native_xyxy':crop,'predicted_native_xyxy':track['native_xyxy'],
                         'publisher14_native_xyxy':case['source_GT_boxes']['14'],'publisher7_native_xyxy':case['source_GT_boxes']['7'],
                         'best_publisher_ID':track['best_publisher_ID'],'best_IoU':track['best_IoU']})
    draw.text((18,1042),'Blue / pink: publisher cow IDs14 /7. Green: current predicted ID5.',font=small,fill='white')
    draw.text((18,1071),'Exploratory case evidence; no aggregate identity-switch metric is claimed.',font=small,fill='#cbd5e1')
    figure=out/'official_ID5_before_after.png';canvas.save(figure)
    record={'status':'READABLE_FOUR_PANEL_OFFICIAL_ID5_REFERENCE_CASE_RENDERED','figure_path':str(figure.resolve()),'figure_sha256':sha(figure),
            'dimensions':[1380,1110],'panels':rows,'reference_case_sha256':sha(ROOT/'results/reference_case.json'),
            'new_predictions_or_reference_changes':False,'actual_visual_review_required':True}
    path=ROOT/'results/failure_focus_record.json';assert not path.exists();path.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k!='panels'}))
if __name__=='__main__':main()
