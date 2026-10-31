"""Versioned packet intake and scoring after a recorded manual reference review."""
from pathlib import Path
import argparse,csv,hashlib,json,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'evaluation_intake_20261028/tools'))
from inspect_annotation import inspect
from build_catalog import validate_row

def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def digest(data):return hashlib.sha256(data).hexdigest()
def sha(p):return digest(Path(p).read_bytes())
def save(p,v):Path(p).write_text(json.dumps(v,indent=2,ensure_ascii=False),encoding='utf-8')
def protocol_check():
    path=ROOT/'protocol/evaluation_v1.json';p=load(path)
    for item in p['source_files'].values():
        if sha(item['path'])!=item['sha256']:raise ValueError('Frozen validation or matching source changed')
    return p
def catalog_check(path):
    c=load(path);ids=[r['condition_id'] for r in c['conditions']]
    if len(ids)!=len(set(ids)):raise ValueError('Duplicate condition identity')
    for row in c['conditions']:
        if row['source_sha256']!=c['source_sha256'] or row['source_frame_scope']!=c['frame_scope_inclusive'] or row['history_start']!=0:
            raise ValueError('Condition source/scope/history mismatch')
        validate_row(row)
    return c
def stage_annotation(annotation,catalog,output):
    annotation=Path(annotation);catalog=Path(catalog);output=Path(output)
    if output.exists():raise FileExistsError(output)
    protocol_check()
    raw=annotation.read_bytes();value=json.loads(raw.decode('utf-8-sig'));c=catalog_check(catalog)
    inspection=inspect(value)
    if value['source']['sha256']!=c['source_sha256']:raise ValueError('Reference/catalog source mismatch')
    result={'schema_version':'paired-cattle-review-packet-v1','status':'DRAFT_READY_FOR_MANUAL_SOURCE_REVIEW' if not inspection['blocking_findings'] else 'DRAFT_INTAKE_BLOCKED',
       'annotation_sha256':digest(raw),'catalog_sha256':sha(catalog),'source_sha256':c['source_sha256'],
       'frame_scope_inclusive':c['frame_scope_inclusive'],'conditions':len(c['conditions']),
       'evaluation_protocol_sha256':sha(ROOT/'protocol/evaluation_v1.json'),
       'inspection':inspection,'reference_acceptance_record_present':False,'metrics_computed':False,
       'independent_reference_certified_by_software':False,'source_count_accuracy_verified':False}
    output.mkdir(parents=True,exist_ok=False)
    (output/'annotation_original.json').write_bytes(raw);(output/'catalog_snapshot.json').write_bytes(catalog.read_bytes())
    save(output/'inspection.json',inspection);result['inspection_sha256']=sha(output/'inspection.json')
    save(output/'packet.json',result);return result
def metric_function():
    protocol=protocol_check();source=Path(protocol['source_files']['matcher']['path'])
    if sha(source)!=protocol['source_files']['matcher']['sha256']:raise ValueError('Frozen matching source changed')
    sys.path.insert(0,str(ROOT/'deps'));sys.path.insert(0,str(source.parent))
    import scipy
    if scipy.__version__!=protocol['scipy_version']:raise ValueError('Scoring dependency version changed')
    from event_metrics import evaluate_events
    return evaluate_events
def ledger(reference,prediction,metrics):
    rows=[]
    for pair in metrics['pairs']:
        i,j=pair['reference_index'],pair['prediction_index']
        candidates=[k for k,p in enumerate(prediction) if abs(p['time_s']-reference[i]['time_s'])<=2.]
        rows.append({'kind':'matched_correct_direction' if pair['direction_correct'] else 'matched_wrong_direction',
             'reference_event_id':reference[i]['event_id'],'reference_frame':reference[i]['source_frame'],
             'reference_direction':reference[i]['direction'],'prediction_direction':prediction[j]['direction'],
             'prediction_index':j,'prediction_frame':prediction[j]['source_frame'],'prediction_track_ID':prediction[j].get('track_id'),
             'time_error_s':pair['time_error_s'],'all_temporal_candidate_indices':candidates,
             'ambiguous_temporal_candidates':len(candidates)>1})
    for i in metrics['unmatched_reference_indices']:
        rows.append({'kind':'unmatched_reference','reference_event_id':reference[i]['event_id'],'reference_frame':reference[i]['source_frame'],'reference_direction':reference[i]['direction']})
    for j in metrics['unmatched_prediction_indices']:
        rows.append({'kind':'unmatched_prediction','prediction_index':j,'prediction_frame':prediction[j]['source_frame'],
                     'prediction_direction':prediction[j]['direction'],
                     'prediction_track_ID':prediction[j].get('track_id')})
    return rows
def temporal_ambiguity(reference,prediction):
    r_counts=[sum(abs(r['time_s']-p['time_s'])<=2. for p in prediction) for r in reference]
    p_counts=[sum(abs(r['time_s']-p['time_s'])<=2. for r in reference) for p in prediction]
    return {'reference_events_with_multiple_temporal_candidates':sum(n>1 for n in r_counts),
            'predictions_with_multiple_reference_candidates':sum(n>1 for n in p_counts),
            'reference_candidate_counts':r_counts,'prediction_candidate_counts':p_counts,
            'physical_identity_correspondence_established':False,'original_assignment_unchanged':True}
def direction_metrics(reference,prediction,metrics):
    out={}
    for direction in ['A->B','B->A']:
        n=sum(r['direction']==direction for r in reference);m=sum(p['direction']==direction for p in prediction)
        tp=sum(p['direction_correct'] and reference[p['reference_index']]['direction']==direction for p in metrics['pairs'])
        fp=m-tp;fn=n-tp
        out[direction]={'reference_events':n,'predicted_events':m,'TP':tp,'FP':fp,'FN':fn,
                        'precision':tp/m if m else None,'recall':tp/n if n else None,
                        'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None}
    return out
def score_packet(packet_dir,acceptance,output,*,fixture_mode=False):
    packet_dir=Path(packet_dir);acceptance=Path(acceptance);output=Path(output)
    if output.exists():raise FileExistsError(output)
    p=load(packet_dir/'packet.json');value=load(packet_dir/'annotation_original.json');receipt=load(acceptance)
    protocol_check()
    if p.get('evaluation_protocol_sha256')!=sha(ROOT/'protocol/evaluation_v1.json'):raise ValueError('Evaluation protocol changed since packet intake')
    if sha(packet_dir/'annotation_original.json')!=p['annotation_sha256'] or sha(packet_dir/'catalog_snapshot.json')!=p['catalog_sha256']:
        raise ValueError('Frozen packet input changed')
    inspection=inspect(value);blocks=list(inspection['blocking_findings'])
    if fixture_mode:
        if value.get('qa_only') is not True or receipt.get('fixture_only') is not True:raise ValueError('Fixture mode requires explicit software-only markers')
        blocks=[b for b in blocks if b!='KNOWN_QA_FIXTURE_NOT_HUMAN_REFERENCE']
    elif value.get('qa_only') is True or receipt.get('fixture_only') is True:
        raise ValueError('Software fixture cannot become accepted reference')
    if blocks:raise ValueError('Unresolved intake findings: '+', '.join(blocks))
    if receipt.get('schema_version')!='cattle-reference-acceptance-v1':raise ValueError('Manual review record required')
    if receipt.get('packet_sha256')!=sha(packet_dir/'packet.json') or receipt.get('annotation_sha256')!=p['annotation_sha256'] or receipt.get('source_sha256')!=p['source_sha256']:
        raise ValueError('Manual review record does not bind this packet')
    for key in ['human_provenance_review_complete','native_source_review_complete','ambiguities_resolved','reviewer_independence_checked']:
        if receipt.get(key) is not True:raise ValueError('Incomplete manual review: '+key)
    if receipt.get('frame_scope_inclusive')!=p['frame_scope_inclusive']:raise ValueError('Manual review scope mismatch')
    log=Path(receipt.get('review_log_path',''))
    if not log.is_file() or sha(log)!=receipt.get('review_log_sha256'):raise ValueError('Manual source/provenance review log missing or changed')
    reference=inspection['complete_scoped_events_for_later_matching']
    checked=receipt.get('checked_native_frames',[])
    if not isinstance(checked,list) or any(type(f) is not int or not 0<=f<=14007 for f in checked):
        raise ValueError('Invalid checked native frame record')
    needed={*p['frame_scope_inclusive'],*[r['source_frame'] for r in reference]}
    if not needed<=set(checked):raise ValueError('Native event frames and interval boundaries not recorded as checked')
    c=catalog_check(packet_dir/'catalog_snapshot.json');evaluate=metric_function();results=[]
    for row in c['conditions']:
        prediction=load(row['events_path']);metrics=evaluate(reference,prediction,tolerance_s=2.)
        results.append({'condition_id':row['condition_id'],'seed':row['seed'],'metrics':metrics,
                        'per_direction':direction_metrics(reference,prediction,metrics),
                        'event_ledger':ledger(reference,prediction,metrics),
                        'temporal_ambiguity':temporal_ambiguity(reference,prediction),'events_sha256':row['events_sha256']})
    byid={r['condition_id']:r for r in results};paired=[]
    for pair in c.get('paired_comparisons',[]):
        a=byid[pair['baseline_condition_id']]['metrics'];b=byid[pair['candidate_condition_id']]['metrics']
        paired.append({**pair,'TP_change':b['TP']-a['TP'],'FP_change':b['FP']-a['FP'],'FN_change':b['FN']-a['FN'],
                       'wrong_direction_change':b['wrong_direction_matches']-a['wrong_direction_matches']})
    result={'status':'SOFTWARE_FIXTURE_SCORE_NOT_RESEARCH_RESULT' if fixture_mode else 'SCORED_AGAINST_RECORDED_MANUALLY_ACCEPTED_REFERENCE',
       'fixture_only':fixture_mode,'packet_sha256':sha(packet_dir/'packet.json'),'acceptance_sha256':sha(acceptance),
       'catalog_sha256':p['catalog_sha256'],'annotation_sha256':p['annotation_sha256'],'reference_events':len(reference),
       'evaluation_protocol_sha256':p['evaluation_protocol_sha256'],
       'conditions':results,'paired_changes':paired,'matching_tolerance_s':2.,
       'original_matching_source_sha256':load(ROOT/'protocol/evaluation_v1.json')['source_files']['matcher']['sha256'],
       'blinding_declaration':value['blinding'],'manual_review_record_validated':True,
       'independent_human_reference_certified_by_software':False,
       'source_count_metrics_computed_against_manual_review_record':not fixture_mode,
       'source_is_independent_test_dataset':False,'physical_individual_matching_not_proved_by_time_assignment':True,
       'new_inference':False,'board_execution':False}
    output.mkdir(parents=True,exist_ok=False);save(output/'scores.json',result)
    fields=['condition_id','seed','reference_events','predicted_events','TP','FP','FN','wrong_direction_matches','precision','recall','f1']
    with (output/'scores.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for r in results:writer.writerow({k:r[k] if k in ['condition_id','seed'] else r['metrics'][k] for k in fields})
    columns=['condition_id','seed','direction','reference_events','predicted_events','TP','FP','FN','precision','recall','f1']
    with (output/'direction_scores.csv').open('w',newline='',encoding='utf-8-sig') as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader()
        for r in results:
            for direction,values in r['per_direction'].items():
                writer.writerow({'condition_id':r['condition_id'],'seed':r['seed'],'direction':direction,**values})
    return result
def main():
    parser=argparse.ArgumentParser();sub=parser.add_subparsers(dest='action',required=True)
    a=sub.add_parser('stage');a.add_argument('annotation',type=Path);a.add_argument('--catalog',type=Path,default=ROOT/'results/frozen_prediction_catalog_v2.json');a.add_argument('--output',type=Path,required=True)
    a=sub.add_parser('score');a.add_argument('packet',type=Path);a.add_argument('--acceptance',type=Path,required=True);a.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.action=='stage':
        r=stage_annotation(args.annotation,args.catalog,args.output);print(json.dumps({k:r[k] for k in ['status','conditions','metrics_computed','source_count_accuracy_verified']}));return 2 if r['inspection']['blocking_findings'] else 0
    r=score_packet(args.packet,args.acceptance,args.output);print(json.dumps({'status':r['status'],'conditions':len(r['conditions']),'reference_events':r['reference_events']}));return 0
if __name__=='__main__':raise SystemExit(main())
