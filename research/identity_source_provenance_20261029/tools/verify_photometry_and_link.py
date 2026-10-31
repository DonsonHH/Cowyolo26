from pathlib import Path
from PIL import Image
from collections import defaultdict
import csv,hashlib,json,numpy as np
from verify_geometry import polygon_area
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def crop_polygon(points,box):
    result=[list(p) for p in points]
    for axis,bound,lower in [(0,box[0],True),(0,box[2],False),(1,box[1],True),(1,box[3],False)]:
        if not result:break
        clipped=[];previous=result[-1];previous_inside=previous[axis]>=bound if lower else previous[axis]<=bound
        for current in result:
            inside=current[axis]>=bound if lower else current[axis]<=bound
            if inside!=previous_inside:
                t=(bound-previous[axis])/(current[axis]-previous[axis]);point=[previous[j]+t*(current[j]-previous[j]) for j in range(2)]
                point[axis]=bound;clipped.append(point)
            if inside:clipped.append(current)
            previous=current;previous_inside=inside
        result=clipped
    return result
def photometry(gallery,warp):
    with Image.open(gallery) as im:a=np.asarray(im.convert('RGB'))
    with Image.open(warp) as im:b=np.asarray(im.convert('RGB'))
    assert a.shape==b.shape;h,w=a.shape[:2];mask=np.zeros((h,w),bool);mask[round(h*.08):round(h*.92),round(w*.08):round(w*.92)]=True
    mask &= ~((a[:,:,2]>160)&(a[:,:,1]<130)&(a[:,:,0]<130))
    # Independent fixed-point RGB-to-luma, then direct normalized dot product.
    gray=lambda image:((image.astype(np.int64)*[4899,9617,1868]).sum(axis=2)+8192)>>14
    x,y=gray(a)[mask].astype(float),gray(b)[mask].astype(float);x-=x.mean();y-=y.mean()
    ncc=float(np.dot(x,y)/np.sqrt(np.dot(x,x)*np.dot(y,y)));mae=float(np.abs(a.astype(float)[mask]-b.astype(float)[mask]).mean())
    return {'NCC':ncc,'mean_absolute_BGR_error':mae,'valid_pixels':int(mask.sum())}
def main():
    rows=load(ROOT/'refined_delivery/results/geometry_refined/top_results.json');art=load(ROOT/'refined_delivery/results/geometry_refined/artifacts.json')
    endpoint=load(ROOT/'endpoint_delivery/results/endpoint_check/summary.json');checked=[]
    with (PROJECT/'firststage_iou_regression_20261029/delivery/results/original_seed26__original_fused/post_tracker_boxes.csv').open(newline='') as f:post=list(csv.DictReader(f))
    by_frame=defaultdict(list)
    for r in post:
        if r['track_id']:by_frame[int(r['frame0'])].append(r)
    for r,a in zip(rows,art):
        best=r['top'][0]
        if not best['geometry_pass']:continue
        actual=photometry(Path(r['gallery']['local_path']),ROOT/'refined_delivery'/a['rewarp_file'])
        assert abs(actual['NCC']-best['NCC'])<1e-12 and actual['mean_absolute_BGR_error']==best['mean_absolute_BGR_error']
        quad=best['mapped_native_corners'];area=polygon_area(quad);support=[]
        for track in by_frame[best['source_frame0']]:
            box=[float(track[k]) for k in ['x1','y1','x2','y2']];intersection=polygon_area(crop_polygon(quad,box))
            union=area+max(0,box[2]-box[0])*max(0,box[3]-box[1])-intersection
            support.append({'track_ID':int(track['track_id']),'quad_box_IoU':intersection/(union+1e-7),'native_box':box})
        support.sort(key=lambda r:-r['quad_box_IoU'])
        checked.append({'template_index':r['template_index'],'anonymous_ID':r['gallery']['published_anonymous_ID'],'filename':r['gallery']['filename'],
            'source_frame0':best['source_frame0'],'independent_photometry':actual,'native_quad_to_confirmed_tracks':support,
            'gallery_sha256':r['gallery']['sha256'],'warp_sha256':a['rewarp_sha256'],'NCC_not_identity_accuracy':True})
    endpoint_checks=[]
    for r in endpoint['endpoint_results']:
        assert sha(Path(r['gallery']['local_path']))==r['gallery']['sha256']
        actual=photometry(Path(r['gallery']['local_path']),ROOT/'endpoint_delivery'/r['rewarp_file'])
        expected=r['diagnostic_photometric'];assert abs(actual['NCC']-expected['NCC'])<1e-12 and actual['mean_absolute_BGR_error']==expected['mean_absolute_BGR_error']
        endpoint_checks.append({'template_index':r['template_index'],'predicted_source_frame0':r['predicted_source_frame0'],
            'unchanged_geometry_pass':r['match']['geometry_pass'],'corners_visible_fraction':r['match']['corners_visible_fraction'],
            'independent_photometry':actual,'endpoint_same_capture_confirmed':False})
    core=[r for r in checked if r['template_index'] in [1,2,3]]
    assert len(core)==3 and all(r['independent_photometry']['NCC']>.99 and r['native_quad_to_confirmed_tracks'][0]['track_ID']==102 for r in core)
    assert [r['source_frame0']-5*int(r['filename'].split('_')[0]) for r in core]==[9490]*3
    assert endpoint_checks[1]['unchanged_geometry_pass'] is False and endpoint_checks[1]['independent_photometry']['NCC']>.99
    assert endpoint_checks[0]['independent_photometry']['NCC']<.8
    events=load(PROJECT/'confirmed12_capture_identity_20261029/delivery/results/replay/events.json');event=next(e for e in events if e['track_id']==102)
    assert event['event_id']=='E010_f9790_tid102' and event['selected_snapshot']['frame0']==9745
    result={'status':'SEVEN_PHOTOMETRIC_PAIRS_AND_THREE_SOURCE_QUAD_TRACK102_LINKS_INDEPENDENTLY_VERIFIED',
        'geometry_accepted_refined_template_photometry':checked,'post_search_endpoint_checks':endpoint_checks,
        'core_same_source_capture_candidates':[{'gallery_filename':r['filename'],'source_frame0':r['source_frame0'],
          'NCC':r['independent_photometry']['NCC'],'best_native_track_ID':102,'quad_box_IoU':r['native_quad_to_confirmed_tracks'][0]['quad_box_IoU']} for r in core],
        'related_event_id':event['event_id'],'related_query_snapshot_frame0':9745,'related_event_frame0':9790,
        'evidence_level':'Strong geometric/pixel source-overlap evidence; no independent human identity reference or ear-tag mapping.',
        'evaluation_decision':'Do not use thissame-passage source query and currentID009Aug14gallery as independent identity evaluation.',
        'public_ID020_no_proven_source_link_in_this_bounded_search':True,
        'missing_geometric_match_is_not_absence_or_wrong_identity_proof':True,
        'no_model_prediction_promoted_to_truth':True,'independent_event_identity_scores_computed':False,'whole_goal_complete':False}
    path=ROOT/'results/photometry_and_event_link_verification.json';assert not path.exists();path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['geometry_accepted_refined_template_photometry','post_search_endpoint_checks']}))
if __name__=='__main__':main()
