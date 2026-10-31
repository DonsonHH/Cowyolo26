from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from concurrent.futures import ThreadPoolExecutor
from collections import defaultdict
from datetime import datetime,timezone
from PIL import Image
import json,hashlib,zlib,io,math
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists(),p;p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def fetch(row):
    target=ROOT/row['relative_file'];assert not target.exists();target.parent.mkdir(parents=True,exist_ok=True)
    opener=build_opener(ProxyHandler({}))
    with opener.open(Request(row['url'],headers={'User-Agent':'cow-crop-domain-fixed-validation/1.0'}),timeout=45) as response:
        assert response.status==200;data=response.read(2*1024*1024+1);assert len(data)<=2*1024*1024
    assert len(data)==row['official_bytes'] and zlib.crc32(data)&0xffffffff==row['official_CRC32'] and hashlib.sha1(data).hexdigest()==row['official_SHA1']
    with Image.open(io.BytesIO(data)) as im:
        im.load();assert im.format=='JPEG';im=im.convert('RGB');pixel=hashlib.sha256(im.tobytes()).hexdigest();width,height=im.size
    target.write_bytes(data)
    return {**row,'query_id':row['relative_file'],'path':'/share/home/renly/projects/idcoo_research_20261026/crop_domain_20261029/'+row['relative_file'],
    'local_path':str(target.resolve()),'sha256':sha(target),'pixel_sha256':pixel,'width':width,'height':height}
def main():
    p=load(ROOT/'protocol/study_v1.json')
    for name,digest in p['input_metadata_sha256'].items():assert sha(ROOT/'input'/name)==digest
    with ThreadPoolExecutor(max_workers=4) as pool:new=list(pool.map(fetch,load(ROOT/'input/new_validation_gallery_selection.json')))
    groups={'validation_gallery':new}
    for name in ['validation_query','evaluation_gallery','evaluation_query','real_event_query']:
        groups[name]=load(ROOT/'input'/(name+'.json'))
        for row in groups[name]:
            if 'query_id' not in row:row['query_id']=row['relative_file']
    pixels=defaultdict(list);bytesha=defaultdict(list);decoded=[]
    for group,rows in groups.items():
        for row in rows:
            file=Path(row['local_path']);assert sha(file)==row['sha256']
            with Image.open(file) as im:im.load();im=im.convert('RGB');pixel=hashlib.sha256(im.tobytes()).hexdigest();size=list(im.size)
            entry={'group':group,'query_id':row['query_id'],'local_path':str(file.resolve()),'source_sha256':row['sha256'],'pixel_sha256':pixel,'dimensions':size}
            decoded.append(entry);pixels[pixel].append(entry);bytesha[row['sha256']].append(entry)
    crosspixel=[r for r in pixels.values() if len({x['group'] for x in r})>1];crossbytes=[r for r in bytesha.values() if len({x['group'] for x in r})>1]
    assert not crosspixel and not crossbytes and len(decoded)==182
    roles=[set(p[k]) for k in ['validation_registered_IDs','validation_unknown_IDs','evaluation_registered_IDs','evaluation_unknown_IDs','gradient_training_IDs']]
    assert all(not a&b for i,a in enumerate(roles) for b in roles[i+1:])
    geometric=load(PROJECT/'identity_source_provenance_20261029/refined_delivery/results/geometry_refined/top_results.json');direction=[]
    for template in geometric:
        if template['gallery']['published_anonymous_ID']=='009' and template['gallery']['filename'] in ['00024_1.jpg','00039_1.jpg','00054_1.jpg']:
            r=template['top'][0];assert r['geometry_pass'] and r['NCC']>.99
            h=r['homography_template_to_native'];x=(template['gallery']['width']-1)/2;y=(template['gallery']['height']-1)/2
            n0=h[0][0]*x+h[0][1]*y+h[0][2];n1=h[1][0]*x+h[1][1]*y+h[1][2];d=h[2][0]*x+h[2][1]*y+h[2][2]
            dx=(h[0][0]*d-n0*h[2][0])/d**2;dy=(h[1][0]*d-n1*h[2][0])/d**2
            current=math.degrees(math.atan2(-dx,dy));opposite=math.degrees(math.atan2(dx,-dy))
            direction.append({'gallery_filename':template['gallery']['filename'],'source_frame0':r['source_frame0'],'NCC':r['NCC'],
            'native_template_positive_x_axis_deg':math.degrees(math.atan2(dy,dx)),'after_current_PIL_ROTATE90_residual_deg':current,
            'after_opposite_PIL_ROTATE270_residual_deg':opposite,'source_homography':h})
    assert len(direction)==3 and all(abs(r['after_current_PIL_ROTATE90_residual_deg'])<25 for r in direction)
    save(ROOT/'results/direction_audit.json',{'status':'THREE_STRONG_SOURCE_TRANSFORMS_SUPPORT_EXISTING90CCW_NOT180REVERSAL',
    'pairs':direction,'scope':'KnownsamepassageID009only;notallcowsheadorientation,notcropselectionoridentitytraininglabel.',
    'author_paper_URL':p['author_paper_URL'],'capture_rotation_source_sha256':sha(PROJECT/'confirmed12_capture_identity_20261029/tools/run_chain.py'),
    'reID_forward_calls':0,'identity_truth_promoted':False})
    save(ROOT/'results/input_audit.json',{'status':'OFFICIAL25_NEW_VALIDATION_GALLERY_AND182_INPUT_IMAGES_DECODED_NO_EXACT_CROSS_ROLE_DUPLICATES',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(ROOT/'protocol/study_v1.json'),'groups':groups,
    'new_gallery_bytes':sum(r['official_bytes'] for r in new),'decoded_input_images':decoded,
    'total_images':182,'cross_role_pixel_duplicates':crosspixel,'cross_role_byte_duplicates':crossbytes,
    'all_identity_roles_mutually_disjoint':True,'evaluation_role_images_during_input_integrity_audit_only_not_model_selection':True,
    'new_model_forwards':0,'whole_goal_complete':False})
    print(json.dumps({'new_images':25,'total_images':182,'new_gallery_bytes':sum(r['official_bytes'] for r in new),
    'direction_residuals_degrees':[r['after_current_PIL_ROTATE90_residual_deg'] for r in direction]}))
if __name__=='__main__':main()
