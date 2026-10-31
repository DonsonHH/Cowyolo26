from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,gzip,csv,ast
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def gzsave(p,v):
    assert not p.exists()
    with gzip.GzipFile(filename=str(p),mode='wb',mtime=0) as f:f.write(json.dumps(v,separators=(',',':')).encode())
for name in ['input','protocol','results','logs','evidence']:(ROOT/name).mkdir(exist_ok=True)
port=load(PROJECT/'pynq_frontend_port_20261029/regression_v1.json');videos=load(PROJECT/'pynq_mosaic192_eval_20261030/protocol/eval_v1.json')['videos']
caches=[]
for i,r in enumerate(port['caches']):
    scene='toros' if r['scene']=='toros' else 'original';full=next(v for v in videos if v['name']==scene)
    caches.append({**r,'id':'prior'+str(i).zfill(3),'label':r['mode']+'_'+r['condition'],'kind':'gzip','board_reference':False,
        'windows':[{'name':'activity','start':full['scope_start_frame0'],'end':full['scope_end_exclusive']}],
        'reference_events':full.get('reference_events'),'formal_event_scoring_allowed':scene=='toros','human_total':12 if scene=='original' else None})
for label,base,board in [('old_O8',PROJECT/'pynq_rot192_eval_20261029/board_delivery/results_v2',True),
    ('new_O8',PROJECT/'pynq_mosaic192_eval_20261030/board_delivery/results',True),
    ('new_FP32',PROJECT/'pynq_mosaic192_eval_20261030/delivery/results/quality',False),
    ('new_QDQ',PROJECT/'pynq_mosaic192_eval_20261030/delivery/results/quality',False)]:
    for v in videos:
        folder=base/v['name']
        if label in ['new_FP32','new_QDQ']:folder=folder/label.split('_')[1]
        for stride in v['counter_replay_strides']:
            raw=folder/'raw_predictions.json.gz';trace=folder/('stride'+str(stride)+'_counter_trace.json.gz')
            def remote(path):
                rel=path.relative_to(PROJECT).parts
                rel=[x for x in rel if x!='delivery']
                # Hardware archives are staged to board_delivery on the server.
                if 'board_delivery' in path.parts:rel=list(path.relative_to(PROJECT).parts)
                return REMOTE+'/'+Path(*rel).as_posix()
            caches.append({'id':label+'_'+v['name']+'_s'+str(stride),'label':label,'kind':'gzip','scene':v['name'],'stride':stride,
                'raw_file':remote(raw),'raw_sha256':sha(raw),'trace_file':remote(trace),'trace_sha256':sha(trace),
                'board_reference':board,'spec':{k:v[k] for k in ['width','height','fps','axis','perpendicular_ROI','decode_end_exclusive']},
                'windows':[{'name':'activity','start':v['scope_start_frame0'],'end':v['scope_end_exclusive']}],
                'reference_events':v.get('reference_events'),'formal_event_scoring_allowed':v['name']=='toros','human_total':12 if v['name']=='original' else None})
reg=load(PROJECT/'firststage_iou_regression_20261029/protocol/regression_v1.json')
for source in reg['sources']:
    rawspec=next(x for x in source['files'] if x['path']==source['raw_path']);rawpath=Path(rawspec['local']);assert sha(rawpath)==rawspec['sha256']
    grouped=defaultdict(list)
    with rawpath.open(encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):grouped[int(r[source['raw_frame_key']])].append({'xyxy':[float(r[k]) for k in ['x1','y1','x2','y2']],
            'confidence':float(r['confidence']),'class':19 if source['model']=='official' else 0})
    spec={'width':source['width'],'height':source['height'],'fps':source['fps'],'axis':source['axis'],'perpendicular_ROI':source['perpendicular_ROI'],
        'decode_end_exclusive':source['history_end_frame0_exclusive']}
    name='native_'+source['name'];records=[{'frame0':i,'time_s':i/spec['fps'],'predictions':grouped[i]} for i in range(0,spec['decode_end_exclusive'],source['stride'])]
    rawfile=ROOT/'input'/(name+'_raw.json.gz');gzsave(rawfile,records)
    old=PROJECT/'firststage_iou_regression_20261029/delivery/results'/(source['name']+'__original_fused')
    post=[]
    with (old/'post_tracker_boxes.csv').open(encoding='utf-8',newline='') as f:
        for r in csv.DictReader(f):
            post.append({'frame0':int(r['frame0']),'time_s':float(r['time_s']),'track_id':int(r['track_id']) if r['track_id'] else None,
                'confidence':float(r['confidence']),'xyxy':[float(r[k]) for k in ['x1','y1','x2','y2']]})
    trace={'observations':load(old/'observations.json'),'post_tracker':post,'confirmed_only_events':load(old/'confirmed_only_events_all_history.json'),
        'handoff_events':load(old/'handoff_events_all_history.json')}
    tracefile=ROOT/'input'/(name+'_trace.json.gz');gzsave(tracefile,trace)
    windows=[{'name':w['name'],'start':w['start_frame0'],'end':w['end_frame0_exclusive']} for w in source['windows']]
    caches.append({'id':name,'label':name,'kind':'gzip','scene':source['scene'],'stride':source['stride'],'spec':spec,
        'raw_file':REMOTE+'/'+ROOT.name+'/input/'+rawfile.name,'raw_sha256':sha(rawfile),'trace_file':REMOTE+'/'+ROOT.name+'/input/'+tracefile.name,'trace_sha256':sha(tracefile),
        'board_reference':False,'windows':windows,'reference_events':videos[1].get('reference_events') if source['scene']=='toros' else None,
        'formal_event_scoring_allowed':source['formal_event_scoring_allowed'],'human_total':12 if source['name']=='original_seed26' else None})
assert len(caches)==111
eventsource=PROJECT/'pynq_mosaic192_eval_20261030/input/event_metrics.py';f=ROOT/'input/event_metrics.py';f.write_bytes(eventsource.read_bytes())
p={'status':'FROZEN111_CACHES_BEFORE_UNCONFIRMED_STAGE_PURE_IOU_CONTROL','created_host_UTC':datetime.now(timezone.utc).isoformat(),
    'caches':caches,'tracker_config':port['tracker_config'],'counter_kwargs':reg['counter'],'port_files':port['files'],
    'variants':['baseline','unconfirmed_pure_IoU'],'only_changed_stage':'BYTETracker._unconfirmed_association;temporarily_fuse_scoreFalse_then_restore',
    'high_low_new_thresholds':[.25,.1,.25],'unconfirmed_cost_limit':.7,'counter_stable_samples':3,
    'frozen_preexisting_board_reference_tolerances':{'box_pixels':.002,'normalized_axis':2e-6,'IDs_events_keys_exact':True},
    'baseline_cpu_complete_trace_exact':True,'focus':{'cache_id':'new_O8_original_s5','frame0':9550,'development_reference_id':103,
        'score':.28858277201652527,'best_fused_cost_at_IoU1':.7114172279834747,'reference_is_GT':False},
    'all_baselines_must_pass_before_probe':True,'expected_trace_conditions':222,'expected_counter_paths':444,
    'new_model_forwards':0,'new_training_updates':0,'board_actions':0,'new_independent_test':False,'whole_goal_complete':False}
save(ROOT/'protocol/control_v1.json',p)
print(json.dumps({'caches':len(caches),'trace_conditions':222,'new_neural_forwards':0}))
