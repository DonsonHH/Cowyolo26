from pathlib import Path
import hashlib,json,math,numpy as np
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def polygon_area(points):
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(points,points[1:]+points[:1])))/2
def convex_hull(points):
    values=sorted(set(tuple(p) for p in points))
    if len(values)<3:return values
    def cross(o,a,b):return (a[0]-o[0])*(b[1]-o[1])-(a[1]-o[1])*(b[0]-o[0])
    low=[];high=[]
    for v in values:
        while len(low)>=2 and cross(low[-2],low[-1],v)<=0:low.pop()
        low.append(v)
    for v in reversed(values):
        while len(high)>=2 and cross(high[-2],high[-1],v)<=0:high.pop()
        high.append(v)
    return low[:-1]+high[:-1]
def project(points,H):
    x=np.c_[np.asarray(points,float),np.ones(len(points))]@np.asarray(H,float).T
    return x[:,:2]/x[:,2,None]
def rank(row):return (row['geometry_pass'],row['NCC'] if row['NCC'] is not None else -2,row['inliers'],-row.get('reprojection_median_search_px',1e10),-row.get('source_frame0',0))
def verify_folder(folder,refined=False):
    p=load(ROOT/'protocol/geometry_v1.json')
    path=folder/('results/geometry_refined' if refined else 'results/geometry_coarse');rows=load(path/'top_results.json');metrics=load(path/'all_metrics.json')
    assert len(rows)==30 and {r['template_index'] for r in rows}==set(range(30))
    if refined:q=load(ROOT/'protocol/refinement_v1.json');assert len(metrics)==q['per_template_comparisons']==300
    else:assert len(metrics)==435*30
    checked=0;inlier_points=0;brief=[]
    for r in rows:
        g=r['gallery'];w,h=g['width'],g['height'];index=r['template_index'];assert g==p['gallery_images'][index]
        local_metrics=[m for m in metrics if m['template_index']==index]
        if refined:assert [m['source_frame0'] for m in local_metrics]==q['templates'][index]['refine_frame0s']
        else:assert [m['source_frame0'] for m in local_metrics]==list(range(0,10874,25))
        best=sorted(local_metrics,key=rank,reverse=True)[:5]
        assert [m['source_frame0'] for m in best]==[m['source_frame0'] for m in r['top']]
        for candidate in r['top']:
            m=next(m for m in local_metrics if m['source_frame0']==candidate['source_frame0'])
            assert all(candidate[k]==v for k,v in m.items() if k!='template_index')
            if 'homography_template_to_native' not in candidate:continue
            u=candidate['inlier_template_xy'];v=candidate['inlier_native_xy'];assert len(u)==len(v)==candidate['inliers']
            H=candidate['homography_template_to_native'];projected=project(u,H)
            error=float(np.median(np.linalg.norm(projected-np.asarray(v),axis=1)*p['search_scale']))
            assert abs(error-candidate['reprojection_median_search_px'])<2e-4
            hull=convex_hull(u);fraction=polygon_area(hull)/(w*h);assert abs(fraction-candidate['template_inlier_hull_fraction'])<1e-7
            corner=project([[0,0],[w-1,0],[w-1,h-1],[0,h-1]],H)
            assert np.max(abs(corner-np.asarray(candidate['mapped_native_corners'])))<.002
            area=polygon_area(candidate['mapped_native_corners'])/(w*h);assert abs(area-candidate['native_quad_area_ratio_to_template'])<1e-6
            fraction_inliers=len(u)/candidate['ratio_matches'];assert fraction_inliers==candidate['inlier_fraction']
            if candidate['geometry_pass']:
                assert len(u)>=12 and fraction_inliers>=.5 and fraction>=.15
                assert candidate['corners_visible_fraction']==1. and .25<=area<=4
                assert -1<=candidate['NCC']<=1 and 0<=candidate['mean_absolute_BGR_error']<=255
            checked+=1;inlier_points+=len(u)
        brief.append({'template_index':index,'anonymous_ID':g['published_anonymous_ID'],'filename':g['filename'],
                      'frame0':r['top'][0]['source_frame0'],'geometry_pass':r['top'][0]['geometry_pass'],'NCC':r['top'][0]['NCC']})
    return {'comparisons':len(metrics),'candidates_with_transform_checked':checked,'inlier_points_checked':inlier_points,'best_each':brief}
def main():
    first=verify_folder(ROOT/'geometry_delivery');checks=load(ROOT/'geometry_delivery/results/geometry_coarse/controls.json')
    assert checks['passed'] is True and len(checks['records'])==2
    for r in checks['records']:
        assert r['known_warp_positive']['geometry_pass'] is True and r['known_warp_positive']['NCC']>.9 and r['maximum_native_corner_error']<5
        assert r['noise_negative']['geometry_pass'] is False
        assert not(r['scramble_negative']['geometry_pass'] and r['scramble_negative']['NCC'] is not None and r['scramble_negative']['NCC']>.9)
    result={'status':'COARSE_GEOMETRIC_CANDIDATE_COORDINATES_RANKING_AND_CONTROL_RECORDS_INDEPENDENTLY_VERIFIED',
            'coarse':first,'controls':2,'geometric_candidates_not_identity_truth':True,'source_mapping_certified':False,'whole_goal_complete':False}
    target=ROOT/'results/coarse_geometry_independent_verification.json';assert not target.exists();target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='coarse'}));print(json.dumps({k:v for k,v in first.items() if k!='best_each'}))
if __name__=='__main__':main()
