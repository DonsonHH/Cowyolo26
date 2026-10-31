from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    old=load(PROJECT/'video_chain_20261026/protocol/video_chain_v1.json')
    accepted=load(PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json')
    assert accepted['human_total']==accepted['predicted_down']==12 and accepted['condition_id']=='confirmation_handoff_20261028/seed26'
    source=PROJECT/'firststage_iou_regression_20261029/delivery/results/original_seed26__original_fused'
    previous=load(source/'summary.json');assert previous['baseline_checks']['both_counter_event_paths_exact'] is True
    actual=load(source/'handoff_events_all_history.json');truth=load(Path(accepted['source_event_record']['events_path']))
    assert len(actual)==12 and actual==[{**{k:v for k,v in e.items() if k!='source_frame'},'frame0':e['source_frame']} for e in truth]
    inputs=ROOT/'input';inputs.mkdir(exist_ok=False);protocol=ROOT/'protocol';protocol.mkdir(exist_ok=False)
    for name,src in [('snapshot_bank.py',PROJECT/'video_chain_20261026/tools/snapshot_bank.py'),
                     ('zone_counter.py',PROJECT/'confirmation_handoff_20261028/input/zone_counter.py'),
                     ('confirmation_counter.py',PROJECT/'confirmation_handoff_20261028/tools/confirmation_counter.py'),
                     ('test_snapshot_bank.py',PROJECT/'video_chain_20261026/tools/test_snapshot_bank.py')]:
        (inputs/name).write_bytes(src.read_bytes())
    worker=PROJECT/'video_chain_20261026/tools/identity_worker.py';code=worker.read_text(encoding='utf-8')
    marker="        result_queue.put({'kind':'ready'"
    assert code.count(marker)==1
    injection='''        export_path=Path(protocol['identity_gallery_export_path'])
        assert not export_path.exists()
        export_path.write_text(json.dumps({'entries':entries,'labels':labels,
            'conditions':{name:{'features':vectors.tolist(),'dimension':int(vectors.shape[1])} for name,vectors in gallery.items()},
            'feature_index_sha256':protocol['identity']['feature_index_sha256'],
            'models_and_thresholds':protocol['identity']['conditions']},indent=2)+'\\n')
'''
    code=code.replace(marker,injection+marker)
    marker="                with Image.open(project/'identity_training'/row['relative_path']) as im:"
    assert code.count(marker)==1
    code=code.replace(marker,"                assert hashlib.sha256((project/'identity_training'/row['relative_path']).read_bytes()).hexdigest()==row['sha256']\n"+marker)
    marker="'feature_norm':float(np.linalg.norm(feature)),'feature_vector':feature.tolist(),"
    assert code.count(marker)==1
    replacement=marker+"\n                                    'query_tensor_sha256':hashlib.sha256(tensor.detach().contiguous().cpu().numpy().tobytes()).hexdigest(),\n                                    'query_tensor_shape':list(tensor.shape),'gallery_image_cosines':similarities.tolist(),\n                                    'identity_scores':[{'anonymous_id':label,'score':score} for label,score in zip(labels,scores)],"
    code=code.replace(marker,replacement)
    worker_out=ROOT/'tools/identity_worker.py';worker_out.write_bytes(code.encode())
    feature_index=PROJECT/'identity_training_20261026/delivery/results/study/feature_index.json'
    study=PROJECT/'identity_training_20261026/delivery/results/study/summary.json'
    assert sha(feature_index)==old['identity']['feature_index_sha256'] and sha(study)==old['identity']['study_summary_sha256']
    gallery=load(feature_index)['evaluation_gallery'];assert len(gallery)==30 and len({r['identity'] for r in gallery})==6
    (inputs/'gallery_source_index.json').write_text(json.dumps(gallery,indent=2)+'\n',encoding='utf-8')
    cache_files=[]
    for name in ['post_tracker_boxes.csv','observations.json','handoff_events_all_history.json','summary.json']:
        cache_files.append({'name':name,'path':REMOTE+'/firststage_iou_regression_20261029/results/original_seed26__original_fused/'+name,
                            'local':str((source/name).resolve()),'sha256':sha(source/name),'bytes':(source/name).stat().st_size})
    proto={'name':'Accepted12-event source replay with native capture, bounded mock-RF queue and actual frozen CPU ReID',
      'created_UTC':datetime.now(timezone.utc).isoformat(),'source_video':REMOTE+'/'+old['source_video'],
      'source_video_sha256':old['source_video_sha256'],'width':2560,'height':1440,'fps':25,'stride':5,
      'decode_end_frame0_exclusive':10874,'export_event_scope_frame0_halfopen':[8912,10874],
      'frozen_development_candidate_sha256':sha(PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json'),
      'human_confirmation_sha256':sha(PROJECT/'human_count_confirmation_20261028/evidence/user_confirmation.json'),
      'expected_events':actual,'cache_files':cache_files,'detector_checkpoint_sha256':accepted['checkpoint_sha256'],
      'counter':{'lower':.4,'upper':.6,'stable_samples':3,'maximum_gap_s':2.},'counter_variant':'original_association_confirmation_handoff',
      'snapshots':old['snapshots'],'rf_window_source_seconds':.5,'rf_mode':'EXPLICIT_MOCK_MISSING_NO_READER',
      'rf_processing':'First5Hz processing tick at or after source event time plus0.5s; usually0.6source seconds later',
      'worker_queue_capacity':4,'worker_result_capacity':16,'worker_deadline_wall_seconds':30,'worker_drain_wall_seconds':30,
      'worker_ready_timeout_seconds':120,'identity':old['identity'],
      'upstream_identity_worker_sha256':sha(worker),'identity_worker_audit_changes_only':['gallery_source_byte_hash_validation','export_actual_gallery_vectors','save_input_tensor_hash_and_all_scores'],
      'identity_worker_sha256':sha(worker_out),'body_transform_sha256':sha(PROJECT/'identity_training_20261026/tools/training_primitives.py'),
      'input_module_sha256':{f.name:sha(f) for f in inputs.iterdir() if f.is_file()},
      'selection_cannot_read_identity_scores':True,'source_identity_ground_truth_available':False,
      'verified_identity_must_remain_false':True,'new_detector_forwards':0,'new_training_updates':0,
      'runtime_scope':'Server CPU functional replay from frozen native detections;5model comparison, not realtime/PYNQ performance.',
      'FPGA_execution_verified':False,'whole_goal_complete':False}
    target=protocol/'chain_v1.json';target.write_text(json.dumps(proto,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'protocol_sha256':sha(target),'accepted_events':len(actual),'models':len(proto['identity']['conditions']),
                      'gallery_images':30,'expected_query_forwards_if_all_complete':60,'new_detector_forwards':0}))
if __name__=='__main__':main()
