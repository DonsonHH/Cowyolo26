"""Write final fusion tables from actual V7 runs, preserving its extra-case failure."""
from pathlib import Path
import csv
import hashlib
import json
root=Path(__file__).resolve().parent
data=json.loads((root/'BIRTH_GEOMETRY_V7_VERIFIED.json').read_bytes())
paper=root/'manuscript_count_primary'
known=[r for r in data['cases'] if r['clip']!='aug17_negative' and r['status']=='COMPLETED_UNSCORED']
assert len(known)==8
lookup={(r['clip'],r['repeat']):r for r in known}
mae=data['per_repeat_full_four_video_aggregates']
values=[mae['conditional_local_pair_r'+str(r)]['mean_absolute_error_over_reviewed_directions_per_video'] for r in (1,2)]
event=max(r['event_publication_max_ms'] for r in known)
obs=max(r['observation_age_max_ms'] for r in known)
p95=max(r['observation_age_p95_ms'] for r in known)
capture=max(r['capture_lateness_max_ms'] for r in known)
drain=max(r['drain_s'] for r in known)
clock=lambda r:r['event_publication_max_ms']<=1000 and r['observation_age_max_ms']<=1500 and r['observation_age_p95_ms']<=1000 and r['capture_lateness_max_ms']<=500 and r['drain_s']<=1
passes=sum(clock(r) for r in known)
fields=['tag','clip','repeat','status','absolute_count_error','real_calls','global_calls','local_calls','warmup_calls',
        'event_publication_max_ms','observation_age_max_ms','observation_age_p95_ms','capture_lateness_max_ms','drain_s','error']
with (root/'BIRTH_GEOMETRY_RESULTS.csv').open('w',newline='',encoding='utf-8') as f:
    writer=csv.DictWriter(f,fieldnames=fields,extrasaction='ignore');writer.writeheader();writer.writerows(data['cases'])
abstract=(rf'The subsequent global-geometry birth variant had MAE {values[0]:.2f} and {values[1]:.2f} in the same two development repeats at the same call quota; {passes} of eight runs met the original replay references. ')
(paper/'fusion_abstract.tex').write_text(abstract+'\n')
text=rf'''\subsection{{Geometry-Preserving Birth Verification}}
The closed-loop board executions of the new variant used 1,030 normal calls per repeat, with four separate warm-ups. They counted 12, 12, 11, and 12 in each repeat, giving MAE {values[0]:.2f} and {values[1]:.2f}. The selected input and raw outputs, actual fusion use, call slots, and per-frame cumulative counts were verified. These are further executions of the same four exposed videos; the change was selected after inspecting their results.

The worst event-publication age was {event:.3f}~ms and the observation-completion maximum was {obs:.3f}~ms. The largest per-run observation p95 was {p95:.3f}~ms, capture lateness was at most {capture:.3f}~ms, and drain was at most {drain:.6f}~s. {passes} of eight runs met all original references. The 1-s publication overrun is retained rather than relabeled, even though its directional total agreed.

\begin{{table}}[!t]
\caption{{Geometry-Preserving Birth Variant: Actual Board Counts}}
\label{{tab:fusion}}
\centering\small
\begin{{tabular}}{{lrrrr}}
\toprule
Clip & Reference & Repeat 1 & Repeat 2 & Calls / repeat\\
\midrule
'''
for clip,n in [('aug14',12),('aug15',12),('aug19',11),('aug20',12)]:
    a,b=lookup[(clip,1)],lookup[(clip,2)]
    text+=f"{clip.replace('aug','Aug ')} & {n} & {a['counts']['IN']} & {b['counts']['IN']} & {a['real_calls']}"+r'\\'+'\n'
text+=r'''\bottomrule
\end{tabular}
\end{table}

An additional fixed camera~2 August~17 input, without an accepted human total, did not finish its SD-backed replay: planned frame404 was unavailable and frame410 was observed. Its partial zero is unscored. The frame-retrieval maximum exceeded1s while the detector API maximum was338.3ms. This separates an observed input/logging jitter issue from count agreement on completed positive clips. The nine-case parent batch remains failed, with eight completed positive runs; it is not an all-case deployment pass.
'''
(paper/'fusion_result.tex').write_text(text)
value={'positive_runs':8,'full_nine_case_batch_status':data['batch_status'],'per_repeat_MAE':values,
 'original_clock_pass_runs':passes,'event_max_ms':event,'observation_max_ms':obs,'p95_max_ms':p95,
 'capture_max_ms':capture,'drain_max_s':drain,
 'actual_positive_nonwarmup_calls':sum(r['real_calls'] for r in known),
 'actual_positive_local_calls':sum(r['local_calls'] for r in known),
 'new_model_forwards':0,'independent_positive_test':False,
 'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [paper/'fusion_abstract.tex',paper/'fusion_result.tex',root/'BIRTH_GEOMETRY_RESULTS.csv']}}
(root/'FUSION_RESULT_ARTIFACTS.json').write_text(json.dumps(value,indent=2)+'\n')
print(json.dumps({k:v for k,v in value.items() if k!='files'},indent=2))
