from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    rows=load(ROOT/'refined_delivery/results/geometry_refined/top_results.json');pairs=[]
    for i in [1,2,3]:
        row=rows[i];best=row['top'][0];index=int(row['gallery']['filename'].split('_')[0])
        assert best['geometry_pass'] and best['NCC']>.99
        pairs.append({'template_index':i,'file_sequence_index':index,'source_frame0':best['source_frame0'],'offset_at_stride5':best['source_frame0']-5*index})
    assert {r['offset_at_stride5'] for r in pairs}=={9490}
    endpoints=[]
    for i in [0,4]:
        row=rows[i];index=int(row['gallery']['filename'].split('_')[0]);endpoints.append({'template_index':i,'gallery':row['gallery'],
          'file_sequence_index':index,'predicted_source_frame0':9490+index*5})
    value={'name':'Post-search filename/stride hypothesis with two endpoint checks',
        'created_UTC':datetime.now(timezone.utc).isoformat(),'source_protocol_sha256':sha(ROOT/'protocol/geometry_v1.json'),
        'source_refinement_results_sha256':sha(ROOT/'refined_delivery/results/geometry_refined/top_results.json'),
        'discovery_pairs':pairs,'hypothesis':'For thisone publishedID009 camera1 local sequence only, source_frame0=9490+5*file_sequence_index.',
        'endpoints':endpoints,'sequence_hypothesis_is_not_global_filename_rule':True,
        'geometry_filters_must_remain_unchanged':True,'diagnostic_photometry_for_rejected_transform_allowed':True,
        'identity_reference_promotion_allowed':False,'whole_goal_complete':False}
    path=ROOT/'protocol/endpoint_v1.json';assert not path.exists();path.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'discovery_pairs':pairs,'endpoint_source_frames':[r['predicted_source_frame0'] for r in endpoints],'protocol_sha256':sha(path)}))
if __name__=='__main__':main()
