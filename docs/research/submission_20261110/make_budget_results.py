"""Generate manuscript numbers/tables and publication plots only from verified V4."""
from pathlib import Path
import csv
import hashlib
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
root=Path(__file__).resolve().parent
data=json.loads((root/'EQUAL_BUDGET_BATCH_V4_VERIFIED.json').read_bytes())
assert data['batch_status']=='COMPLETED' and len(data['cases'])==16
rows=data['cases'];clips=['aug14','aug15','aug19','aug20']
lookup={(r['clip'],r['policy'],r['repeat']):r for r in rows}
paper=root/'manuscript_count_primary';figures=root/'figures'
paper.mkdir(exist_ok=True);figures.mkdir(exist_ok=True)
fields=['tag','clip','repeat','policy','status','absolute_count_error','planned_real_calls',
        'real_calls','global_calls','local_calls','warmup_calls','event_publication_max_ms',
        'observation_age_max_ms','observation_age_p95_ms','capture_lateness_max_ms',
        'stream_wall_s','drain_s','overwritten_frames','not_admitted_frames']
with (root/'BUDGET_RESULTS.csv').open('w',newline='',encoding='utf-8') as f:
    writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore')
    writer.writeheader();writer.writerows(rows)
a='global_pair';b='conditional_local_pair'
mae=data['per_repeat_full_four_video_aggregates']
assert [mae[p+'_r'+str(r)]['mean_absolute_error_over_reviewed_directions_per_video']
        for p in (a,b) for r in (1,2)]==[1.5,1.5,.25,.25]
event=max(r['event_publication_max_ms'] for r in rows)
obs=max(r['observation_age_max_ms'] for r in rows)
p95=max(r['observation_age_p95_ms'] for r in rows)
capture=max(r['capture_lateness_max_ms'] for r in rows)
drain=max(r['drain_s'] for r in rows)
assert event<=1000 and obs<=1500 and p95<=1000 and capture<=500 and drain<=1
calls={p:sum(r['real_calls'] for r in rows if r['policy']==p) for p in (a,b)}
locals_b=sum(r['local_calls'] for r in rows if r['policy']==b)
assert calls[a]==calls[b]==2060
abstract=(r'In two repeats, the global-only policy had MAE 1.50 passages per video and the replacement policy had MAE 0.25; '
          r'the latter improved three clips and degraded one. Each policy executed 2,060 non-warm-up calls over both repeats. '
          rf'The largest event-publication age was {event:.1f}~ms. ')
(paper/'abstract_result.tex').write_text(abstract+'\n')
summary=rf'''All 16 declared cases completed with the fixed call quota. A counted 11, 12, 9, and 9 on the four clips in each repeat; B counted 12, 11, 11, and 12. Each repeat therefore had MAE 1.50 for A and 0.25 for B, with exact agreement in one and three of four videos, respectively. B's August~15 underestimate is retained: the policy did not improve every clip.

Each policy used 1,030 non-warm-up calls per repeat, plus four separate warm-ups. Across both repeats B allocated {locals_b} calls to local crops and {calls[b]-locals_b} to global images; A used {calls[a]} global calls. All {data['raw_arrays_verified']:,} non-warm-up raw arrays were checked against their call records. The independent comparison of 24 pairs of runs found 6,015 shared global input/output hash pairs, all identical; the pair count is not additional independent observations.

The event-publication maximum over all runs was {event:.3f}~ms. The observation-completion maximum was {obs:.3f}~ms, and the largest per-run observation p95 was {p95:.3f}~ms. Capture lateness reached {capture:.3f}~ms and final stream drain reached {drain:.6f}~s. All original replay reference checks passed, including the 1,500-ms observation maximum; not every observation was younger than 1~s. Acquisition remained paced, all admitted calls used arrived frames, and no planned global was lost in this block.

\begin{{figure*}}[!t]
\centering
\includegraphics[width=0.98\textwidth]{{figures/paired_results.pdf}}
\caption{{Count error and maximum event-publication age for all sixteen development replays. Marker shapes distinguish repetitions; they are repeated executions of four videos, not additional animal samples. The 1-s line is a replay publication reference, not a measured physical crossing deadline.}}
\label{{fig:results}}
\end{{figure*}}
'''
(paper/'results_summary.tex').write_text(summary)
table=r'''\begin{table*}[!t]
\caption{Complete Fixed-Budget Development Comparison (Repeat 1 / Repeat 2)}
\label{tab:budget}
\centering\small
\begin{tabular}{lrrrrrr}
\toprule
Clip & Reference & A count & B count & Calls per policy & B global & B local\\
\midrule
'''
for clip in clips:
    ra=[lookup[(clip,p,r)] for p in (a,b) for r in (1,2)]
    reference=next(iter(ra[0]['reference_totals'].values()))
    table+=f"{clip.replace('aug','Aug ')} & {reference} & {ra[0]['counts']['IN']}/{ra[1]['counts']['IN']} & {ra[2]['counts']['IN']}/{ra[3]['counts']['IN']} & {ra[0]['real_calls']}/{ra[1]['real_calls']} & {ra[2]['global_calls']}/{ra[3]['global_calls']} & {ra[2]['local_calls']}/{ra[3]['local_calls']}"+r'\\'+'\n'
table+=r'''\midrule
MAE / video & -- & 1.50 / 1.50 & 0.25 / 0.25 & -- & -- & --\\
\bottomrule
\end{tabular}
\end{table*}
'''
(paper/'results_table.tex').write_text(table)
BLUE='#0072B2';ORANGE='#D55E00'
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':8,'pdf.fonttype':42,
                     'svg.fonttype':'none','axes.spines.top':False,'axes.spines.right':False})
fig,axes=plt.subplots(1,2,figsize=(7.16,2.65),layout='constrained')
x=np.arange(4)
for policy,color,shift,label in [(a,BLUE,-.13,'A: two globals'),(b,ORANGE,.13,'B: conditional local')]:
    for repeat,marker,jitter in [(1,'o',-.025),(2,'s',.025)]:
        values=[lookup[(c,policy,repeat)] for c in clips]
        for ax,key in zip(axes,['absolute_count_error','event_publication_max_ms']):
            ax.scatter(x+shift+jitter,[v[key] for v in values],marker=marker,s=28,
                       facecolors='none' if repeat==2 else color,edgecolors=color,lw=1,
                       label=label if repeat==1 else None,zorder=3)
for ax in axes:
    ax.set_xticks(x,[c.replace('aug','Aug ') for c in clips])
    ax.set_xlim(-.5,3.5);ax.set_xlabel('Development clip')
    ax.grid(axis='y',color='#E6E9EC',linewidth=.6);ax.set_axisbelow(True)
axes[0].set_ylabel('Absolute count error (passages)')
axes[0].set_ylim(-.12,3.5);axes[0].set_yticks([0,1,2,3])
axes[0].set_title('(a) Reviewed-direction totals',loc='left',fontsize=9)
axes[0].legend(frameon=False,fontsize=7,loc='upper left')
axes[1].set_ylabel('Maximum event-publication age (ms)')
axes[1].set_ylim(0,max(1100,event+100));axes[1].axhline(1000,color='#66717C',ls='--',lw=.8)
axes[1].text(.98,1020,'1-s replay reference',ha='right',va='bottom',
             transform=axes[1].get_yaxis_transform(),fontsize=7,color='#66717C')
axes[1].set_title('(b) Age from scheduled image arrival',loc='left',fontsize=9)
for ext in ['pdf','svg','png']:fig.savefig(figures/('paired_results.'+ext),dpi=400,bbox_inches='tight',pad_inches=.03)
plt.close(fig)
result={'verified_source_sha256':hashlib.sha256((root/'EQUAL_BUDGET_BATCH_V4_VERIFIED.json').read_bytes()).hexdigest(),
 'rows':16,'raw_arrays':data['raw_arrays_verified'],'nonwarmup_calls_per_policy_both_repeats':calls,
 'B_local_calls_both_repeats':locals_b,'event_max_ms':event,'observation_max_ms':obs,
 'largest_perrun_p95_ms':p95,'capture_max_ms':capture,'drain_max_s':drain,
 'new_model_forwards':0,
 'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [paper/'abstract_result.tex',
    paper/'results_summary.tex',paper/'results_table.tex',root/'BUDGET_RESULTS.csv',
    figures/'paired_results.pdf',figures/'paired_results.svg',figures/'paired_results.png']}}
(root/'BUDGET_RESULT_ARTIFACTS.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k!='files'},indent=2))
