"""Verify actual SVG bar geometry and all30 displayed input-source links."""
from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re,xml.etree.ElementTree as ET
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'delivery/results/study_v2';MEDIA=ROOT/'delivery/results/media'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
for row in load(MEDIA/'manifest.json'):
    f=MEDIA/row['file'];assert sha(f)==row['sha256'] and f.stat().st_size==row['bytes']
data=load(MEDIA/'media_values.json');s=load(OUT/'summary.json')
xml=ET.parse(MEDIA/'all_photometric_controls.svg');ns={'s':'http://www.w3.org/2000/svg'}
checked=0;maxerror=0.
for panel in range(4):
    axis=xml.find('.//s:g[@id="axes_'+str(panel+1)+'"]',ns);paths=[]
    for element in axis:
        if element.attrib.get('id','').startswith('patch_'):
            path=element.find('s:path',ns)
            if path is not None and 'clip-path' in path.attrib:paths.append(path)
    rows=[r for r in data['bars'] if r['panel']==panel]
    assert len(rows)==len(paths)==(12 if panel==3 else 6)
    ymax=[2100,max(r['value'] for r in rows)*1.2,14,7][panel]
    for row,path in zip(rows,paths):
        if panel<2:
            value=next(r[row['metric']] for r in s['validation_metrics'] if r['condition']==row['condition'] and r['mode']==row['mode'])
        else:
            source=next(r for r in s['video_metrics'] if r['condition']==row['condition'] and r['mode']==row['mode'] and r['counter']=='handoff_events' and
                r['scene']==('original' if panel==2 else 'toros') and r['stride']==(5 if panel==2 else row['stride']))
            value=source['down'] if panel==2 else source['formal_event_metrics']['TP']
        assert value==row['value']
        clip=re.search(r'#([^\)]+)',path.attrib['clip-path']).group(1)
        rect=xml.find('.//s:clipPath[@id="'+clip+'"]/s:rect',ns)
        xy=np.asarray([float(n) for n in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',path.attrib['d'])]).reshape(-1,2)
        height=np.ptp(xy[:,1])/float(rect.attrib['height'])*ymax
        x=(xy[0,0]-float(rect.attrib['x']))/float(rect.attrib['width'])*3.2-.6
        error=max(abs(height-value),abs(x-row['x']));assert error<3e-5;maxerror=max(maxerror,error);checked+=1
assert checked==30
anchors=load(OUT/'pixel_controls.json');panels=0;minimum_pixel_agreement=1.
for scene in ['original','toros']:
    with Image.open(MEDIA/(scene+'_actual_inputs_QDQ_boxes.png')) as img:
        img.load()
        assert img.width==1220 and img.height==(2775 if scene=='original' else 1905)
        for row in [p for p in data['input_panels'] if p['scene']==scene]:
            anchor=next(r for r in anchors if r['scene']==scene and r['condition']==row['condition'] and r['frame0']==row['frame0'])
            assert row['source_pixel_file']==anchor['pixel_file'] and row['source_pixel_sha256']==anchor['pixel_sha256']==sha(OUT/anchor['pixel_file'])
            with np.load(OUT/anchor['array_file']) as arrays:
                assert arrays['QDQ'][arrays['QDQ'][:,4]>=.2].tolist()==row['QDQ_boxes']
            native=Image.open(OUT/anchor['pixel_file']).convert('RGB').resize((384,384),Image.Resampling.NEAREST)
            x,y,w,h=row['rect'];actual=np.array(img.crop((x,y,x+w,y+h)));reference=np.array(native)
            same=float(np.mean(np.all(actual==reference,axis=2)))
            assert same>.8,(scene,row['frame0'],row['condition'],same)
            minimum_pixel_agreement=min(minimum_pixel_agreement,same);panels+=1
assert panels==30
result={'status':'THIRTY_ACTUAL_SVG_BAR_HEIGHTS_AND_THIRTY_INPUT_PANEL_SOURCE_LINKS_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),
    'SVG_bars':checked,'maximum_bar_geometry_error':maxerror,'input_panels':panels,
    'minimum_source_pixel_agreement_despite_QDQ_box_overlays':minimum_pixel_agreement,
    'overlay_box_values_match_saved_raw':True,'figures_to_actually_view':3,'panels_to_actually_view':34,
    'new_network_forwards':0,'whole_goal_complete':False}
file=ROOT/'results/media_verification.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
