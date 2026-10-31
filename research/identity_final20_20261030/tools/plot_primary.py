from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,os,socket
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT=Path(__file__).resolve().parents[1]
assert os.environ.get('SLURM_JOB_ID')and socket.gethostname()!='mu01'
rows=json.loads((ROOT/'results/evaluation/all_outcomes.json').read_text());a=next(r for r in rows if r['model']=='old_C'and r['policy']=='primary_cal10_fold0');b=next(r for r in rows if r['model']=='new_C_domain_seed26'and r['policy']=='primary_cal10_fold0')
out=ROOT/'results/figures';out.mkdir(exist_ok=False);plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
fig,ax=plt.subplots(1,2,figsize=(10.5,4.5),layout='constrained');names=['Old encoder','New domain encoder'];colors=['#678293','#238774']
for i,row in enumerate([a,b]):
 ax[0].barh(i,row['known_Top1'],height=.48,color=colors[i]);ax[0].text(row['known_Top1']+.4,i,f"{row['known_Top1']}/30",va='center')
ax[0].set(yticks=[0,1],yticklabels=names,xlim=(0,34),xticks=[0,10,20,30],xlabel='Known query images',title='A  Correct first-ranked identity');ax[0].invert_yaxis()
left=[0,0]
for key,label,color in[('C','Correctly accepted','#238774'),('W','Wrong identity accepted','#b64c45'),('U','Rejected','#d0d6da')]:
 values=[a[key],b[key]];ax[1].barh([0,1],values,left=left,height=.48,label=label,color=color)
 for i,value in enumerate(values):
  if value:ax[1].text(left[i]+value/2,i,str(value),va='center',ha='center',color='white'if key in['C','W']else'#28343d')
 left=[x+y for x,y in zip(left,values)]
ax[1].set(yticks=[0,1],yticklabels=names,xlim=(0,30),xticks=[0,10,20,30],xlabel='Known query images',title='B  Decisions at frozen primary thresholds');ax[1].invert_yaxis();ax[1].legend(loc='lower left',bbox_to_anchor=(0,-.45),frameon=False,fontsize=9)
fig.suptitle('Ranking and automatic acceptance on the 20 reserved Cows2021 identities',fontsize=13)
fig.supxlabel('Unknown false accepts: old 3/30; new 0/30.  10 known IDs and 10 unknown IDs, three queries each.\nSame-scene curated crops; fixed gallery 10 IDs; no passage or field-identity result.',fontsize=9)
for suffix in['png','svg']:fig.savefig(out/('final20_primary.'+suffix),dpi=170,bbox_inches='tight')
plt.close(fig)
v={'status':'PRIMARY_FIXED_OUTCOMES_PLOTTED_WITHOUT_INFERENCE','created_UTC':datetime.now(timezone.utc).isoformat(),'Slurm_job_id':os.environ['SLURM_JOB_ID'],'matplotlib_version':matplotlib.__version__,'data_SHA256':hashlib.sha256((ROOT/'results/evaluation/all_outcomes.json').read_bytes()).hexdigest(),'new_model_forwards':0,'files':[{'file':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}for p in sorted(out.iterdir())]};(ROOT/'results/figure_manifest.json').write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v),flush=True)
