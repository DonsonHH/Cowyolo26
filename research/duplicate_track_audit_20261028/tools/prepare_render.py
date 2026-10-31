from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
a=load(ROOT/'results/audit.json');cases=[]
for c in a['conditions']:
    episode=max((e for e in a['episodes'] if e['condition']==c['condition']),key=lambda e:(e['pair_frames'],e['maximum_pair_IoU'],-e['first_frame']))
    frame=(episode['first_frame']+episode['last_frame'])//2
    r=next(r for r in a['all_high_overlap_pairs'] if r['condition']==c['condition'] and r['frame']==frame and r['track_IDs']==episode['track_IDs'])
    cases.append({'selection':'longest exactIDpair episode; tie highestmaximumIoU then earlieststart',**r})
special=[{'selection':'known newevent risk',**a['known_case_frame120']},
         {'selection':'geometric counterexample: different uniquelybest publisher IDs and both above .5',
          **next(r for r in a['all_high_overlap_pairs'] if r['condition']=='generic_secondstage_iou' and r['frame']==323)}]
q={'source_video':'/share/home/renly/projects/idcoo_research_20261026/phase2/data/mendeley_counting/extracted/Ground Truth/Toros.mp4',
   'source_sha256':load(ROOT/'protocol/duplicate_v1.json')['source_sha256'],
   'audit_sha256':sha(ROOT/'results/audit.json'),'protocol_sha256':sha(ROOT/'protocol/duplicate_v1.json'),
   'independent_verification_sha256':sha(ROOT/'results/independent_verification.json'),
   'frames':sorted({r['frame'] for r in cases+special}),'all6representatives':cases,'special_cases':special,
   'figure_reduction':'counts exact output metrics and frame timeline, no smoothing or log scales',
   'new_inference':False,'posthoc_cases_not_independent_truth':True}
p=ROOT/'protocol/render_v1.json';assert not p.exists();p.write_text(json.dumps(q,indent=2),encoding='utf-8')
print(json.dumps({'selected_frames':q['frames'],'representatives':6,'special_cases':2,'render_protocol_sha256':sha(p)}))
