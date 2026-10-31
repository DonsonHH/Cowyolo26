from pathlib import Path
from datetime import datetime,timezone
import json,gzip,hashlib,subprocess,os
from collections import defaultdict
import numpy as np,cv2
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
plt.rcParams['svg.fonttype']='none'
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'results/baseline'
def load(p):return json.loads(p.read_text())
def loadgz(p):return json.loads(gzip.decompress(p.read_bytes()))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
protocol=load(ROOT/'protocol/baseline_v2_path_fix.json');summary=load(OUT/'summary.json');assert summary['protocol_sha256']==sha(ROOT/'protocol/baseline_v2_path_fix.json')
out=ROOT/'results/plots_v2';out.mkdir(exist_ok=False)
models=[m['name'] for m in protocol['models']];sizes=[192,256,320];colors=['#436fbd','#d28a40','#258471']
fig,axes=plt.subplots(2,2,figsize=(12,8));bar_data=[]
for ai,(axis,kind,title,limit) in enumerate([(axes[0,0],'localization','(a) Matched visible torso envelopes / 1,864',2000),
(axes[0,1],'original','(b) Original human-confirmed clip: down count',14),
(axes[1,0],'toros5','(c) Toros correct event matches / 6 at 5Hz',7),
(axes[1,1],'toros30','(d) Toros correct event matches / 6 at 30Hz control',7)]):
    for si,size in enumerate(sizes):
        values=[]
        for model in models:
            cname=model+'_s'+str(size)
            if kind=='localization':value=next(r for r in summary['validation_metrics'] if r['condition']==cname)['matched']
            else:
                scene='original' if kind=='original' else 'toros';stride=5 if scene=='original' else 6 if kind=='toros5' else 1
                row=next(r for r in summary['video_metrics'] if r['condition']==cname and r['scene']==scene and r['sample_stride']==stride and r['counter']=='handoff_events')
                value=row['down'] if scene=='original' else row['formal_event_metrics']['TP']
            values.append(value)
        x=np.arange(4)+(si-1)*.24;bars=axis.bar(x,values,width=.22,label=str(size),color=colors[si])
        for i,(bar,value) in enumerate(zip(bars,values)):
            axis.text(bar.get_x()+bar.get_width()/2,value+limit*.015,str(value),ha='center',va='bottom',fontsize=8,rotation=90)
            bar_data.append({'panel':ai,'model':models[i],'size':size,'value':value,'bar_x':float(bar.get_x()),'width':float(bar.get_width()),'ymax':limit})
    axis.set_ylim(0,limit);axis.set_xlim(-.6,3.6);axis.set_xticks(range(4),models);axis.set_title(title,fontsize=11)
    axis.spines[['top','right']].set_visible(False);axis.grid(axis='y',alpha=.15);axis.set_axisbelow(True)
    if kind=='original':axis.axhline(12,color='#a84452',linestyle='--',linewidth=1);axis.text(3.55,12.15,'12',color='#a84452',ha='right',fontsize=9)
    if kind.startswith('toros'):axis.axhline(6,color='#a84452',linestyle='--',linewidth=1)
handles,labels=axes[0,0].get_legend_handles_labels()
fig.legend(handles,labels,title='Input size',ncol=3,frameon=False,loc='upper right',bbox_to_anchor=(.98,.955),fontsize=9)
fig.suptitle('192 / 256 / 320 square-input baselines: accuracy and sampling effects',y=.98,fontsize=14)
fig.text(.06,.025,'Four frozen FP32 detectors; same counters and conf0.2. Already-used development data. Server replay rate is not PYNQ throughput.',fontsize=9)
fig.subplots_adjust(left=.07,right=.98,top=.85,bottom=.09,hspace=.36,wspace=.22)
fig.savefig(out/'lowres_baseline_counts.png',dpi=180);fig.savefig(out/'lowres_baseline_counts.svg');plt.close(fig)
(out/'plot_data.json').write_text(json.dumps({'bars':bar_data,'models':models,'sizes':sizes,'image_panels':4},indent=2)+'\n')
(out/'manifest.json').write_text(json.dumps([{'relative_file':f.relative_to(ROOT).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in sorted(out.iterdir()) if f.is_file()],indent=2)+'\n')
print(json.dumps({'status':'SAME48BARVALUES_LAYOUT_V2_LEGEND_AND_ANNOTATION_SPACING_REPAIRED','panels':4,'new_model_forwards':0}))
