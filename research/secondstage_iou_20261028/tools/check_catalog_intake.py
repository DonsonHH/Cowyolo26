from pathlib import Path
import csv,hashlib,json,sys,tempfile
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(PROJECT/'paired_event_intake_20261028/tools'))
from intake_pipeline import catalog_check,stage_annotation,score_packet
from test_pipeline import draft,receipt
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    target=ROOT/'results/catalog_intake_verification.json';assert not target.exists()
    path=ROOT/'results/frozen_prediction_catalog_v3.json';c=catalog_check(path)
    old=load(c['previous_catalog_path']);assert c['conditions'][:23]==old['conditions'] and len(c['conditions'])==26
    assert len(c['paired_comparisons'])==6
    index={r['condition_id']:r for r in c['conditions']};files=set()
    for row in c['conditions']:
        for field in ['events','summary','protocol']:
            f=Path(row[field+'_path']);assert sha(f)==row[field+'_sha256'];files.add(str(f))
    for pair in c['paired_comparisons'][3:]:
        a=index[pair['baseline_condition_id']];b=index[pair['candidate_condition_id']]
        assert a['checkpoint_sha256']==b['checkpoint_sha256'] and a['pipeline_contract_sha256']!=b['pipeline_contract_sha256']
        new=load(b['events_path']);previous=load(a['events_path'])
        norm=lambda rows:[{k:v for k,v in e.items() if k!='track_id'} for e in rows]
        assert norm(new)==norm(previous)  # still distinct algorithms, retained as separate conditions
    qa=ROOT/'qa_fixtures';qa.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=qa) as temporary:
        tmp=Path(temporary);annotation=tmp/'SOFTWARE_ONLY.json';annotation.write_text(json.dumps(draft()),encoding='utf-8')
        packet=tmp/'packet';result=stage_annotation(annotation,path,packet)
        assert result['conditions']==26 and not result['metrics_computed']
        approval=tmp/'SOFTWARE_ONLY_RECEIPT.json';approval.write_text(json.dumps(receipt(packet,tmp)),encoding='utf-8')
        scores=score_packet(packet,approval,tmp/'software_scores',fixture_mode=True)
        assert scores['fixture_only'] and not scores['source_count_metrics_computed_against_manual_review_record']
        assert len(scores['conditions'])==26 and len(scores['paired_changes'])==6
        with (tmp/'software_scores/direction_scores.csv').open(encoding='utf-8-sig',newline='') as f:assert len(list(csv.DictReader(f)))==52
        try:score_packet(packet,approval,tmp/'must_not_be_created')
        except ValueError:pass
        else:raise AssertionError('Software fixture admitted as real reference')
        assert not (tmp/'must_not_be_created').exists()
    source=PROJECT/'phase3_diagnosis_20261026/results/qa_fixture_annotation.json';before=sha(source)
    packet=ROOT/'results/known_QA_26_conditions_blocked';blocked=stage_annotation(source,path,packet)
    assert blocked['status']=='DRAFT_INTAKE_BLOCKED' and not blocked['metrics_computed'] and sha(source)==before
    report={'status':'CURRENT26_CATALOG_AND_SCORING_INTAKE_CHECKS_PASS_WITHOUT_REAL_REFERENCE',
      'catalog_sha256':sha(path),'conditions':26,'preserved_records':23,'pairs':6,'distinct_source_artifact_files':len(files),
      'indexed_prediction_events':sum(r['predicted_events'] for r in c['conditions']),
      'software_fixture_scored_conditions':26,'software_fixture_direction_rows':52,
      'software_fixture_refused_as_real_reference':True,'known_QA_intake_blocked':True,'known_QA_input_preserved':True,
      'real_reference_received':False,'source_accuracy_computed':False,'new_inference':False,'board_execution':False,'whole_goal_complete':False}
    target.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report))
if __name__=='__main__':main()
