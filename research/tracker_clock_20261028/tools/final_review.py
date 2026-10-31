from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import csv,hashlib,json,re
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    target=ROOT/'results/final_review.json';assert not target.exists()
    local=load(ROOT/'results/local_verification.json');probe=load(ROOT/'results/probe_local_verification.json')
    assert local['files']==46 and local['conditions']==7 and local['native_flow_rows']==8705
    assert local['both_controls_preserve_event_times_directions'] and local['both_controls_change_IDs_and_tracks']
    assert probe['files']==10 and probe['counter_states_checked']==63
    files=[]
    for folder in ['delivery','probe_delivery']:
        for row in load(ROOT/folder/'delivery_manifest.json'):
            path=ROOT/folder/row['path'];assert path.stat().st_size==row['bytes'] and sha(path)==row['sha256'];files.append(row['path'])
    assert len(files)==len(set(files))==56
    for filename in ['replay.py','verify_collect.py']:
        assert sha(ROOT/'tools'/filename)==sha(ROOT/'delivery/tools'/filename)
    assert sha(ROOT/'tools/case_probe.py')==sha(ROOT/'probe_delivery/tools/case_probe.py')
    summary=load(ROOT/'delivery/results/summary.json');check=load(ROOT/'delivery/results/independent_verification.json')
    assert check['summary_sha256']==sha(ROOT/'delivery/results/summary.json')
    assert summary['protocol_sha256']==check['protocol_sha256']==sha(ROOT/'protocol/clock_v1.json')
    assert [r['predicted_down'] for r in summary['conditions']]==[11,10,11,10,10,10,10]
    assert all(r['predicted_up']==0 for r in summary['conditions'])
    for case in probe['cases'][:2]:
        assert case['unconfirmed_frames']==[9305] and case['first_ROI_output_frame']==9310
        assert case['A_output_frames']==[9310,9315] and case['B_output_frames']==list(range(9335,9361,5))
        assert case['counter_origin_transitions']==[{'frame':9345,'origin':'B'}] and case['full_replay_exact']
    last=probe['cases'][2];assert last['B_output_frames']==[9355,9375] and last['full_replay_exact']
    assert last['counter_origin_transitions']==[{'frame':9315,'origin':'A'}]
    images=load(ROOT/'results/stability_case_record.json');assert images['visual_QA']=='PASS' and not images['independent_ground_truth']
    assert len(images['raw_frames'])==9 and len(images['figures'])==4
    for row in images['raw_frames']+images['figures']:
        path=ROOT/'source_case'/row['file'];assert sha(path)==row['sha256']
        with Image.open(path) as image:
            image.load()
            if row in images['raw_frames']:assert image.size==(2560,1440)
    with (ROOT/'results/stability_case_rows.csv').open(newline='',encoding='utf-8-sig') as f:assert len(list(csv.DictReader(f)))==31
    docs=[ROOT/'计划与验收.md',ROOT/'跟踪时钟与稳定区间诊断.md',ROOT/'Review与当前状态.md',PROJECT/'研究进度.md',PROJECT/'研究总览_从想法到论文.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md']
    links=[]
    for doc in docs:
        content=doc.read_text(encoding='utf-8');assert '\ufffd' not in content
        for match in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)',content):
            value=unquote(match[1] or match[2])
            if re.match(r'^[A-Za-z]:[/\\]',value):
                line=re.match(r'^(.*):(\d+)$',value);path=Path(line[1] if line else value);assert path.exists(),path
                if line:assert 1<=int(line[2])<=len(path.read_text(encoding='utf-8').splitlines())
                links.append(value)
    status=(ROOT/'results/final_status.txt').read_text(encoding='utf-8')
    assert all(f'{job}|COMPLETED|0:0|' in status for job in [130238,130239,130240])
    output={'status':'CLOCK_CONTROLS_STATE_PROBES_IMAGES_AND_SCIENTIFIC_SCOPE_REVIEWED',
       'created_UTC':datetime.now(timezone.utc).isoformat(),'clock_protocol_sha256':sha(ROOT/'protocol/clock_v1.json'),
       'probe_protocol_sha256':sha(ROOT/'protocol/case_probe_v1.json'),'delivery_files_verified':56,
       'exact_cache_replays_before_controls':5,'additional_instrumented_replays_exact':3,
       'independent_event_conditions':7,'native_track_rows':8705,'case_counter_states':63,
       'native_source_frames':9,'visual_figures':4,'local_links_checked':len(links),
       'documents':[{'path':str(p),'sha256':sha(p)} for p in docs],
       'buffer_controls_preserve_event_times_and_directions':True,'buffer_controls_change_IDs_and_tracks':True,
       'candidate_confirmation_handoff_implemented':False,'source_predictions_remain':[11,10,11],
       'three_seeds_case_objects_not_assumed_identical':True,'posthoc_cases_not_independent_truth':True,
       'new_detector_forwards':0,'training_updates':0,'independent_source_accuracy_verified':False,
       'FPGA_execution_verified':False,'whole_goal_complete':False,'goal_should_remain_active':True}
    target.write_text(json.dumps(output,indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({k:v for k,v in output.items() if k!='documents'}))
if __name__=='__main__':main()
