"""Compare geometric rectangles, including width/height plus90degree equivalence."""
from pathlib import Path
import json,math,xml.etree.ElementTree as ET
from audit_labels import corners,derive
ROOT=Path(__file__).resolve().parents[1]


def polygon_error(a,b):
    alternatives=[]
    for reverse in [False,True]:
        order=list(reversed(b)) if reverse else b
        for shift in range(4):
            alternative=order[shift:]+order[:shift]
            alternatives.append(max(math.hypot(p[0]-q[0],p[1]-q[1]) for p,q in zip(a,alternative)))
    return min(alternatives)


def main():
    source=json.loads((ROOT/'results/label_audit/summary.json').read_text(encoding='utf-8'))
    catalog=json.loads((ROOT/'results/label_audit/derived_box_catalog.json').read_text(encoding='utf-8'))
    records=[]
    for sample in source['train_samples']:
        root=ET.parse(ROOT/'catalog/train_audit'/Path(sample['file_name']).with_suffix('.xml')).getroot()
        candidates=[]
        for obj in root.findall('object'):
            if obj.find('robndbox') is None:continue
            cx,cy,w,h,angle=[float(obj.findtext('robndbox/'+k)) for k in ['cx','cy','w','h','angle']]
            if w<=0 or h<=0:continue
            candidates.append({'centre':[cx,cy],'w':w,'h':h,'theta':angle,
                               'polygon':corners([cx-w/2,cy-h/2,w,h,angle])})
        rows=[r for r in catalog if r['role']=='train' and r['file_name']==sample['file_name']]
        used=[]
        for row in rows:
            errors=[polygon_error(row['original_polygon'],r['polygon']) for r in candidates]
            j=min(range(len(errors)),key=errors.__getitem__);best=candidates[j]
            assert j not in used;used.append(j)
            # Independent analytic envelope, then verify all derived box corners
            # enclose every vertex of the image-clipped polygon.
            d=row['yolo_class_cxcywh'];x1,y1,x2,y2=row['axis_box_xyxy']
            assert all(x1-1e-9<=x<=x2+1e-9 and y1-1e-9<=y<=y2+1e-9 for x,y in row['visible_polygon'])
            assert all(0<=v<=1 for v in d[1:]) and d[3]>0 and d[4]>0
            expected=[0,(x1+x2)/2560,(y1+y2)/1440,(x2-x1)/1280,(y2-y1)/720]
            assert all(abs(a-b)<1e-12 for a,b in zip(d,expected))
            x,y,w,h,t=row['bbox_xywh_angle_radians']
            swapped=abs(w-best['h'])+abs(h-best['w']) < abs(w-best['w'])+abs(h-best['h'])
            records.append({'file_name':row['file_name'],'annotation_id':row['annotation_id'],
                            'best_XML_rotated_polygon_vertex_max_difference_pixels':errors[j],
                            'width_height_swap_representation':swapped,'raw_parameter_check_flag_retained':any(r['annotation_id']==row['annotation_id'] for r in sample['XML_JSON_mismatches_above_declared_rounding_tolerance']),
                            'derived_normalised_box_geometry_verified':True,
                            'scope':'Geometry differences measured; no additional tolerance used to approve labels automatically'})
    assert len(records)==sum(r['derived_classic_YOLO_rows'] for r in source['train_samples'])
    output={'status':'SAMPLE_RECTANGLE_EQUIVALENCE_AND_DERIVED_BOXES_RECOMPUTED','records':records,
            'naive_parameter_flags':sum(r['raw_parameter_check_flag_retained'] for r in records),
            'swapped_representations':sum(r['width_height_swap_representation'] for r in records),
            'maximum_polygon_difference_pixels':max(r['best_XML_rotated_polygon_vertex_max_difference_pixels'] for r in records),
            'train_XML_zero_area_objects_not_added_as_detector_labels':sum(r['XML_zero_area_rotated_objects'] for r in source['train_samples'])}
    (ROOT/'results/XML_JSON_geometry_control.json').write_text(json.dumps(output,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in output.items() if k!='records'}),flush=True)


if __name__=='__main__':main()
