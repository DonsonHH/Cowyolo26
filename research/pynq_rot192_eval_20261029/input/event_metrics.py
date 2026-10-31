"""Event assignment and directional counts, independent from detector code."""
import numpy as np
from scipy.optimize import linear_sum_assignment

def evaluate_events(reference,prediction,tolerance_s=2.):
    if tolerance_s<=0:raise ValueError('Positive tolerance required')
    n,m=len(reference),len(prediction);pairs=[]
    if n and m:
        penalty=(n+m+1)*(tolerance_s+1)
        cost=np.full((n+m,n+m),penalty*100,dtype=float)
        cost[:n,m:]=penalty;cost[n:,:m]=penalty;cost[n:,m:]=0
        for i,r in enumerate(reference):
            for j,p in enumerate(prediction):
                error=abs(float(r['time_s'])-float(p['time_s']))
                if error<=tolerance_s:cost[i,j]=error
        ii,jj=linear_sum_assignment(cost)
        for i,j in zip(ii,jj):
            if i<n and j<m and cost[i,j]<=tolerance_s:
                pairs.append({'reference_index':int(i),'prediction_index':int(j),'time_error_s':float(cost[i,j]),'direction_correct':reference[i]['direction']==prediction[j]['direction']})
    matches=len(pairs);correct=sum(p['direction_correct'] for p in pairs);direction_errors=matches-correct
    tp=correct;fp=m-correct;fn=n-correct
    precision=tp/(tp+fp) if tp+fp else None;recall=tp/(tp+fn) if tp+fn else None
    f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None
    counts={d:{'reference':sum(r['direction']==d for r in reference),'prediction':sum(p['direction']==d for p in prediction)} for d in ['A->B','B->A']}
    return {'reference_events':n,'predicted_events':m,'temporally_matched':matches,'correct_direction_matches':correct,'wrong_direction_matches':direction_errors,'TP':tp,'FP':fp,'FN':fn,'precision':precision,'recall':recall,'f1':f1,'direction_accuracy_given_temporal_match':correct/matches if matches else None,'counts':counts,'mean_absolute_direction_count_error':sum(abs(v['reference']-v['prediction']) for v in counts.values())/2,'matching_tolerance_s':tolerance_s,'pairs':pairs,'unmatched_reference_indices':[i for i in range(n) if i not in {p['reference_index'] for p in pairs}],'unmatched_prediction_indices':[j for j in range(m) if j not in {p['prediction_index'] for p in pairs}]}
