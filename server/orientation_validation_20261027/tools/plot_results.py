"""Standalone scientific figure and machine-readable metric table."""
from pathlib import Path
import csv,hashlib,json,os,socket
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    source=ROOT/'results/control/summary.json';summary=json.loads(source.read_text())
    assert summary['status']=='FROZEN_THREE_SEED_PAIRED_ORIENTATION_VALIDATION_COMPLETE'
    comparisons=summary['primary_paired_comparisons'];assert [r['seed'] for r in comparisons]==[26,27,28]
    out=ROOT/'figures';out.mkdir(exist_ok=False)
    all_metrics=[metric for item in summary['conditions'] for metric in item['metrics']]
    fields=['seed','orientation','confidence_threshold','IoU_threshold','GT','predictions','TP','FP','FN','recall','precision']
    with (out/'metrics_all24.csv').open('w',newline='') as file:
        writer=csv.DictWriter(file,fieldnames=fields);writer.writeheader()
        writer.writerows([{k:row[k] for k in fields} for row in all_metrics])
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'svg.fonttype':'none'})
    fig,axes=plt.subplots(1,2,figsize=(10.6,4.8),gridspec_kw={'width_ratios':[1.15,1]})
    x=np.arange(3);width=.34
    originals=np.array([r['original_recall'] for r in comparisons])*100
    turns=np.array([r['clockwise90_recall'] for r in comparisons])*100
    bars0=axes[0].bar(x-width/2,originals,width,label='Original pixels',color='#244963')
    bars1=axes[0].bar(x+width/2,turns,width,label='90 deg clockwise',color='#bb6045')
    axes[0].set_ylim(0,106);axes[0].set_xticks(x,[f'Seed {r["seed"]}' for r in comparisons])
    axes[0].set_ylabel('Matched body-box recall (%)')
    axes[0].set_title('Fixed confidence 0.20 and IoU 0.50',loc='left',fontweight='bold')
    axes[0].legend(frameon=False,loc='lower left')
    for bars in [bars0,bars1]:
        for bar in bars:
            axes[0].text(bar.get_x()+bar.get_width()/2,bar.get_height()+1.2,f'{bar.get_height():.1f}',ha='center',fontsize=9)
    delta=(turns-originals)
    bounds=np.array([r['date_cluster_bootstrap95_percentile'] for r in comparisons])*100
    axes[1].axvline(0,color='#999999',linewidth=1)
    axes[1].errorbar(delta,x,xerr=[delta-bounds[:,0],bounds[:,1]-delta],fmt='o',color='#7d4030',
                     ecolor='#bb6045',capsize=5,markersize=6,linewidth=1.5)
    axes[1].set_yticks(x,[f'Seed {r["seed"]}' for r in comparisons]);axes[1].invert_yaxis()
    axes[1].set_xlim(-21,3);axes[1].set_ylim(2.5,-.5)
    axes[1].set_xlabel('Recall difference: 90 deg minus original (pp)')
    axes[1].set_title('Paired change by model',loc='left',fontweight='bold')
    for i,value in enumerate(delta):axes[1].text(value,i-.16,f'{value:.2f} pp',ha='center',fontsize=9)
    for ax in axes:
        ax.spines[['top','right']].set_visible(False);ax.grid(axis='y' if ax is axes[0] else 'x',color='#dddddd',linewidth=.7)
        ax.set_axisbelow(True)
    fig.suptitle('Orientation sensitivity of frozen Cows2021 detectors',x=.09,ha='left',fontweight='bold',fontsize=14)
    fig.text(.09,.90,'Same 1,571 validation images / 1,864 objects / 6 source dates; 320 x 320 inference.',fontsize=10)
    fig.text(.09,.065,'Right: exploratory 95% percentile intervals from 10,000 date-cluster resamples (only 6 dates).',fontsize=9,color='#555555')
    fig.text(.09,.025,'Diagnostic on development data. No new training, source-video counting, final holdout or board measurement.',fontsize=9,color='#555555')
    fig.subplots_adjust(left=.09,right=.98,top=.80,bottom=.22,wspace=.45)
    fig.savefig(out/'paired_orientation_recall.png',dpi=180)
    fig.savefig(out/'paired_orientation_recall.svg')
    plt.close(fig)
    record={'status':'SCIENTIFIC_PNG_SVG_AND_24_ROW_METRIC_TABLE_CREATED','job_id':os.environ['SLURM_JOB_ID'],
            'source_summary_sha256':sha(source),'matplotlib':matplotlib.__version__,
            'files':[{'name':p.name,'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(out.iterdir()) if p.is_file()],
            'source_video_or_final_accuracy_claimed':False}
    path=ROOT/'results/figure_record.json';assert not path.exists();path.write_text(json.dumps(record,indent=2))
    print(json.dumps(record),flush=True)


if __name__=='__main__':main()
