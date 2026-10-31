from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
def main():
    stage=PROJECT/'external_method_regression_20261028';summary=stage/'delivery/results/summary.json'
    previous=load(stage/'protocol/regression_v1.json');s=load(summary)
    out=ROOT/'protocol/duplicate_v1.json';assert not out.exists();out.parent.mkdir(parents=True,exist_ok=True)
    inputs=[summary,stage/'input/publisher_gt_original.txt',stage/'results/overlap_case_review.json',stage/'protocol/regression_v1.json']
    conditions=[]
    for c in s['conditions']:
        folder=stage/'delivery/results'/c['name'];raw=stage/'delivery/original_cache'/c['model']/'raw_detector_boxes.csv'
        files=[folder/'post_tracker_boxes.csv',folder/'confirmed_only_events.json',folder/'handoff_events.json',folder/'summary.json',raw]
        conditions.append({'name':c['name'],'model':c['model'],'variant':c['variant'],
            'files':{f.name:{'path':str(f),'sha256':sha(f),'bytes':f.stat().st_size} for f in files}})
    protocol={'name':'Read-only simultaneous high-overlap track redundancy audit of all fixed Toros regression runs',
      'created_UTC':datetime.now(timezone.utc).isoformat(),'posthoc_development_diagnosis':True,
      'previous_summary_sha256':sha(summary),'source_sha256':previous['source_sha256'],
      'frames_inclusive':[0,478],'fps':30,'width':1920,'height':1080,'perpendicular_ROI_y':[.1,.95],
      'conditions':conditions,'input_files':[{'path':str(f),'sha256':sha(f),'bytes':f.stat().st_size} for f in inputs],
      'high_overlap_pair_IoU_threshold':.5,'threshold_selection':'Fixed geometric diagnostic threshold, no count optimization; reuse prior GT .5/.3 sensitivity',
      'GT_primary_IoU':.5,'GT_sensitivity_IoU':.3,
      'reference_support_rule':'Both predictions have unique highest-IoU clipped publisher box with sameID and IoU>=threshold; this geometric support not independent identity certification',
      'pair_rule':'Each unordered pair of different confirmed predicted IDs inside fixed perpendicular ROI, one per frame, IoU>=.5',
      'raw_pair_rule':'Same ROI and overlap rule on raw detections, no ID requirement; links use distinct raw rows at exact confidence and xyxy IoU>=.9',
      'raw_link_IoU_threshold':.9,'raw_link_confidence_tolerance':1e-7,
      'episode_rule':'Consecutive sourceframes for exact same unordered predictedIDpair; every length retained, no minimal duration filter',
      'reference_tie_rule':'Within1e-12 of best IoU is ambiguous, do not assign unique publisher identity',
      'report_all_conditions_and_missed_GT_support':True,
      'main_questions':['How many highoverlap pairs existed before/after each fixedtracker change?',
                        'Are frame120 twoIDs a oneoff or part of a longer overlappingID episode?',
                        'Are pair boxes already duplicated in rawdetector output?',
                        'Do both IDs emit events in the same geometric episode?'],
      'no_predictions_changed_or_parameters_tuned':True,'new_detector_forwards':0,'training_updates':0,
      'new_independent_reference_received':False,'FPGA_execution_verified':False,'whole_goal_complete':False}
    assert len(conditions)==6
    out.write_text(json.dumps(protocol,indent=2),encoding='utf-8');print(json.dumps({'protocol_sha256':sha(out),'conditions':6,'fixed_pair_threshold':.5}))
if __name__=='__main__':main()
