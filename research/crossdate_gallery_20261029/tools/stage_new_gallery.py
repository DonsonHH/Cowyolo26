from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from concurrent.futures import ThreadPoolExecutor
from PIL import Image
from datetime import datetime,timezone
from collections import defaultdict,Counter
import hashlib,io,json,zlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def fetch(row):
    file=ROOT/row['relative_file'];assert not file.exists();file.parent.mkdir(parents=True,exist_ok=True)
    op=build_opener(ProxyHandler({}))
    with op.open(Request(row['url'],headers={'User-Agent':'cow-crossdate-gallery-fixed-selection/1.0'}),timeout=40) as response:
        data=response.read(2*1024*1024+1);assert len(data)<=2*1024*1024 and response.status==200
        final_url=response.url
    assert len(data)==row['official_bytes'] and zlib.crc32(data)&0xffffffff==row['official_CRC32']
    assert hashlib.sha1(data).hexdigest()==row['official_SHA1']
    with Image.open(io.BytesIO(data)) as im:
        im.load();assert im.format=='JPEG';image=im.convert('RGB');size=list(image.size);pixels=hashlib.sha256(image.tobytes()).hexdigest()
    file.write_bytes(data)
    return {**row,'path':'/share/home/renly/projects/idcoo_research_20261026/crossdate_gallery_20261029/'+row['relative_file'],
            'local_path':str(file.resolve()),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),
            'pixel_sha256':pixels,'width':size[0],'height':size[1],'final_url':final_url}
def main():
    p=load(ROOT/'protocol/study_v1.json');selection=load(ROOT/'input/new_gallery_selection.json')
    assert len(selection)==30 and sha(ROOT/'input/new_gallery_selection.json')==p['input_module_sha256']['new_gallery_selection.json']
    with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(fetch,selection))
    other=load(ROOT/'input/old_gallery.json')+load(ROOT/'input/labelled_queries.json')+load(ROOT/'input/real_event_queries.json')
    pixels=defaultdict(list);byte_hashes=defaultdict(list)
    for row in [*rows,*other]:
        file=Path(row['local_path']);assert sha(file)==row['sha256']
        with Image.open(file) as im:im.load();image=im.convert('RGB');pixel=hashlib.sha256(image.tobytes()).hexdigest()
        group='new_Aug19' if row.get('gallery_name')=='new_Aug19' else row['input_kind']
        pixels[pixel].append({'group':group,'file':str(file.resolve())});byte_hashes[row['sha256']].append({'group':group,'file':str(file.resolve())})
    cross_pixel=[r for r in pixels.values() if len({x['group'] for x in r})>1]
    cross_bytes=[r for r in byte_hashes.values() if len({x['group'] for x in r})>1]
    assert not cross_pixel and not cross_bytes,'Do not run model with exact cross-role duplicate inputs'
    original_protocol=load(PROJECT/'identity_training_20261026/protocol/identity_training_v1.json')
    assert not set(p['registered_IDs'])&set(original_protocol['training_ids'])
    assert {r['identity'] for r in load(ROOT/'input/labelled_queries.json') if r['role']=='evaluation_registered_ids'}==set(p['registered_IDs'])
    registered=[r for r in load(ROOT/'input/labelled_queries.json') if r['identity'] in p['registered_IDs']]
    unknown=[r for r in load(ROOT/'input/labelled_queries.json') if r['identity'] not in p['registered_IDs']]
    assert len(registered)==len(unknown)==30 and not {r['identity'] for r in unknown}&set(p['registered_IDs'])
    result={'status':'NEW30_AUG19_GALLERY_RELEASE_HASHES_FULL_DECODE_AND132_INPUT_CROSS_ROLE_DUPLICATES_VERIFIED',
        'created_UTC':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(ROOT/'protocol/study_v1.json'),
        'new_images':rows,'new_image_count':30,'new_image_bytes':sum(r['bytes'] for r in rows),'full_decoded_input_images':len(rows)+len(other),
        'exact_cross_role_pixel_duplicate_groups':cross_pixel,'exact_cross_role_byte_duplicate_groups':cross_bytes,
        'registered_IDs_not_gradient_training_IDs':True,'labelled_known_query_images':30,'labelled_unknown_query_images':30,
        'new_gallery_vs_source_event_dates':['2023Aug19','2023Aug14'],'retrospective_only_for_source_event_queries':True,
        'new_gallery_day_precedes_labelled_query_day':True,'new_model_forwards':0,'new_training_updates':0,
        'new_independent_test':False,'whole_goal_complete':False}
    out=ROOT/'results';out.mkdir(exist_ok=False);path=out/'input_audit.json';assert not path.exists();path.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='new_images'}))
if __name__=='__main__':main()
