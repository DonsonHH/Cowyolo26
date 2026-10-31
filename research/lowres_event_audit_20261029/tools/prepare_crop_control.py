from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
base=load(ROOT/'protocol/audit_v1.json');crop=PROJECT/'lowres_roi_20261029';cp=load(crop/'protocol/roi_v1.json');caches=[]
for c in cp['conditions']:
    folder=crop/'delivery/results/roi/original'/c['condition'];row={'condition':'fixedcrop_'+c['condition'],'group':'prior_fixed_detector_and_fixed_lane_crop',
        'size':c['input_size'],'seed':None if c['model']=='official' else int(c['model'][4:]),
        'raw_file':str((folder/'raw_predictions.json.gz').resolve()),'trace_file':str((folder/'stride5_counter_trace.json.gz').resolve()),
        'summary_file':str((folder/'stride5_summary.json').resolve())}
    for kind in ['raw','trace','summary']:row[kind+'_sha256']=sha(row[kind+'_file'])
    caches.append(row)
assert len(caches)==12
p={**base,'status':'FROZEN_BEFORE_EXISTING_FIXED_CROP_CACHE_ORACLE_EXTENSION','created_host_UTC':datetime.now(timezone.utc).isoformat(),
   'extends_primary_protocol_sha256':sha(ROOT/'protocol/audit_v1.json'),'primary_full_input_verification_sha256':sha(ROOT/'results/independent_verification.json'),
   'previous_fixed_crop_protocol_sha256':sha(crop/'protocol/roi_v1.json'),'caches':caches,
   'purpose':'Afterfullinputdiagnosis,comparealreadyexistingfixedROIcachewithsameweightfullinput;noROIre-tuningorre-inference.',
   'primary_case':'fixedcrop_seed26_s192','whole_goal_complete':False}
file=ROOT/'protocol/audit_crop_v1.json';assert not file.exists();file.write_text(json.dumps(p,indent=2)+'\n')
script=(ROOT/'tools/run_audit.py').read_text().replace("ROOT/'protocol/audit_v1.json'","ROOT/'protocol/audit_crop_v1.json'")
script=script.replace("out=ROOT/'results';out.mkdir(exist_ok=False)","out=ROOT/'crop_results';out.mkdir(exist_ok=False)")
script=script.replace('len(allcases)==54 and casepaths==162 and referencerows==27*2*581','len(allcases)==24 and casepaths==72 and referencerows==12*2*581')
script=script.replace('ALL27_CACHES2_FIXED_IOU_LEVELS162_DIAGNOSTIC_ORACLE_PATHS_COMPLETE','ALL12_FIXED_CROP_CACHES2_IOU_LEVELS72_ORACLE_PATHS_COMPLETE').replace("'cached_conditions':27","'cached_conditions':12")
file=ROOT/'tools/run_crop_control.py';assert not file.exists();file.write_text(script,newline='\n')
print(json.dumps({'fixed_ROI_cache_conditions':12,'new_NN_forwards':0,'new_crop_parameters':0}))
