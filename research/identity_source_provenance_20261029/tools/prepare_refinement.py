from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=load(ROOT/'protocol/geometry_v1.json');rows=load(ROOT/'geometry_delivery/results/geometry_coarse/top_results.json')
    assert load(ROOT/'geometry_delivery/results/geometry_coarse/controls.json')['passed'] is True
    templates=[]
    for row in rows:
        frame=row['top'][0]['source_frame0'];ticks=list(range(max(0,frame-25),min(10873,frame+25)+1,5))
        assert all(f%5==0 for f in ticks)
        templates.append({'template_index':row['template_index'],'gallery':row['gallery'],'coarse_best_frame0':frame,'refine_frame0s':ticks})
    value={'name':'Predetermined every-template +/-25frame5Hz refinement of geometric provenance candidates',
      'created_UTC':datetime.now(timezone.utc).isoformat(),'coarse_protocol_sha256':sha(ROOT/'protocol/geometry_v1.json'),
      'coarse_results_sha256':sha(ROOT/'geometry_delivery/results/geometry_coarse/top_results.json'),
      'source_search_implementation_sha256':sha(ROOT/'tools/geometry_probe.py'),
      'templates':templates,'unique_refinement_frames':sorted({f for t in templates for f in t['refine_frame0s']}),
      'per_template_comparisons':sum(len(t['refine_frame0s']) for t in templates),
      'review_artifacts':'For every template save best source native JPEG, source rewarp PNG and all metrics, even if no geometry candidate.',
      'source_mapping_status':'geometric_source_candidate_only','identity_promotion_allowed':False,
      'new_identity_model_forwards':0,'new_training_updates':0,'whole_goal_complete':False}
    out=ROOT/'protocol/refinement_v1.json';assert not out.exists();out.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'templates':len(templates),'source_frames':len(value['unique_refinement_frames']),
                      'comparisons':value['per_template_comparisons'],'protocol_sha256':sha(out)}))
if __name__=='__main__':main()
