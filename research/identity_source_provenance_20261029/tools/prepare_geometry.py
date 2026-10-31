from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def main():
    protocol=ROOT/'protocol';protocol.mkdir(exist_ok=False)
    index=PROJECT/'identity_training_20261026/delivery/results/study/feature_index.json';gallery=load(index)['evaluation_gallery']
    events=load(PROJECT/'confirmed12_capture_identity_20261029/delivery/results/replay/events.json')
    control=[]
    for i in [2,9]:
        e=events[i];s=e['selected_snapshot'];control.append({'name':e['event_id'],
          'source_native_photo':REMOTE+'/confirmed12_capture_identity_20261029/results/replay/'+s['native_path'],
          'source_native_sha256':s['native_sha256'],'known_native_crop_box':s['box']})
    rows=[{'published_anonymous_ID':r['identity'],'filename':r['source_filename'],
           'path':REMOTE+'/identity_training/'+r['relative_path'],'local_path':str((PROJECT/'identity_training_20261026/delivery'/r['relative_path']).resolve()),
           'sha256':r['sha256'],'width':r['width'],'height':r['height']} for r in gallery]
    assert len(rows)==30
    p={'name':'All30 existing gallery images geometric provenance pilot; no learned identity scores',
      'created_UTC':datetime.now(timezone.utc).isoformat(),'source_video':REMOTE+'/data/multicam_samples/camera1/2023-08-14T12-54-48.mp4',
      'source_sha256':'5d1d8c197abbebfd98d11b7900fe2655013acc43cf5e01bebc7c72a3bcde95a1',
      'source_dimensions_WH':[2560,1440],'source_fps':25,'decode_start0':0,'decode_end0_exclusive':10874,
      'coarse_stride':25,'coarse_expected_frames':435,'search_native_crop':[870,0,1920,1440],'search_scale':.6,
      'gallery_images':rows,'gallery_selection':'All30 frozen evaluation-gallery images across6registeredIDs; none selected by new visual matches.',
      'SIFT':{'nfeatures':3000,'contrastThreshold':.04,'edgeThreshold':10},
      'FLANN':{'algorithm':1,'trees':4,'checks':64},'Lowe_ratio':.65,
      'homography':{'method':'RANSAC','max_reprojection_error_search_px':3.,'confidence':.995,'max_iterations':2000},
      'template_feature_mask_fraction_per_side':.04,'minimum_ratio_matches_to_fit':8,
      'candidate_geometry_filters':{'minimum_inliers':12,'minimum_inlier_fraction':.5,'minimum_template_inlier_hull_area_fraction':.15,
        'minimum_corner_visible_fraction':1.,'native_mapped_quad_area_ratio_to_template':[.25,4.]},
      'photometric':{'template_interior_fraction_per_side':.08,'saturation_blue_mask_BGR':'B>160,G<130,R<130',
        'note':'Warp native source frame back onto gallery template dimensions; report grayscale NCC and MAE with blue border masked. Neither is identity truth.'},
      'retained_per_template':5,'ranking':['geometry_pass_desc','NCC_desc','inliers_desc','reprojection_median_asc','frame0_asc'],
      'pilot_known_warp_controls':control,
      'pilot_negative_controls':['fixed_seed26_iid_noise','same_control_template_quadrants_scrambled'],
      'refinement_if_control_passes':'For each template coarse bestframe, inspect all5Hz source ticks within +/-25frames, clamped to originalrange; preserve everytemplate even if coarse match fails.',
      'new_identity_model_forwards':0,'new_training_updates':0,'identity_reference_promotion_allowed':False,
      'all_12_source_events_and_raw_annotations_unchanged':True,'whole_goal_complete':False}
    out=protocol/'geometry_v1.json';out.write_text(json.dumps(p,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'protocol_sha256':sha(out),'gallery_images':30,'coarse_source_frames':435,'known_source_controls':2}))
if __name__=='__main__':main()
