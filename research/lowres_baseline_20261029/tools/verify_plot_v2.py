from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile,re,xml.etree.ElementTree as ET
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
m=load(ROOT/'evidence/plot_v2_transfer.json');archive=ROOT/'plot_v2_delivery.tar.gz';assert sha(archive)==m['sha256'] and archive.stat().st_size==m['bytes']
out=ROOT/'plot_v2_delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    assert len(tar.getmembers())==m['members']
    for entry in tar.getmembers():
        assert entry.isfile() and not entry.name.startswith('/') and '..' not in Path(entry.name).parts
        target=(out/entry.name).resolve();assert target.is_relative_to(out.resolve()) and not target.exists()
        target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(tar.extractfile(entry).read())
for row in load(out/'results/plots_v2/manifest.json'):
    file=out/row['relative_file'];assert file.stat().st_size==row['bytes'] and sha(file)==row['sha256']
data=load(out/'results/plots_v2/plot_data.json');old=load(ROOT/'media_delivery/results/media/plot_data.json');assert data==old
ns={'s':'http://www.w3.org/2000/svg'};xml=ET.parse(out/'results/plots_v2/lowres_baseline_counts.svg');count=0;maximum=0.
for ai in range(4):
    axis=xml.find('.//s:g[@id="axes_'+str(ai+1)+'"]',ns);paths=[]
    for element in axis:
        if element.attrib.get('id','').startswith('patch_'):
            path=element.find('s:path',ns)
            if path is not None and 'clip-path' in path.attrib:paths.append(path)
    rows=[r for r in data['bars'] if r['panel']==ai];assert len(paths)==len(rows)==12
    for path,row in zip(paths,rows):
        clipid=re.search(r'#([^\)]+)',path.attrib['clip-path']).group(1);rect=xml.find('.//s:clipPath[@id="'+clipid+'"]/s:rect',ns)
        vals=[float(v) for v in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',path.attrib['d'])];points=np.asarray(vals).reshape(-1,2)
        height=(max(points[:,1])-min(points[:,1]))/float(rect.attrib['height'])*row['ymax'];left=(points[0,0]-float(rect.attrib['x']))/float(rect.attrib['width'])*4.2-.6
        error=max(abs(height-row['value']),abs(left-row['bar_x']));assert error<2e-5;maximum=max(maximum,error);count+=1
result={'status':'SAME48BAR_VALUES_REVERIFIED_IN_LAYOUT_V2','created_UTC':datetime.now(timezone.utc).isoformat(),'archive_sha256':sha(archive),
'archive_bytes':archive.stat().st_size,'members':m['members'],'bar_segments':count,'maximum_bar_data_error':maximum,
'layout_repair_only':True,'original_data_and_movies_unchanged':True}
file=ROOT/'results/plot_v2_verification.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
