"""Rotated public-label audit and explicit axis-aligned derivative, no model forward."""
from pathlib import Path
from collections import Counter,defaultdict
import csv,hashlib,json,math,re,xml.etree.ElementTree as ET
from PIL import Image,ImageDraw,ImageOps
ROOT=Path(__file__).resolve().parents[1]


def corners(box):
    x,y,w,h,angle=box;cx=x+w/2;cy=y+h/2;c=math.cos(angle);s=math.sin(angle)
    return [(cx+dx*c-dy*s,cy+dx*s+dy*c) for dx,dy in [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]]


def clip_polygon(poly,width,height):
    for axis,bound,greater in [(0,0,True),(0,width,False),(1,0,True),(1,height,False)]:
        before=poly;poly=[]
        if not before:break
        def inside(p):return p[axis]>=bound if greater else p[axis]<=bound
        for a,b in zip(before[-1:]+before[:-1],before):
            ia,ib=inside(a),inside(b)
            if ia!=ib:
                t=(bound-a[axis])/(b[axis]-a[axis]);point=[a[0]+t*(b[0]-a[0]),a[1]+t*(b[1]-a[1])];point[axis]=bound
                poly.append(tuple(point))
            if ib:poly.append(tuple(b))
    return poly


def area(poly):
    return abs(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(poly,poly[1:]+poly[:1])))/2 if len(poly)>=3 else 0.


def derive(box,width,height):
    polygon=corners(box);clipped=clip_polygon(polygon,width,height)
    if area(clipped)<=1e-8:return {'original_polygon':polygon,'visible_polygon':clipped,'valid':False}
    xs,ys=zip(*clipped);aabb=[min(xs),min(ys),max(xs),max(ys)]
    x1,y1,x2,y2=aabb
    return {'original_polygon':polygon,'visible_polygon':clipped,'valid':True,'axis_box_xyxy':aabb,
            'yolo_class_cxcywh':[0,(x1+x2)/2/width,(y1+y2)/2/height,(x2-x1)/width,(y2-y1)/height],
            'visible_polygon_fraction':area(clipped)/(box[2]*box[3])}


def geometry_controls():
    a=derive([10,20,40,20,0],100,100);assert a['axis_box_xyxy']==[10.,20.,50.,40.]
    b=derive([10,20,40,20,math.pi/2],100,100)
    assert all(abs(x-y)<1e-10 for x,y in zip(b['axis_box_xyxy'],[20,10,40,50]))
    c=derive([-20,20,40,20,0],100,100);assert abs(c['visible_polygon_fraction']-.5)<1e-10
    assert not derive([200,200,20,10,0],100,100)['valid']
    # Independent closed-form envelope for the unclipped rotated rectangle.
    for angle in [-1.4,-.5,0,.7,2.9]:
        x,y,w,h=30,50,70,20;poly=corners([x,y,w,h,angle]);xs,ys=zip(*poly)
        halfx=(abs(w*math.cos(angle))+abs(h*math.sin(angle)))/2
        halfy=(abs(w*math.sin(angle))+abs(h*math.cos(angle)))/2
        expected=[x+w/2-halfx,y+h/2-halfy,x+w/2+halfx,y+h/2+halfy]
        assert all(abs(a-b)<1e-10 for a,b in zip([min(xs),min(ys),max(xs),max(ys)],expected))
    return 'AXIS_ROTATION_CLIPPING_AND_INDEPENDENT_ENVELOPE_PASS'


def main():
    out=ROOT/'results/label_audit';out.mkdir(parents=True,exist_ok=False)
    roles={'train':'train_annotations.json','validation':'validation_annotations.json','reserved_test':'reserved_test_annotations.json'}
    summaries=[];all_images={};all_rows=[];role_dates={};samples=[]
    for role,file in roles.items():
        path=ROOT/'catalog'/file;value=json.loads(path.read_text(encoding='utf-8'))
        imgs={r['id']:r for r in value['images']};assert len(imgs)==len(value['images'])
        assert len({r['file_name'] for r in imgs.values()})==len(imgs)
        assert len({r['id'] for r in value['annotations']})==len(value['annotations'])
        assert value['categories']==[{'supercategory':'cow','id':1,'name':'xin'}]
        byid=defaultdict(list);empty=invalid=outside=0;angles=[]
        for r in value['annotations']:
            image=imgs[r['image_id']];assert r['category_id']==1 and r['iscrowd']==0 and len(r['bbox'])==5
            box=list(map(float,r['bbox']));assert all(math.isfinite(v) for v in box) and box[2]>0 and box[3]>0
            angles.append(box[4]);derived=derive(box,image['width'],image['height'])
            invalid+=not derived['valid']
            outside+=any(x<0 or y<0 or x>image['width'] or y>image['height'] for x,y in derived['original_polygon'])
            row={'role':role,'image_id':image['id'],'file_name':image['file_name'],'annotation_id':r['id'],
                 'published_category_id':1,'derived_class':0,'bbox_xywh_angle_radians':box,**derived}
            byid[image['id']].append(row);all_rows.append(row)
        for r in imgs.values():
            assert r['file_name'] not in all_images
            all_images[r['file_name']]={'role':role,**r};empty+=not byid[r['id']]
        summaries.append({'role':role,'images':len(imgs),'annotations':len(value['annotations']),'annotation_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                          'dimensions':dict(Counter(f"{r['width']}x{r['height']}" for r in imgs.values())),
                          'bbox_length':5,'angles_min_max_radians':[min(angles),max(angles)],
                          'rotated_polygons_outside_image':outside,'zero_visible_polygons':invalid,'images_without_published_objects':empty,
                          'category_mapping':'category1(supercategory cow,name xin) -> derived torso class0; no cow identity assigned'})
    assert sum(r['images'] for r in summaries)==10402
    protocol=json.loads((ROOT/'protocol/cows_labels_v1.json').read_text(encoding='utf-8'))
    (out/'sample_overlays').mkdir();(out/'sample_yolo').mkdir()
    source_notes=[]
    for sample in protocol['selected']:
        image=sample['image'];name=image['file_name'];assert all_images[name]['role']=='train'
        jpg=ROOT/'catalog/train_audit'/name;xml=jpg.with_suffix('.xml')
        tree=ET.parse(xml).getroot();declared=(int(tree.findtext('size/width')),int(tree.findtext('size/height')))
        with Image.open(jpg) as im:im.load();im=im.convert('RGB');assert im.size==declared==(image['width'],image['height'])
        draw=ImageDraw.Draw(im);annotations=[r for r in all_rows if r['role']=='train' and r['image_id']==image['id']]
        lines=[]
        for row in annotations:
            draw.line(row['original_polygon']+[row['original_polygon'][0]],fill='#87e6ac',width=4)
            if row['valid']:
                draw.rectangle(row['axis_box_xyxy'],outline='#ffbe69',width=3)
                lines.append(' '.join(str(v) if i==0 else f'{v:.9f}' for i,v in enumerate(row['yolo_class_cxcywh'])))
        xmlcow=[obj for obj in tree.findall('object') if obj.find('robndbox') is not None]
        mismatch=[];matches=[]
        for row in annotations:
            x,y,w,h,t=row['bbox_xywh_angle_radians'];cx=x+w/2;cy=y+h/2
            candidates=[]
            for obj in xmlcow:
                values=[float(obj.findtext('robndbox/'+k)) for k in ['cx','cy','w','h','angle']]
                distance=sum(abs(a-b) for a,b in zip([cx,cy,w,h],values[:4]))
                candidates.append((distance,values,obj.findtext('name')))
            distance,values,label=min(candidates)
            d=((t-values[4]+math.pi/2)%math.pi)-math.pi/2
            matches.append({'annotation_id':row['annotation_id'],'centre_and_size_L1_difference':distance,
                            'angle_mod_pi_difference_radians':abs(d),'XML_name':label})
            if distance>3 or abs(d)>.011:mismatch.append(matches[-1])
        target=out/'sample_overlays'/name;im.save(target,quality=93)
        (out/'sample_yolo'/Path(name).with_suffix('.txt')).write_text('\n'.join(lines)+'\n',encoding='utf-8')
        original=tree.findtext('filename');date_match=re.search(r'(\d{4}-\d{2}-\d{2})_(\d{1,2})-(\d{1,2})-(\d{1,2})',original or '')
        record={'file_name':name,'sampled_role':'train','source_jpeg_sha256':hashlib.sha256(jpg.read_bytes()).hexdigest(),
                'source_XML_sha256':hashlib.sha256(xml.read_bytes()).hexdigest(),'original_filename':original,
                'source_block':tree.findtext('folder'),'capture_timestamp':date_match.group(0) if date_match else None,
                'XML_JSON_geometric_matches':matches,'XML_JSON_mismatches_above_declared_rounding_tolerance':mismatch,
                'XML_zero_area_rotated_objects':sum(float(obj.findtext('robndbox/w'))<=0 or float(obj.findtext('robndbox/h'))<=0 for obj in xmlcow),
                'overlay':str(target.relative_to(ROOT)),'derived_classic_YOLO_rows':len(lines)}
        samples.append(record)
    sheet=Image.new('RGB',(3*480,4*300),(20,26,30));draw=ImageDraw.Draw(sheet)
    for i,r in enumerate(samples):
        x=i%3*480;y=i//3*300
        with Image.open(ROOT/r['overlay']) as im:tile=ImageOps.contain(im,(470,265));sheet.paste(tile,(x,y+25))
        draw.text((x+5,y+5),f'{r["file_name"]} TRAIN {r["source_block"]}',fill='white')
    sheet.save(out/'train_label_contact.jpg',quality=94)
    (out/'derived_box_catalog.json').write_text(json.dumps(all_rows,indent=2),encoding='utf-8')
    result={'status':'FULL_PUBLISHED_JSON_AND_12_TRAIN_XML_IMAGE_AUDIT_COMPLETE','geometry_controls':geometry_controls(),
            'roles':summaries,'total_published_images':10402,'total_published_annotations':len(all_rows),'train_samples':samples,
            'new_model_forward_or_training':False,'validation_or_test_pixels_opened':False,
            'derived_label_definition':'axis-aligned envelope of image-clipped published rotated cow-body polygon; source JSON retained',
            'rotated_detector_oriented_AP_not_equivalent':True,'source_session_split_verified':False,
            'full_source_metadata_recovery':'Separate XML-stage audit needed;12train samples expose original timestamps and block fields'}
    (out/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'status':result['status'],'roles':summaries,'sample_XML_mismatches':sum(len(r['XML_JSON_mismatches_above_declared_rounding_tolerance']) for r in samples),
                      'sample_timestamps':[r['capture_timestamp'] for r in samples]}),flush=True)


if __name__=='__main__':main()
