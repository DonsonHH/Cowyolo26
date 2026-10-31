from pathlib import Path
from datetime import datetime,timezone
from PIL import Image,ImageDraw,ImageFont
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/"delivery/results/evaluation"
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
p=load(ROOT/"protocol/run_v1.json");a=load(ROOT/"results/pixel_admission.json")
decisions=load(OUT/"all_decisions.json")
lookup={(r["model"],r["source_index"]):r for r in decisions if r["policy"]==p["primary_policy"]}
folder=ROOT/"results/source_and_primary_panels";folder.mkdir(exist_ok=False)
font=ImageFont.truetype("C:/Windows/Fonts/arial.ttf",19)
small=ImageFont.truetype("C:/Windows/Fonts/arial.ttf",16)
records=[];panels=[]
for page,start in enumerate(range(0,90,9),1):
    canvas=Image.new("RGB",(1260,1770),"#e7edf3");draw=ImageDraw.Draw(canvas)
    draw.text((18,13),f"BECA fixed transfer | page {page}/10 | all source inputs and primary decisions",font=font,fill="#182736")
    for n,index in enumerate(range(start,min(start+9,90))):
        row=p["images"][index];audit=a["rows"][index];path=ROOT/row["local_relative_file"]
        assert sha(path)==audit["sha256"]
        x=10+n%3*420;y=55+n//3*565;draw.rectangle((x,y,x+408,y+551),fill="white")
        draw.text((x+9,y+7),f'#{index:02d} ID {row["publisher_identity"]} {row["purpose"]}',font=small,fill="#182736")
        draw.text((x+9,y+29),f'{row["date"]} {row["native_group"]}',font=small,fill="#182736")
        if row["purpose"]!="gallery":
            labels=[]
            for line,model in enumerate(["old_C","new_C_domain_seed26"]):
                d=lookup[(model,index)];correct=d["is_known"]and d["identity"]==d["predicted_id"]
                outcome="FA"if not d["is_known"]and d["accepted"]else"C"if correct and d["accepted"]else"W"if d["accepted"]else"U"
                color="#ac2020"if outcome in{"FA","W"}else"#1d7744"if outcome=="C"else"#264f80"
                label=("old"if line==0 else"new")+f': {d["predicted_id"]} s={d["score"]:.4f} {outcome}'
                draw.text((x+9,y+51+line*21),label,font=small,fill=color);labels.append(label)
        else:draw.text((x+9,y+51),"Frozen gallery input; no query score",font=small,fill="#264f80")
        with Image.open(path)as source:source.load();image=source.convert("RGB")
        assert hashlib.sha256(image.tobytes()).hexdigest()==audit["RGB_pixel_SHA256"]
        image.thumbnail((384,445),Image.Resampling.LANCZOS)
        canvas.paste(image,(x+12+(384-image.width)//2,y+98+(445-image.height)//2))
        panels.append({"index":index,"page":page,"source_JPEG_sha256":audit["sha256"],"RGB_pixel_SHA256":audit["RGB_pixel_SHA256"],
                       "role":row["purpose"],"image_resized_only_for_display":True,"added_overlay_on_source_pixels":False})
    path=folder/f"page{page:02d}.png";canvas.save(path)
    records.append({"page":page,"file":str(path.resolve()),"sha256":sha(path),"indices":list(range(start,min(start+9,90)))})
out=ROOT/"results/visual_panels_manifest.json";assert not out.exists()
out.write_text(json.dumps({"status":"ALL90_SOURCE_INPUTS_AND_PRIMARY_DECISIONS_RENDERED_POST_EVALUATION",
                           "created_UTC":datetime.now(timezone.utc).isoformat(),"source_count":90,"pages":records,"panels":panels,
                           "all_pages_actually_viewed_yet":False,"new_model_forwards":0,"whole_goal_complete":False},ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"pages":len(records),"source_inputs":len(panels),"folder":str(folder.resolve())}))
