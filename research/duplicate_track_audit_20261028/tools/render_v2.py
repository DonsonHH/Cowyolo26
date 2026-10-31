from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,os,socket,tarfile
import cv2,numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/duplicate_track_audit_20261028')
load=lambda p:json.loads(Path(p).read_text())
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):Path(p).write_text(json.dumps(v,indent=2))
def annotate(image,r,refs,font):
    im=Image.fromarray(cv2.cvtColor(image,cv2.COLOR_BGR2RGB));d=ImageDraw.Draw(im)
    wanted={g['ID'] for g in [r['GT_a'],r['GT_b']] if g['ID'] is not None}
    for row in refs:
        if int(row[1]) not in wanted:continue
        x,y,w,h=row[2:6];box=(max(0,x),max(0,y),min(1919,x+w),min(1079,y+h))
        if box[2]>box[0] and box[3]>box[1]:
            d.rectangle(box,outline='#e8ae20',width=5);d.text((box[0],max(0,box[1]-26)),f'GT {int(row[1])}',font=font,fill='#e8ae20',stroke_width=1,stroke_fill='black')
    for tid,key,color in [(r['track_IDs'][0],'xyxy_a','#ee527d'),(r['track_IDs'][1],'xyxy_b','#00b9ca')]:
        b=r[key];d.rectangle(b,outline=color,width=4);d.text((b[0],b[1]+12+(32 if key=='xyxy_b' else 0)),f'ID {tid}',font=font,fill=color,stroke_width=1,stroke_fill='black')
    return im
def crop_context(im,r):
    b=np.array([r['xyxy_a'],r['xyxy_b']]);x0,y0=b[:,:2].min(0);x1,y1=b[:,2:].max(0)
    margin=max(80.,.35*max(x1-x0,y1-y0));x0=max(0,int(x0-margin));y0=max(0,int(y0-margin));x1=min(1920,int(x1+margin));y1=min(1080,int(y1+margin))
    image=im.crop((x0,y0,x1,y1));image.thumbnail((620,335))
    panel=Image.new('RGB',(640,360),'#eef1f2');panel.paste(image,((640-image.width)//2,(360-image.height)//2));return panel,[x0,y0,x1,y1]
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01';cv2.setNumThreads(1)
    q=load(ROOT/'protocol/render_v1.json');a=load(ROOT/'results/audit.json');v=load(ROOT/'results/independent_verification.json')
    assert sha(ROOT/'results/audit.json')==q['audit_sha256'] and sha(ROOT/'results/independent_verification.json')==q['independent_verification_sha256']
    assert a['protocol_sha256']==q['protocol_sha256']==sha(ROOT/'protocol/duplicate_v1.json')
    assert v['high_overlap_pair_frames']==75 and v['episode_count']==48
    source=Path(q['source_video']);assert sha(source)==q['source_sha256']
    out=ROOT/'results/figures_v2';out.mkdir(exist_ok=False)
    cap=cv2.VideoCapture(str(source));assert (cap.get(5),int(cap.get(7)),int(cap.get(3)),int(cap.get(4)))==(30.,479,1920,1080)
    images={}
    for f in range(max(q['frames'])+1):
        ok,image=cap.read();assert ok,f
        if f in q['frames']:images[f]=image.copy();assert cv2.imwrite(str(out/f'native_f{f}.jpg'),image)
    cap.release();gt=defaultdict(list)
    with (ROOT/'input/publisher_gt_original.txt').open() as f:
        for row in csv.reader(f):r=list(map(float,row));gt[int(r[0])].append(r)
    font=ImageFont.truetype(font_manager.findfont('DejaVu Sans'),24);small=ImageFont.truetype(font_manager.findfont('DejaVu Sans'),17)
    sheet=Image.new('RGB',(1920,820),'white');draw=ImageDraw.Draw(sheet);crops=[]
    for i,r in enumerate(q['all6representatives']):
        im=annotate(images[r['frame']],r,gt[r['frame']],font);panel,rect=crop_context(im,r)
        x=(i%3)*640;y=(i//3)*410;sheet.paste(panel,(x,y));draw.text((x+8,y+361),f'{r["condition"]} | f{r["frame"]}',font=small,fill='black')
        draw.text((x+8,y+380),f'IDs {r["track_IDs"]} | pair IoU {r["pair_IoU"]:.3f}',font=small,fill='black')
        panel.save(out/f'representative_{i+1}.jpg',quality=94);crops.append({'case':r['condition'],'frame':r['frame'],'crop_xyxy':rect})
    sheet.save(out/'all6_representatives.jpg',quality=94)
    special=Image.new('RGB',(1920,585),'white');draw=ImageDraw.Draw(special)
    for i,r in enumerate(q['special_cases']):
        im=annotate(images[r['frame']],r,gt[r['frame']],font);im=im.resize((960,540));special.paste(im,(960*i,0))
        draw.text((960*i+8,545),f'{r["condition"]} | frame {r["frame"]} | IoU {r["pair_IoU"]:.3f}',font=small,fill='black')
        draw.text((960*i+8,565),f'Best publisher IDs: {r["GT_a"]["ID"]}, {r["GT_b"]["ID"]}; geometric support only',font=small,fill='black')
    special.save(out/'known_case_and_distinct_cow_counterexample.jpg',quality=94)
    labels=['Official / installed','Official / pure IoU','Official / allow Lost','Five epoch / installed','Five epoch / pure IoU','Five epoch / allow Lost']
    metrics=a['conditions'];y=np.arange(6);fig,axes=plt.subplots(1,2,figsize=(13,6),gridspec_kw={'width_ratios':[1.05,1.25]})
    colors=['#647b89','#b29a51','#147f80'];bar_values=[]
    fields=['high_overlap_pair_frames','GT_primary_supported_pair_frames','GT_sensitivity_supported_pair_frames']
    legend=['All high-overlap pairs','Same GT, both IoU >=0.5','Same GT, both IoU >=0.3']
    for j,key in enumerate(fields):
        values=[r[key] for r in metrics];bar_values.append(values);axes[0].barh(y+(j-1)*.23,values,height=.21,color=colors[j],label=legend[j])
        for yy,value in zip(y+(j-1)*.23,values):axes[0].text(value+.18,yy,str(value),va='center',fontsize=9)
    axes[0].set_yticks(y,labels,fontsize=9);axes[0].invert_yaxis();axes[0].set_xlim(0,25);axes[0].set_xlabel('Pair x frame occurrences (479-frame clip)');axes[0].set_title('(a) Geometric candidates, not physical duplicate rate',fontsize=10)
    fig.legend(*axes[0].get_legend_handles_labels(),loc='lower left',bbox_to_anchor=(.01,.005),ncol=3,fontsize=8,frameon=False)
    timeline=[]
    for i,c in enumerate(metrics):
        records=[r for r in a['all_high_overlap_pairs'] if r['condition']==c['condition']];frames=sorted({r['frame'] for r in records});types=[]
        for f in frames:
            rows=[r for r in records if r['frame']==f];kind=2 if any(r['primary_same_GT'] for r in rows) else 1 if any(r['sensitivity_same_GT'] for r in rows) else 0
            types.append(kind)
        axes[1].scatter(frames,[i]*len(frames),marker='|',s=130,c=[[colors[0],colors[2],colors[1]][t] for t in types],linewidths=2)
        timeline.append({'condition':c['condition'],'distinct_frames':frames,'support_color_class':types})
    axes[1].set_yticks(y,labels,fontsize=9);axes[1].invert_yaxis();axes[1].set_ylim(5.6,-.6);axes[1].set_xlim(0,478);axes[1].set_xlabel('Source frame (0-based, 30 fps)')
    axes[1].set_title('(b) One mark per source frame with a candidate',fontsize=10)
    for axis in axes:
        axis.spines[['top','right']].set_visible(False);axis.grid(axis='x',alpha=.15);axis.set_axisbelow(True)
    fig.suptitle('Toros: high-overlap ID pairs across six fixed tracker replays',fontsize=13)
    fig.text(.01,.06,'Both models reuse the same already-used 479-frame clip. Pair IoU >=0.5. Reference support depends on box definition.\nColors in timeline show strongest reference support in that frame. No predictions were changed.',fontsize=8)
    fig.tight_layout(rect=(0,.13,1,.94))
    for ext in ['png','svg','pdf']:fig.savefig(out/f'redundancy_diagnostics.{ext}',dpi=180,bbox_inches='tight')
    plt.close(fig)
    record={'status':'SOURCE_CASE_PANELS_AND_STANDARD_PLOT_RENDERED','job_id':os.environ['SLURM_JOB_ID'],
      'audit_sha256':q['audit_sha256'],'source_sha256':q['source_sha256'],'matplotlib_version':matplotlib.__version__,
      'native_frames':q['frames'],'representative_crops':crops,'bar_fields':fields,'bar_values':bar_values,'timeline':timeline,
      'output_files':[{'path':f.name,'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(out.iterdir())],
      'new_detector_forwards':0,'new_independent_reference':False}
    save(ROOT/'results/render_record_v2.json',record)
    files=[ROOT/'protocol/render_v1.json',ROOT/'tools/render_v2.py',ROOT/'tools/render_v2.slurm',ROOT/'results/render_record_v2.json',*out.iterdir()]
    manifest=[{'path':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files];mp=ROOT/'results/render_manifest_v2.json';save(mp,manifest)
    archive=ROOT/'results/render_v2_delivery.tar.gz';assert not archive.exists()
    with tarfile.open(archive,'w:gz') as tf:
        for f in files:tf.add(f,arcname=f.relative_to(ROOT).as_posix())
        tf.add(mp,arcname='delivery_manifest.json')
    delivery={'manifest_files':len(files),'archive_members':len(files)+1,'bytes':archive.stat().st_size,'sha256':sha(archive),'manifest_sha256':sha(mp)}
    save(ROOT/'results/render_v2_delivery_record.json',delivery);print(json.dumps(delivery),flush=True)
if __name__=='__main__':main()
