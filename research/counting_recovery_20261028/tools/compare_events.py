"""Compare two prediction lists; this is not ground-truth scoring."""
from pathlib import Path
from functools import lru_cache
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(path):return json.loads(Path(path).read_text(encoding='utf-8'))
def main():
    source=ROOT/'delivery/results';summary=load(source/'replay_v2/summary.json')
    extension=load(source/'full640_confirmation/summary.json')
    allrows=summary['conditions']+extension['conditions'];comparisons=[]
    for seed in [26,27,28]:
        old_path=PROJECT/f'orientation_video_20261027/delivery/results/inference/clockwise90_seed{seed}/source_events.json'
        old=load(old_path);newpath=source/f'full640_confirmation/full640_5hz_seed{seed}/source_events.json'
        if seed==26:newpath=source/f'replay_v2/full640_5hz_seed{seed}/source_events.json'
        new=load(newpath)
        @lru_cache(None)
        def solve(j,mask):
            if j==len(new):return 0,0.,()
            best=solve(j+1,mask)
            for i,event in enumerate(old):
                delta=abs(event['time_s']-new[j]['time_s'])
                if mask&(1<<i) or delta>2:continue
                n,err,pairs=solve(j+1,mask|(1<<i));candidate=n+1,err+delta,((i,j),)+pairs
                if (candidate[0],-candidate[1])>(best[0],-best[1]):best=candidate
            return best
        count,error,pairs=solve(0,0)
        used_old={i for i,j in pairs};used_new={j for i,j in pairs}
        comparisons.append({'seed':seed,'old_predictions':len(old),'full640_predictions':len(new),
            'prediction_time_pairs_within_2seconds':count,'direction_agrees_in_pairs':all(old[i]['direction']==new[j]['direction'] for i,j in pairs),
            'old_only_predictions':[r for i,r in enumerate(old) if i not in used_old],
            'new_only_predictions':[r for j,r in enumerate(new) if j not in used_new],
            'pairs':[{'old_frame':old[i]['source_frame'],'new_frame':new[j]['source_frame'],'time_error_s':abs(old[i]['time_s']-new[j]['time_s'])} for i,j in pairs],
            'these_are_not_TP_FP_FN_against_truth':True})
    target=ROOT/'results/old_new_event_comparison.json';assert not target.exists()
    target.write_text(json.dumps({'comparisons':comparisons,'independent_accuracy':None},indent=2),encoding='utf-8')
    print(json.dumps({'comparisons':comparisons}))
if __name__=='__main__':main()
