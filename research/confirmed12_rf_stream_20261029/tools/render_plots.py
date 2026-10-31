from pathlib import Path
from collections import Counter
import hashlib,json,os,socket,tarfile
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/confirmed12_rf_stream_20261029')
def load(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n')
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    q=load(ROOT/'protocol/plots_v1.json');p=load(ROOT/'protocol/stream_v1.json');s=load(ROOT/'results/summary.json')
    assert sha(ROOT/'results/summary.json')==q['source_summary_sha256'] and sha(ROOT/'results/independent_verification.json')==q['independent_verification_sha256']
    out=ROOT/'results/plots';out.mkdir(exist_ok=False)
    labels={'S00_missing':'S00  No RF reads','S01_single':'S01  One code per event','S02_duplicates':'S02  Repeated same code',
        'S03_delay_inside':'S03  Delayed within cutoff','S04_late':'S04  After-cutoff receipt','S05_conflict':'S05  Two-code conflict',
        'S06_invalid':'S06  Invalid / wrong lane / clock','S07_wrong_single':'S07  Sole wrong code (control)',
        'S08_unregistered':'S08  Unregistered code','S09_missing_snapshot':'S09  Missing photo interface',
        'P00_burst_capacity':'P00  Burst admission barrier','P01_expired':'P01  Expired waiting barrier'}
    palette=[('RF_UNIQUE_CANDIDATE_UNVERIFIED','RF candidate (unverified)','#2a9d8f'),
             ('VISUAL_THRESHOLD_CANDIDATE_UNVERIFIED','Visual threshold crossed (unverified)','#e9b44c'),
             ('VISUAL_ALL_CONDITIONS_REJECTED','Visual query: all5 reject','#4c78a8'),
             ('UNRESOLVED_NO_SNAPSHOT','No snapshot supplied','#9467bd'),
             ('UNRESOLVED_QUEUE_CAPACITY','Queue capacity rejected','#9aa0a6'),
             ('UNRESOLVED_EXPIRED_WAITING','Expired before query','#d95f59')]
    fig,ax=plt.subplots(figsize=(13.6,8.6));left=[0]*12;y=list(range(12))
    for status,title,color in palette:
        values=[case['terminal_status_counts'].get(status,0) for case in s['cases']]
        ax.barh(y,values,left=left,color=color,label=title,height=.65,edgecolor='white',linewidth=.5)
        for i,n in enumerate(values):
            if n:ax.text(left[i]+n/2,i,str(n),ha='center',va='center',fontsize=10,color='black' if status in ['VISUAL_THRESHOLD_CANDIDATE_UNVERIFIED','UNRESOLVED_QUEUE_CAPACITY'] else 'white')
        left=[a+b for a,b in zip(left,values)]
    assert left==[12]*12
    ax.set_yticks(y,[labels[c['case_id']] for c in s['cases']]);ax.invert_yaxis();ax.set_xlim(0,12);ax.set_xticks(range(13))
    ax.set_xlabel('Software event ledgers (the same12 source events reused in every case)')
    ax.set_title('Controlled RF ingress and actual CPU Re-ID query states',loc='left',fontsize=15,pad=22)
    ax.axhline(9.5,color='#4b5563',linestyle='--',linewidth=1)
    ax.spines[['top','right','left']].set_visible(False);ax.grid(axis='x',alpha=.15);ax.set_axisbelow(True)
    ax.legend(loc='upper center',bbox_to_anchor=(.5,-.11),ncol=2,frameon=False,fontsize=9)
    fig.text(.02,.015,'Synthetic RF and deliberate pressure controls; counts are not correct cow identifications or field error rates.',fontsize=9)
    fig.subplots_adjust(left=.29,right=.98,top=.9,bottom=.23)
    for ext in ['png','svg']:fig.savefig(out/('controlled_outcomes.'+ext),dpi=150)
    plt.close(fig)
    trace=load(ROOT/'results/cases'/q['case_id_for_timeline']/'stream_linker_trace.json')
    captures=load(ROOT/'input/runtime_captures.json');by_event={e['event_id']:e for e in trace['outputs']}
    slots={e['event_id']:e for e in trace['slots'] if e['event_id'] is not None}
    fig,(ax,detail)=plt.subplots(2,1,figsize=(13.6,9.6),gridspec_kw={'height_ratios':[2.25,1]})
    interval_data=[]
    for i,capture in enumerate(captures):
        identity=capture['event_id'];slot=slots[identity];decision=by_event[identity];color='#2a9d8f' if decision['rf_status']=='RF_UNIQUE_CANDIDATE' else '#e9b44c'
        a,b=slot['opened_frame0']/25,slot['closed_frame0']/25;d=decision['decision_frame0']/25
        ax.plot([a,b],[i,i],color=color,linewidth=6,solid_capstyle='butt')
        ax.plot([b,d],[i,i],color='#6b7280',linestyle=':',linewidth=1.8)
        ax.plot(b,i,'o',color='black',markersize=4);ax.plot((capture['frame0']-5)/25,i,'v',color='#111827',markersize=5)
        interval_data.append({'event_id':identity,'track_id':slot['track_id'],'opened_frame0':slot['opened_frame0'],
            'closed_frame0':slot['closed_frame0'],'decision_frame0':decision['decision_frame0'],'injected_read_capture_frame0':capture['frame0']-5,
            'RF_status':decision['rf_status']})
    ax.set_yticks(range(12),[f'E{i+1:03d} / track{c["track_id"]}' for i,c in enumerate(captures)])
    ax.invert_yaxis();ax.set_xlim(355,435.5);ax.set_xlabel('Original source time (s), frame0 /25')
    ax.set_title('One injected code per event: five unique candidates, seven shared-window decisions',loc='left',fontsize=13)
    ax.grid(axis='x',alpha=.2);ax.spines[['top','right']].set_visible(False)
    context=next(r for r in trace['audit'] if r['kind']=='RF_CAUSAL_CONTEXT' and r['event_id']==q['focus_event_id'])
    read=next(r for r in context['received_reads'] if r['read_id']=='S01_single_read007_primary')
    matching=[w for w in context['passages'] if w['reader']==read['reader'] and w['opened']<=read['captured']<=w['closed']]
    assert len(matching)==2 and context['frame0']==9480 and read['captured']==9460
    pending=next(w for w in matching if w['closed']>context['frame0']);closed=next(w for w in matching if w['closed']<=context['frame0'])
    for y0,w,title,color in [(1,closed,'E007 / track96 (counted)', '#2a9d8f'),(0,pending,'Track98 still open (no completed event yet)', '#e9b44c')]:
        end=min(w['closed'],context['frame0']);detail.plot([w['opened'],end],[y0,y0],color=color,linewidth=9,solid_capstyle='butt')
        detail.plot(read['captured'],y0,'v',color='#111827',markersize=9)
        detail.text(w['opened'],y0+.15,title,fontsize=10)
    detail.axvline(context['frame0'],color='#d95f59',linestyle='--',linewidth=1.5)
    detail.text(context['frame0']-1,.5,'RF decision\nframe9480',ha='right',va='center',fontsize=9,color='#b53c38')
    detail.set_xlim(9375,9498);detail.set_ylim(-.3,1.5);detail.set_yticks([]);detail.set_xlabel('Original source frame0')
    detail.set_title('At frame9480, the read captured at9460 fits both visible reservations',loc='left',fontsize=12)
    detail.spines[['top','right','left']].set_visible(False);detail.grid(axis='x',alpha=.2)
    fig.text(.02,.028,'Top: retrospectively labelled counted reservations;13 additional visual reservations are logged separately. Dots: count close; triangles: synthetic read capture.',fontsize=8.4)
    fig.text(.02,.011,'Bottom: only information available at the decision. Open track98 was a blocker before its later count; future event labels were not supplied to the resolver.',fontsize=8.4)
    fig.subplots_adjust(left=.18,right=.98,top=.94,bottom=.11,hspace=.58)
    for ext in ['png','svg']:fig.savefig(out/('shared_window_timeline.'+ext),dpi=150)
    plt.close(fig)
    plotdata={'case_states':[{'case_id':c['case_id'],'terminal_status_counts':c['terminal_status_counts']} for c in s['cases']],
        'counted_intervals':interval_data,'focus_context':context,'focus_read':read,'focus_matching_passages':matching,
        'uncounted_visual_reservations':sum(w['event_id'] is None for w in trace['slots']),
        'source_summary_sha256':sha(ROOT/'results/summary.json'),'source_trace_sha256':sha(ROOT/'results/cases/S01_single/stream_linker_trace.json')}
    save(out/'plot_data.json',plotdata)
    files=[{'path':file.relative_to(ROOT).as_posix(),'sha256':sha(file),'bytes':file.stat().st_size} for file in sorted(out.iterdir()) if file.is_file()]
    record={'status':'RF_SOFTWARE_STATE_AND_CAUSAL_SHARED_WINDOW_FIGURES_RENDERED','job_id':os.environ['SLURM_JOB_ID'],
            'plots_protocol_sha256':sha(ROOT/'protocol/plots_v1.json'),'files':files,'actual_visual_review_required':True,
            'source_cow_identity_accuracy':None,'RF_hardware_connected':False,'whole_goal_complete':False}
    save(out/'summary.json',record)
    allfiles=[ROOT/'protocol/plots_v1.json',ROOT/'tools/render_plots.py',*[file for file in out.iterdir() if file.is_file()]]
    manifest=[{'file':file.relative_to(ROOT).as_posix(),'bytes':file.stat().st_size,'sha256':sha(file)} for file in allfiles]
    save(ROOT/'plot_delivery_manifest.json',{'files':manifest});archive=ROOT/'plot_delivery.tar.gz'
    with tarfile.open(archive,'w:gz') as tf:
        for row in manifest:tf.add(ROOT/row['file'],arcname=row['file'])
        tf.add(ROOT/'plot_delivery_manifest.json',arcname='plot_delivery_manifest.json')
    print(json.dumps({'files':len(manifest)+1,'archive_bytes':archive.stat().st_size,'archive_sha256':sha(archive)}),flush=True)
if __name__=='__main__':main()
