"""Freeze all noninitial publisher-ID births as five continuous audit windows."""
from pathlib import Path
import csv,hashlib,json,zipfile

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    out=ROOT/'protocol';out.mkdir(parents=True,exist_ok=False)
    upstream=PROJECT/'mootrack_alignment_20261028';index=upstream/'results/sample_index/index.json'
    meta=json.loads(index.read_text(encoding='utf-8'));samples=[]
    with (index.parent/'samples.csv').open(encoding='utf-8') as f:
        for r in csv.DictReader(f):
            samples.append({k:(v=='True' if k=='sync' else int(v)) for k,v in r.items()})
    assert len(samples)==53946 and all(s['display_index0']==s['decode_index0']==i for i,s in enumerate(samples))
    assert meta['timescale']==30000 and meta['ctts_present'] is False
    archive=PROJECT/'counting_reference_candidates_20261027/catalog/MooTrack360_TrackEval_evaluation_code.zip'
    assert sha(archive)=='26800ea3b6e653e4e9d7c54a2587060bd2a920b4e862f0b84afef624234b6478'
    with zipfile.ZipFile(archive) as z:b=z.read('TrackEval_evaluation_code/TrackEval/data/gt/mot_challenge/1hour/gt/gt.txt')
    assert hashlib.sha256(b).hexdigest()=='595cdad9581382da5f3f406b2259f3d6937b1a131f6d677eca5756bdfcabccbd'
    first={}
    for line in b.decode().splitlines():
        r=line.split(',');frame,ID=map(int,r[:2])
        if ID not in first:first[ID]={'first_GT_frame1':frame,'xywh':list(map(float,r[2:6]))}
    births=[(ID,r) for ID,r in sorted(first.items()) if r['first_GT_frame1']>1]
    assert [(ID,r['first_GT_frame1']) for ID,r in births]==[(0,1581),(1,6341),(2,6791),(6,26521),(7,39859)]
    windows=[]
    for ID,r in births:
        center=r['first_GT_frame1']-1;start=center-30;end=center+60
        decode_start=max(n for n in meta['sync_indices'] if n<=start)
        decode_end=next((n for n in meta['sync_indices'] if n>=end),len(samples))
        selected=samples[decode_start:decode_end]
        assert len(selected)>0 and selected[0]['sync']
        minimum=min(s['offset'] for s in selected);maximum=max(s['offset']+s['size'] for s in selected)
        windows.append({'name':f'GT_ID{ID}_birth_{center:05d}','publisher_ID':ID,'first_GT_frame1':r['first_GT_frame1'],
                        'first_GT_xywh_raw':r['xywh'],'center_video_frame0_hypothesis':center,
                        'review_start_video0':start,'review_end_video0_exclusive':end,'review_frames':end-start,
                        'decode_start_video0':decode_start,'decode_end_video0_exclusive':decode_end,'decode_frames':len(selected),
                        'range_start':minimum,'range_end_exclusive':maximum,'range_bytes':maximum-minimum,
                        'video_sample_bytes':sum(s['size'] for s in selected),
                        'native_anchor_frames0':[center-30,center-1,center,center+15,center+59]})
    planned=sum(w['range_bytes'] for w in windows)+1076007
    assert planned<256*1024*1024
    p={'version':'continuous_births_v1','intended_use':'Temporal and spatial correspondence audit, not model evaluation or complete passage truth.',
       'source_url':'https://zenodo.org/records/20287681/files/1hour_annotated_sequence.mp4?download=1','source_total_bytes':18890553141,
       'moov_sha256':'f060958b4bd3120c0e35070f0532930e41a97e349a8d8e448f8d60031b2e18d3',
       'upstream_review_sha256':sha(upstream/'results/final_review.json'),'sample_index_sha256':sha(index),'sample_rows_sha256':sha(index.parent/'samples.csv'),
       'GT_zip_sha256':sha(archive),'GT_member_sha256':hashlib.sha256(b).hexdigest(),
       'fps_numerator':30000,'fps_denominator':2002,'GT_coordinate_scale':2.0,'GT_translation':[0,0],
       'video0_to_GT1_offset_hypothesis':1,'all_noninitial_ID_births_included':True,'pixel_inspection_preceded_this_window_selection':False,
       'previous_static_samples_inspected':True,'window_selection_uses_model_predictions':False,'HTTP_budget_bytes':256*1024*1024,
       'planned_HTTP_bytes':planned,'planned_review_frames':sum(w['review_frames'] for w in windows),
       'planned_decode_frames':sum(w['decode_frames'] for w in windows),'windows':windows,
       'whole_GT_alignment_not_proved_by_these_windows':True,'whole_goal_complete':False}
    (out/'continuous_births_v1.json').write_text(json.dumps(p,indent=2),encoding='utf-8')
    print(json.dumps({'planned_bytes':planned,'decode_frames':p['planned_decode_frames'],'review_frames':p['planned_review_frames'],
                      'windows':[{k:v for k,v in w.items() if k in ['name','range_bytes','first_GT_xywh_raw','decode_frames']} for w in windows]}),flush=True)

if __name__=='__main__':main()
