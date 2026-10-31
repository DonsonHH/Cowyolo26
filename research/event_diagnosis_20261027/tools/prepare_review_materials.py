"""Review derivatives from verified diagnostic outputs; never creates reference truth."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,shutil
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent
DELIVERY=ROOT/'delivery/results'


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    source=json.loads((DELIVERY/'source_cases/summary.json').read_text(encoding='utf-8'))
    assert source['status']=='TWENTY_NATIVE_SOURCE_FRAMES_AND_80_OVERLAYS_PREPARED'
    assert source['source_scope']==[8912,10873] and not source['human_passage_or_identity_truth_created']
    allowed_models=['pilot','epoch20_seed26','epoch20_seed27','epoch20_seed28']
    prior=BASE/'detector_training_20261027/delivery/results/inference'
    by_model={}
    for name in allowed_models:
        by_frame=defaultdict(list)
        for row in csv.DictReader((prior/name/'source_tracks.csv').open()):by_frame[int(row['source_frame'])].append(row)
        by_model[name]=by_frame
    assets=BASE/'phase3_diagnosis_20261026/inputs/diagnostic_cases'
    assert not assets.exists();assets.mkdir()
    verified=[];record_frames=[]
    for row in source['frames']:
        frame=row['source_frame'];assert 8912<=frame<=10873 and abs(row['time_s']-frame/25)<1e-10
        native=DELIVERY/'source_cases'/row['native_jpeg'];assert sha(native)==row['native_jpeg_sha256']
        with Image.open(native) as im:im.load();assert im.size==(2560,1440)
        target=assets/native.name;shutil.copyfile(native,target);assert sha(target)==sha(native)
        images=[]
        assert [r['model'] for r in row['overlays']]==allowed_models
        for overlay in row['overlays']:
            name=overlay['model'];assert overlay['tracks']==by_model[name][frame]
            original=DELIVERY/'source_cases'/overlay['path'];assert sha(original)==overlay['sha256']
            with Image.open(original) as im:im.load();assert im.size==(1280,720)
            target=assets/original.name;shutil.copyfile(original,target);assert sha(target)==sha(original)
            images.append({'model':name,'url':'../inputs/diagnostic_cases/'+target.name,
                           'track_ids':[int(r['track_id']) for r in overlay['tracks']],
                           'events_at_this_frame':overlay['events_at_this_frame']})
            verified.append({'file':target.name,'sha256':sha(target),'kind':'actual_cached_output_overlay'})
        record_frames.append({'source_frame':frame,'time_s':row['time_s'],
                              'native_url':'../inputs/diagnostic_cases/'+native.name,'models':images})
        verified.append({'file':native.name,'sha256':sha(native),'kind':'native_resolution_source_jpeg_derivative'})
    assert len(verified)==100 and len(record_frames)==20
    observations=[
        {'case_id':'case1','note':'9345附近画面中可见两头牛并排，seed28同时输出两条事件。先检查各自完整跨区与轨迹连续性，再判断是否重复。仅按时间去重会有合并两头牛的风险。',
         'status':'AGENT_NONBLIND_VISUAL_OBSERVATION_NOT_HUMAN_REFERENCE'},
        {'case_id':'case2','note':'9475附近黑底白纹牛位于通道中下部。seed26的track18输出事件，其他模型在附近使用不同ID。需结合前面的稳定起始区观察检查，不能用单张有框代替完整通行。',
         'status':'AGENT_NONBLIND_VISUAL_OBSERVATION_NOT_HUMAN_REFERENCE'},
        {'case_id':'case3','note':'9695附近左侧深色牛向下移动；seed27在部分所选帧没有该牛的输出框。seed26的track20仍有框但未在这段输出事件，需检查历史与连续性。',
         'status':'AGENT_NONBLIND_VISUAL_OBSERVATION_NOT_HUMAN_REFERENCE'},
        {'case_id':'case4','note':'9790附近白底黑纹牛的seed26轨迹21输出跨区事件；其他模型在之前/之后能看到该牛的框。这里适合比较两侧稳定观察是否被串接或中断。',
         'status':'AGENT_NONBLIND_VISUAL_OBSERVATION_NOT_HUMAN_REFERENCE'}]
    cases=[]
    for case in source['cases']:
        cases.append({**case,'observation':next(r for r in observations if r['case_id']==case['case_id']),
                      'frames':[next(r for r in record_frames if r['source_frame']==f) for f in case['frames']]})
    record={'status':'20_SOURCE_FRAMES_80_OVERLAYS_AND_TRACE_PROVENANCE_VERIFIED','source_scope':[8912,10873],
            'source_sha256':source['source_sha256'],'case_count':4,'models':allowed_models,'cases':cases,
            'reference_labels_created':False,'selection':'Fixed prediction-disagreement windows; nonblind debugging material, not final evaluation sample'}
    target=BASE/'phase3_diagnosis_20261026/annotation_workbench/event_review_data.json'
    target.write_text(json.dumps(record,indent=2,ensure_ascii=False),encoding='utf-8')
    (ROOT/'results/source_case_verification.json').write_text(json.dumps({'status':record['status'],
          'files':verified,'source_frames':[r['source_frame'] for r in record_frames],
          'independent_event_truth_created':False,'visual_observations':observations},indent=2,ensure_ascii=False),encoding='utf-8')
    print(json.dumps({'status':record['status'],'verified_assets':len(verified),'case_count':4}),flush=True)


if __name__=='__main__':main()
