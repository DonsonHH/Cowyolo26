"""Independent polar-corner and clipping-envelope checks for all13165labels."""
from pathlib import Path
from collections import Counter
import csv,hashlib,json,math
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent


def polar_polygon(box):
    x,y,w,h,t=box;cx=x+w/2;cy=y+h/2;r=math.hypot(w,h)/2;a=math.atan2(h,w)
    return [(cx-r*math.cos(t+a),cy-r*math.sin(t+a)),(cx+r*math.cos(t-a),cy+r*math.sin(t-a)),
            (cx+r*math.cos(t+a),cy+r*math.sin(t+a)),(cx-r*math.cos(t-a),cy-r*math.sin(t-a))]


def point_inside(point,polygon):
    crosses=[(b[0]-a[0])*(point[1]-a[1])-(b[1]-a[1])*(point[0]-a[0]) for a,b in zip(polygon,polygon[1:]+polygon[:1])]
    return min(crosses)>=-1e-8 or max(crosses)<=1e-8


def visible_vertices(polygon,width,height):
    # Enumerate both polygons' interior vertices and all segment/rectangle
    # crossings; independent from repeated half-plane clipping.
    points=[p for p in polygon if 0<=p[0]<=width and 0<=p[1]<=height]
    for p in [(0,0),(width,0),(width,height),(0,height)]:
        if point_inside(p,polygon):points.append(p)
    for a,b in zip(polygon,polygon[1:]+polygon[:1]):
        for axis,bound in [(0,0),(0,width),(1,0),(1,height)]:
            delta=b[axis]-a[axis]
            if abs(delta)<1e-14:continue
            t=(bound-a[axis])/delta
            if 0<=t<=1:
                p=[a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])];p[axis]=bound
                if -1e-8<=p[0]<=width+1e-8 and -1e-8<=p[1]<=height+1e-8:points.append(p)
    return points


def main():
    result=json.loads((ROOT/'results/label_audit/summary.json').read_text(encoding='utf-8'))
    catalog=json.loads((ROOT/'results/label_audit/derived_box_catalog.json').read_text(encoding='utf-8'))
    assert len(catalog)==13165 and result['total_published_images']==10402
    metadata={};checked=0;max_error=0.
    for role,name,expected in [('train','train_annotations.json',(7248,9395)),('validation','validation_annotations.json',(1023,1238)),('reserved_test','reserved_test_annotations.json',(2131,2532))]:
        path=ROOT/'catalog'/name;raw=json.loads(path.read_text(encoding='utf-8'))
        record=json.loads(path.with_name(path.name+'.record.json').read_text(encoding='utf-8'))
        assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256'] and path.stat().st_size==record['bytes']
        assert (len(raw['images']),len(raw['annotations']))==expected
        imgs={r['id']:r for r in raw['images']};anns={r['id']:r for r in raw['annotations']}
        metadata[role]={'images':imgs,'annotations':anns}
        for row in (r for r in catalog if r['role']==role):
            source=anns[row['annotation_id']];image=imgs[row['image_id']]
            assert source['bbox']==row['bbox_xywh_angle_radians'] and image['file_name']==row['file_name']
            polygon=polar_polygon(source['bbox']);expected_points=visible_vertices(polygon,image['width'],image['height'])
            assert expected_points and row['valid']
            xs,ys=zip(*expected_points);box=[min(xs),min(ys),max(xs),max(ys)]
            error=max(abs(a-b) for a,b in zip(box,row['axis_box_xyxy']));max_error=max(max_error,error)
            assert error<1e-8
            d=row['yolo_class_cxcywh'];x1,y1,x2,y2=box
            expected_box=[0,(x1+x2)/2/image['width'],(y1+y2)/2/image['height'],(x2-x1)/image['width'],(y2-y1)/image['height']]
            assert max(abs(a-b) for a,b in zip(d,expected_box))<1e-9
            checked+=1
    selected=json.loads((ROOT/'protocol/cows_labels_v1.json').read_text(encoding='utf-8'))['selected']
    assert len(selected)==12
    downloaded=sorted((ROOT/'catalog/train_audit').glob('*.jpg'));assert len(downloaded)==12
    old_hashes={r['sha256'] for r in csv.DictReader((BASE/'data_audit_20261026/local_opencows/image_manifest.csv').open(encoding='utf-8'))}
    collisions=[]
    for sample in result['train_samples']:
        name=sample['file_name'];image=ROOT/'catalog/train_audit'/name
        assert any(s['image']['file_name']==name for s in selected)
        assert name in {r['file_name'] for r in metadata['train']['images'].values()}
        assert hashlib.sha256(image.read_bytes()).hexdigest()==sample['source_jpeg_sha256']
        with Image.open(image) as im:im.load();assert im.size==(1280,720)
        with Image.open(ROOT/sample['overlay']) as im:im.load();assert im.size==(1280,720)
        if sample['source_jpeg_sha256'] in old_hashes:collisions.append(name)
        lines=(ROOT/'results/label_audit/sample_yolo'/Path(name).with_suffix('.txt')).read_text(encoding='utf-8').splitlines()
        assert len(lines)==sample['derived_classic_YOLO_rows']
        for line in lines:
            cls,cx,cy,w,h=map(float,line.split());assert cls==0 and w>0 and h>0 and min(cx-w/2,cy-h/2)>=-1e-8 and max(cx+w/2,cy+h/2)<=1+1e-8
    equivalence=json.loads((ROOT/'results/XML_JSON_geometry_control.json').read_text(encoding='utf-8'))
    assert equivalence['naive_parameter_flags']==equivalence['swapped_representations']==2
    assert len(equivalence['records'])==sum(r['derived_classic_YOLO_rows'] for r in result['train_samples'])
    tree=json.loads((ROOT/'catalog/repo_tree.json').read_text(encoding='utf-8'))
    source_checks=[]
    for name in ['visualization.py','rotate_test.py','anchors.py']:
        path=ROOT/'catalog/author_blobs'/name;content=path.read_bytes()
        original=next(r for r in tree['tree'] if r['path'].endswith('/'+name))
        digest=hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()
        assert digest==original['sha'];source_checks.append({'path':original['path'],'blob_sha1':digest})
    output={'status':'ALL_JSON_GEOMETRY_AND_TRAIN_SAMPLE_DERIVATIVES_VERIFIED','published_image_metadata':10402,
            'rotated_boxes_independently_converted':checked,'maximum_axis_envelope_error_pixels':max_error,
            'train_image_XML_pairs':12,'original_and_overlay_JPEGs_decoded':24,'author_source_blob_checks':source_checks,
            'naive_XML_parameter_flags_retained':2,'width_height_swap_equivalent_representations':2,
            'sample_max_XML_JSON_polygon_difference_pixels':equivalence['maximum_polygon_difference_pixels'],
            '12sample_byte_collisions_with_OpenCows_manifest':collisions,
            'all_Cows2021_OpenCows_source_overlap_resolved':False,'validation_and_reserved_test_pixels_downloaded':False,
            'full_XML_source_metadata_recovery_complete':(ROOT/'results/source_recovery_summary.json').exists(),
            'new_model_training_or_inference':False,'whole_goal_complete':False}
    (ROOT/'results/independent_verification.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    print(json.dumps(output),flush=True)


if __name__=='__main__':main()
