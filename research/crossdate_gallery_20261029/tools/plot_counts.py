from pathlib import Path
import json,hashlib
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
ROOT=Path(__file__).resolve().parents[1]
summary=json.loads((ROOT/'results/study_v2/summary.json').read_text());rows=[]
for r in summary['conditions']:
    m=r['curated_metrics'];rows.append({'condition':r['condition'],'gallery':r['gallery_condition'],
    'C':m['known_correct_accepted_C'],'W':m['known_wrong_accepted_W'],'U':m['known_rejected_U'],'F':m['unknown_false_accepts']})
out=ROOT/'results/plots';out.mkdir(exist_ok=False)
fig,(left,right)=plt.subplots(1,2,figsize=(12,6.7),gridspec_kw={'width_ratios':[1.6,1]},sharey=True)
short={'A_official_frozen':'A','B_letterbox_frozen':'B','C_letterbox_trained_seed26':'C26','C_letterbox_trained_seed27':'C27','C_letterbox_trained_seed28':'C28'}
labels=[];bars=[]
for y,row in enumerate(rows):
    labels.append(short[row['condition']]+' / Aug'+('14' if row['gallery']=='old_Aug14' else '19'))
    x=0
    for key,col in [('C','#25816b'),('W','#cc644a'),('U','#dce3e7')]:
        width=row[key];left.barh(y,width,left=x,color=col,height=.68)
        bars.append({'panel':'registered','row':y,'kind':key,'left':x,'width':width,'height':.68})
        if width:left.text(x+width/2,y,str(width),ha='center',va='center',fontsize=9,color='white' if key=='C' else '#142d3b')
        x+=width
    right.barh(y,row['F'],color='#bb465a',height=.68)
    bars.append({'panel':'unknown','row':y,'kind':'F','left':0,'width':row['F'],'height':.68})
    right.text(row['F']+.3,y,str(row['F'])+'/30',va='center',fontsize=10)
left.set_yticks(range(10),labels);left.invert_yaxis();left.set_xlim(0,30);right.set_xlim(0,30)
for axis in (left,right):
    axis.set_xticks([0,5,10,15,20,25,30]);axis.set_axisbelow(True);axis.grid(axis='x',alpha=.2)
    axis.spines[['top','right']].set_visible(False)
left.set_title('(a) Registered queries (30 images)');right.set_title('(b) Gallery-excluded queries (30 images)')
left.set_xlabel('Correct accept / wrong accept / reject');right.set_xlabel('False accepts at unchanged threshold')
left.legend(handles=[Patch(facecolor='#25816b',label='Correct accept'),Patch(facecolor='#cc644a',label='Wrong accept'),Patch(facecolor='#dce3e7',label='Reject')],loc='lower left',bbox_to_anchor=(0,-.19),ncol=3,frameon=False,fontsize=9)
fig.suptitle('Gallery date changes both coverage and false-acceptance risk',x=.53,y=.97,fontsize=14)
fig.text(.08,.025,'Five frozen encoder configurations. Gallery: 6 IDs x 5 images. Same Aug20 development queries. No threshold or weight changes.',fontsize=9)
fig.subplots_adjust(left=.14,right=.97,top=.89,bottom=.16,wspace=.15)
fig.savefig(out/'gallery_date_risk.png',dpi=180)
fig.savefig(out/'gallery_date_risk.svg')
data={'rows':rows,'bars':bars,'registered_total':30,'unknown_total':30,'x_limits':[0,30],'y_ticks':list(range(10)),'labels':labels,'image_panels':2}
(out/'plot_data.json').write_text(json.dumps(data,indent=2)+'\n')
(out/'manifest.json').write_text(json.dumps([{'relative_file':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(out.iterdir()) if p.is_file()],indent=2)+'\n')
print(json.dumps({'images':['gallery_date_risk.png','gallery_date_risk.svg'],'panels':2,'rows':10,'bar_segments':len(bars)}))
