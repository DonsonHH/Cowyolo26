from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re,xml.etree.ElementTree as ET
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;MEDIA=ROOT/'delivery/results/media';OUT=ROOT/'delivery/results/audit'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
rows=load(OUT/'objects.json');data=load(MEDIA/'media_values.json');selected=load(MEDIA/'selected_examples.json')
for row in load(MEDIA/'manifest.json'):
    f=MEDIA/row['file'];assert sha(f)==row['sha256'] and f.stat().st_size==row['bytes']
xml=ET.parse(MEDIA/'training_coverage_histograms.svg');ns={'s':'http://www.w3.org/2000/svg'}
def tick_mapping(axis,kind):
    ticks=[]
    for g in axis.findall('.//s:g',ns):
        if not g.attrib.get('id','').startswith(kind+'tick_'):continue
        text=g.find('.//s:text',ns);mark=g.find('.//s:use',ns)
        if text is None or mark is None:continue
        label=''.join(text.itertext()).strip().replace('\u2212','-')
        try:value=float(label)
        except ValueError:continue
        coord=float(mark.attrib[kind]);ticks.append((value,coord))
    assert len(ticks)>=2
    a,b=next((a,b) for a in ticks for b in ticks if a[0]!=b[0])
    scale=(b[1]-a[1])/(b[0]-a[0]);offset=a[1]-a[0]*scale
    for value,coord in ticks:assert abs(coord-(value*scale+offset))<2e-5
    return scale,offset
bars=0;maxbar=0.
for record in data['histograms']:
    vals=[r[record['key']] for r in rows if r[record['key']] is not None]
    counts,edges=np.histogram(vals,bins=record['edges']);assert counts.tolist()==record['counts'] and sum(counts)==record['samples']
    axis=xml.find('.//s:g[@id="axes_'+str(record['panel']+1)+'"]',ns)
    sx,ox=tick_mapping(axis,'x');sy,oy=tick_mapping(axis,'y');paths=[]
    for g in axis:
        if g.attrib.get('id','').startswith('patch_'):
            p=g.find('s:path',ns)
            if p is not None and 'clip-path' in p.attrib:paths.append(p)
    assert len(paths)==len(counts)
    for i,(path,count) in enumerate(zip(paths,counts)):
        points=np.asarray([float(n) for n in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',path.attrib['d'])]).reshape(-1,2)
        height=float(np.ptp(points[:,1]));value=height/abs(sy)
        delta=max(abs(value-int(count)),abs(points[:,0].min()-(edges[i]*sx+ox)))
        assert delta<2e-4;maxbar=max(maxbar,delta);bars+=1
used=set();expected=[]
for category,key,reverse in [('low_luminance','Y_median',False),('low_background_contrast','absolute_median_contrast',False),('rectangle_overlap','max_overlap_over_min_area',True),('small192_shortside','short_side_at192',False)]:
    group=[]
    for row in sorted([r for r in rows if r[key] is not None],key=lambda r:((-r[key]) if reverse else r[key],r['annotation_key'])):
        if row['annotation_key'] in used:continue
        used.add(row['annotation_key']);group.append(row['annotation_key'])
        if len(group)==3:break
    expected.extend(group)
assert expected==[r['annotation_key'] for r in selected] and len(expected)==12
source=PROJECT/'cows2021_labels_20261027/source_XML/train/02191.xml'
metadata=next(r for r in load(PROJECT/'cows2021_adaptation_20261027/input/source_metadata_all.json') if r['role']=='train' and r['file_name']=='02191.jpg')
assert sha(source)==metadata['XML_sha256'] and source.stat().st_size==metadata['XML_bytes']
tree=ET.parse(source);bodies=[]
for obj in tree.findall('object'):
    if obj.findtext('name')=='cow':
        b=obj.find('robndbox');bodies.append({key:float(b.findtext(key)) for key in ['cx','cy','w','h','angle']})
assert len(bodies)==3 and bodies[0]['w']==bodies[1]['w'] and bodies[0]['h']==bodies[1]['h'] and bodies[0]['angle']==bodies[1]['angle']
assert [bodies[0][k]-bodies[1][k] for k in ['cx','cy']]==[2.,2.]
pairs=load(OUT/'polygon_pairs.json');high=[r for r in pairs if r['polygon_IoU']>=.5]
assert len(high)==1 and high[0]['file_name']=='02191.jpg'
flag={'status':'ONE_NEAR_DUPLICATE_BODY_PAIR_PRESENT_IN_ORIGINAL_PUBLISHER_XML_NOT_INTRODUCED_BY_PIPELINE',
    'created_UTC':datetime.now(timezone.utc).isoformat(),'file_name':'02191.jpg','XML_source_url':metadata['XML_url'],
    'XML_path':str(source.resolve()),'XML_sha256':sha(source),'XML_verified_attribute':tree.getroot().attrib.get('verified'),
    'cow_objects':bodies,'derived_training_pair':high[0],'high_overlap_pairs_over_all_training':1,'exact_identical_parameter_duplicates':0,
    'interpretation':'visually_highly_suspected_duplicate_same_body;retain_review_flag_not_automatic_truth_or_automatic_deletion',
    'labels_removed_or_changed':0,'new_model_forwards':0,'whole_goal_complete':False}
p=ROOT/'results/publisher_annotation_flag.json';assert not p.exists();p.write_text(json.dumps(flag,indent=2)+'\n',encoding='utf-8')
result={'status':'ALL_HISTOGRAM_SVG_BARS12_SELECTIONS_AND_SOURCE_XML_FLAG_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),
    'SVG_histogram_bars':bars,'maximum_SVG_bar_value_or_position_error':maxbar,'example_panels':12,
    'histogram_observations':sum(r['samples'] for r in data['histograms']),'XML_pair_provenance_verified':True,
    'expected_figures_to_actually_view':2,'expected_panels_to_actually_view':16,'labels_removed_or_changed':0,'new_model_forwards':0,'whole_goal_complete':False}
p=ROOT/'results/media_and_XML_verification.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
print(json.dumps(result))
