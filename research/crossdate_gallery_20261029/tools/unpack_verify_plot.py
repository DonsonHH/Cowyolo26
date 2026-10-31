from pathlib import Path
import json,hashlib,tarfile,re,xml.etree.ElementTree as ET
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=json.loads((ROOT/'evidence/plot_transfer.json').read_text());archive=ROOT/'plots_delivery.tar.gz'
assert sha(archive)==m['sha256'] and archive.stat().st_size==m['bytes']
out=ROOT/'plot_delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    members=tar.getmembers();assert len(members)==m['members']
    for item in members:
        assert item.isfile() and not item.name.startswith('/') and '..' not in Path(item.name).parts
        file=(out/item.name).resolve();assert file.is_relative_to(out.resolve());assert not file.exists()
        file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(tar.extractfile(item).read())
manifest=json.loads((out/'results/plots/manifest.json').read_text())
for row in manifest:assert sha(out/row['relative_file'])==row['sha256'] and (out/row['relative_file']).stat().st_size==row['bytes']
data=json.loads((out/'results/plots/plot_data.json').read_text())
metrics=json.loads((ROOT/'results/independent_verification.json').read_text())['metrics'];assert len(data['rows'])==len(metrics)==10
for r,mr in zip(data['rows'],metrics):
    assert r['condition']==mr['condition'] and r['gallery']==mr['gallery_condition']
    assert [r[k] for k in ['C','W','U','F']]==[mr[k] for k in ['known_correct_accepted_C','known_wrong_accepted_W','known_rejected_U','unknown_false_accepts']]
xml=ET.parse(out/'results/plots/gallery_date_risk.svg');ns={'s':'http://www.w3.org/2000/svg'};width_deltas=[]
for ai,panel,n in [('axes_1','registered',30),('axes_2','unknown',10)]:
    axis=xml.find('.//s:g[@id="'+ai+'"]',ns);rectangles=[]
    for child in axis:
        if child.attrib.get('id','').startswith('patch_'):
            path=child.find('s:path',ns)
            if path is not None and 'clip-path' in path.attrib:rectangles.append(path)
    assert len(rectangles)==n
    expected=[r for r in data['bars'] if r['panel']==panel]
    for path,r in zip(rectangles,expected):
        clipid=re.search(r'#([^\)]+)',path.attrib['clip-path']).group(1)
        rect=xml.find('.//s:clipPath[@id="'+clipid+'"]/s:rect',ns)
        points=[float(v) for v in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',path.attrib['d'])]
        assert len(points)==8
        xwidth=(points[2]-points[0])*30/float(rect.attrib['width'])
        xleft=(points[0]-float(rect.attrib['x']))*30/float(rect.attrib['width'])
        assert abs(xwidth-r['width'])<1e-5 and abs(xleft-r['left'])<1e-5
        width_deltas.append(abs(xwidth-r['width']))
with Image.open(out/'results/plots/gallery_date_risk.png') as im:im.load();size=list(im.size)
result={'status':'PLOT_TRANSFER_AND40_ACTUAL_SVG_SEGMENTS_MATCH_INDEPENDENT_METRICS','members':len(members),'manifest_files':len(manifest),
'PNG_size':size,'image_panels':2,'SVG_segments_verified':len(width_deltas),'maximum_SVG_count_width_error':max(width_deltas),'metric_rows':10,
'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,'human_identity_truth_inferred':False,'whole_goal_complete':False}
file=ROOT/'results/plot_verification.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result))
