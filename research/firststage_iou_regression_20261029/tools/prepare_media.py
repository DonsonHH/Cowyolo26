from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    p=load(ROOT/'protocol/regression_v1.json');s=load(ROOT/'delivery/results/summary.json')
    assert s['candidate_adopted'] is False and len(s['conditions'])==18
    videos={
      'new_long':{'path':REMOTE+'/overhead_positive_reference_20261028/input/2023-08-17T13-25-38.mp4',
                  'sha256':'8210a5bf206dd7f2356bc3d4653b439ab6de12ccfdc8209fe301ac7f02807058','width':2560,'height':1440,'fps':25,
                  'start_frame0':2375,'end_frame0_exclusive':4375,'render_stride':5,'output_fps':5},
      'original_clip':{'path':REMOTE+'/data/multicam_samples/camera1/2023-08-14T12-54-48.mp4',
                  'sha256':'5d1d8c197abbebfd98d11b7900fe2655013acc43cf5e01bebc7c72a3bcde95a1','width':2560,'height':1440,'fps':25,
                  'start_frame0':8912,'end_frame0_exclusive':10874,'render_stride':1,'output_fps':25},
      'toros_used_reverse':{'path':REMOTE+'/phase2/data/mendeley_counting/extracted/Ground Truth/Toros.mp4',
                  'sha256':'1172810976a09e1a75a8b0a69edf21038393aa6f6b1c1273b8d7c34f62146a6c','width':1920,'height':1080,'fps':30,
                  'start_frame0':0,'end_frame0_exclusive':479,'render_stride':1,'output_fps':30}}
    sources=[]
    for source in p['sources']:
        anchors=list(p['fixed_visual_anchors'][source['scene']]);extra=[]
        if source['name']=='toros_generic':extra += [150,153,162,167,193,199]
        if source['name'] in ['original_seed26','toros_generic','toros_pilot']:
            overlaps=load(ROOT/'delivery/results'/(source['name']+'__firststage_pure_IoU')/'ROI_overlap_candidates.json')
            maximum=sorted(overlaps,key=lambda r:(-r['IoU'],r['frame0']))[0];extra.append(maximum['frame0'])
        records=[]
        for variant in p['variants']:
            folder=ROOT/'delivery/results'/(source['name']+'__'+variant)
            for name in ['post_tracker_boxes.csv','handoff_events_all_history.json']:
                records.append({'path':REMOTE+'/firststage_iou_regression_20261029/results/'+folder.name+'/'+name,'sha256':sha(folder/name)})
        sources.append({'source_name':source['name'],'scene':source['scene'],'anchors':sorted(set(anchors+extra)),
                        'predefined_anchors':anchors,'exploratory_post_prediction_anchors':extra,'result_files':records})
    protocol={'name':'Native paired videos and preregistered plus explicitly exploratory case panels',
              'regression_protocol_sha256':sha(ROOT/'protocol/regression_v1.json'),
              'summary_sha256':sha(ROOT/'delivery/results/summary.json'),'videos':videos,'sources':sources,
              'full_prediction_videos':9,'native_anchor_sheets':sum(len(x['anchors']) for x in sources),
              'publisher_GT_in_case_panels_only':True,'new_long_reference_overlaid':False,'new_model_forwards':0,
              'candidate_adopted':False,'whole_goal_complete':False}
    out=ROOT/'protocol/media_v1.json';assert not out.exists();out.write_text(json.dumps(protocol,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'videos':9,'anchor_sheets':protocol['native_anchor_sheets'],'protocol_sha256':sha(out)}))
if __name__=='__main__':main()
