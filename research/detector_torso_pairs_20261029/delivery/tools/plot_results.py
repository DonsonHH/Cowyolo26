from pathlib import Path
from collections import Counter
import gzip,json,hashlib
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
plt.rcParams['svg.fonttype']='none';plt.rcParams['path.simplify']=False
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/pairs'
summary=json.loads((OUT/'summary.json').read_text());p=json.loads((ROOT/'protocol/pairs_v1.json').read_text())
models=[r['name'] for r in p['models']];records={r['condition']:r for r in summary['condition_summaries'] if r['split']=='val'}
dest=ROOT/'results/plots';dest.mkdir(exist_ok=False);data={'bars':[],'curves':[]}
fig,(a,b)=plt.subplots(1,2,figsize=(12.5,4.9),sharey=True,gridspec_kw={'width_ratios':[1.5,1]})
for i,model in enumerate(models):
    row=records[model];tp=row['matched'];fn=row['unmatched_references'];extra=row['unmatched_predictions']
    a.barh(i,tp,color='#277f70',height=.58);a.barh(i,fn,left=tp,color='#dce2e6',height=.58);b.barh(i,extra,color='#a96a46',height=.58)
    a.text(tp/2,i,str(tp),ha='center',va='center',color='white',fontsize=11)
    if fn:a.text(tp+fn/2,i,str(fn),ha='center',va='center',fontsize=11)
    b.text(extra+12,i,str(extra),va='center',fontsize=11)
    data['bars'].extend([{'panel':0,'row':i,'left':0,'width':tp,'kind':'matched'},{'panel':0,'row':i,'left':tp,'width':fn,'kind':'unmatched_reference'},
                        {'panel':1,'row':i,'left':0,'width':extra,'kind':'unmatched_prediction'}])
right_limit=max(500,int(np.ceil(max(records[m]['unmatched_predictions'] for m in models)*1.15/100))*100)
data['bar_xlim_by_panel']=[2000,right_limit]
a.set_yticks(range(4),models);a.invert_yaxis();a.set_xlim(0,2000);b.set_xlim(0,right_limit)
a.set_xticks([0,500,1000,1500,1864]);b.set_xticks(np.arange(0,right_limit+1,500))
a.set_title('(a) Visible torso-reference envelope matching');b.set_title('(b) Predictions without a reference match')
a.set_xlabel('Reference boxes (total 1,864)');b.set_xlabel('Unmatched predicted boxes')
for axis in [a,b]:axis.set_axisbelow(True);axis.grid(axis='x',alpha=.2);axis.spines[['top','right']].set_visible(False)
a.legend(handles=[Patch(facecolor='#277f70',label='Matched at AABB IoU >=0.5'),Patch(facecolor='#dce2e6',label='No match')],loc='lower left',bbox_to_anchor=(0,-.28),ncol=2,frameon=False,fontsize=9)
fig.suptitle('Fixed 640px CW90 detectors on the same 1,571 development images',y=.97,fontsize=14)
fig.text(.07,.027,'Body-reference agreement only. Unmatched predictions may be real whole cows or unlabeled regions; no passage or identity accuracy.',fontsize=9)
fig.subplots_adjust(left=.11,right=.97,top=.84,bottom=.22,wspace=.17)
fig.savefig(dest/'reference_matching.png',dpi=180);fig.savefig(dest/'reference_matching.svg');plt.close(fig)
fig,axes=plt.subplots(1,3,figsize=(15,4.8));colors={'official':'#396db1','seed26':'#2b8870','seed27':'#cc7e32','seed28':'#8561b5'}
def curve(axis,panel,key,values,label,color,style='-'):
    values=np.sort(np.asarray(values,dtype=float));y=np.arange(1,len(values)+1)/len(values)
    line=axis.step(values,y,where='post',label=label+' (n='+str(len(values))+')',color=color,linestyle=style,linewidth=1.7)[0]
    line.set_gid('curve_'+str(panel)+'_'+key)
    data['curves'].append({'panel':panel,'key':key,'x':values.tolist(),'y':y.tolist(),'sample_count':len(values),'curve_id':'curve_'+str(panel)+'_'+key})
geometry=json.loads(gzip.decompress((OUT/'source_geometry.json.gz').read_bytes()))['val']
refs=[r for im in geometry for r in im['references']]
for complete,label,color in [(True,'Complete reference','#183f64'),(False,'Clipped reference','#909da8')]:
    curve(axes[0],0,'complete' if complete else 'clipped',[r['ideal_AABB_exterior_fraction'] for r in refs if r['reference_complete']==complete],label,color)
for model in models:
    pairs=json.loads(gzip.decompress((OUT/('val_'+model+'_reference_pairs.json.gz')).read_bytes()))
    matches=[r for image in pairs for r in image['reference_pairs'] if r['matched_prediction_index'] is not None and r['reference_complete']]
    curve(axes[1],1,model,[r['crop_metrics']['reference_coverage'] for r in matches],model,colors[model])
    curve(axes[2],2,model,[r['crop_metrics']['reference_exterior_fraction'] for r in matches],model,colors[model])
curve(axes[2],2,'ideal_complete',[r['ideal_AABB_exterior_fraction'] for r in refs if r['reference_complete']],'Ideal reference AABB','#30363d','--')
titles=['(a) Ideal axis-aligned reference envelope','(b) Actual crop coverage of reference','(c) Actual crop reference-exterior portion']
labels=['Reference-exterior portion','Visible reference covered','Reference-exterior portion']
for i,axis in enumerate(axes):
    axis.set_title(titles[i],fontsize=11);axis.set_xlabel(labels[i]);axis.set_xlim(0,1);axis.set_ylim(0,1);axis.grid(alpha=.2)
    axis.set_xticks(np.linspace(0,1,5));axis.set_yticks(np.linspace(0,1,5));axis.spines[['top','right']].set_visible(False)
    axis.legend(fontsize=8,loc='lower right' if i!=1 else 'upper left',frameon=True)
axes[0].set_ylabel('Cumulative fraction of reference boxes')
axes[0].axvline(.25,color='#ad4352',alpha=.6,linestyle=':',linewidth=1)
axes[1].axvline(.9,color='#ad4352',alpha=.6,linestyle=':',linewidth=1)
axes[2].axvline(.25,color='#ad4352',alpha=.6,linestyle=':',linewidth=1)
fig.suptitle('Separating axis-aligned representation limits from detector crop errors',y=.98,fontsize=14)
fig.text(.055,.035,'Panels b/c use complete matched references only; missed detections excluded from these CDFs. Reference-exterior is not semantic background.',fontsize=9)
fig.subplots_adjust(left=.055,right=.98,top=.85,bottom=.19,wspace=.32)
fig.savefig(dest/'crop_geometry_CDF.png',dpi=180);fig.savefig(dest/'crop_geometry_CDF.svg');plt.close(fig)
data['image_panels']=5
(dest/'plot_data.json').write_text(json.dumps(data,separators=(',',':'))+'\n')
(dest/'manifest.json').write_text(json.dumps([{'relative_file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()} for f in sorted(dest.iterdir()) if f.is_file()],indent=2)+'\n')
print(json.dumps({'figures':2,'image_panels':5,'bar_segments':len(data['bars']),'CDF_curves':len(data['curves']),'CDF_input_points':sum(len(r['x']) for r in data['curves'])}))
