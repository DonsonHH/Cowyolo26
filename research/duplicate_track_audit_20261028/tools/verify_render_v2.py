from pathlib import Path,PurePosixPath
import hashlib,json,tarfile
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    record=load(ROOT/'results/render_v2_delivery_record.json');archive=ROOT/'results/render_v2_delivery.tar.gz';dest=ROOT/'render_v2_delivery';assert not dest.exists()
    assert sha(archive)==record['sha256'] and archive.stat().st_size==record['bytes']
    with tarfile.open(archive,'r:gz') as tf:
        raw=tf.extractfile('delivery_manifest.json').read();assert hashlib.sha256(raw).hexdigest()==record['manifest_sha256']
        rows=json.loads(raw);expected={r['path']:r for r in rows};members=tf.getmembers()
        assert len(rows)==len(expected)==record['manifest_files']==19 and len(members)==record['archive_members']==20
        assert {m.name for m in members}==set(expected)|{'delivery_manifest.json'}
        for m in members:
            name=PurePosixPath(m.name);assert m.isfile() and not name.is_absolute() and '..' not in name.parts and ':' not in m.name
            path=dest.joinpath(*name.parts).resolve();assert path.is_relative_to(dest.resolve());data=tf.extractfile(m).read()
            if m.name in expected:assert len(data)==expected[m.name]['bytes'] and hashlib.sha256(data).hexdigest()==expected[m.name]['sha256']
            path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(data);assert sha(path)==hashlib.sha256(data).hexdigest()
    r=load(dest/'results/render_record_v2.json');a=load(ROOT/'results/audit.json');q=load(ROOT/'protocol/render_v1.json')
    assert r['audit_sha256']==sha(ROOT/'results/audit.json') and r['source_sha256']==q['source_sha256']
    assert sha(ROOT/'tools/render_v2.py')==sha(dest/'tools/render_v2.py') and sha(ROOT/'protocol/render_v1.json')==sha(dest/'protocol/render_v1.json')
    fields=['high_overlap_pair_frames','GT_primary_supported_pair_frames','GT_sensitivity_supported_pair_frames']
    assert r['bar_fields']==fields and r['bar_values']==[[c[k] for c in a['conditions']] for k in fields]
    for t in r['timeline']:
        rows=[d for d in a['all_high_overlap_pairs'] if d['condition']==t['condition']]
        frames=sorted({d['frame'] for d in rows});assert frames==t['distinct_frames']
        expected=[2 if any(d['frame']==f and d['primary_same_GT'] for d in rows) else 1 if any(d['frame']==f and d['sensitivity_same_GT'] for d in rows) else 0 for f in frames]
        assert expected==t['support_color_class']
    decoded=[]
    for row in r['output_files']:
        f=dest/'results/figures_v2'/row['path'];assert sha(f)==row['sha256'] and f.stat().st_size==row['bytes']
        if f.suffix in ['.png','.jpg']:
            with Image.open(f) as im:im.load();decoded.append({'file':f.name,'size':list(im.size)})
        elif f.suffix=='.svg':
            import xml.etree.ElementTree as ET
            assert ET.parse(f).getroot().tag.endswith('svg')
        elif f.suffix=='.pdf':assert f.read_bytes().startswith(b'%PDF')
    assert len(decoded)==13 and len(r['output_files'])==15 and len(r['representative_crops'])==6
    result={'status':'ALL19_RENDER_FILES_13_RASTERS_AND_EXACT_BAR_TIMELINE_DATA_VERIFIED',
       'files':19,'raster_full_decodes':13,'native_frames':[120,323,345,421],
       'audit_sha256':sha(ROOT/'results/audit.json'),'render_record_sha256':sha(dest/'results/render_record_v2.json'),
       'representative_cases':6,'special_cases':2,'outputs':decoded,'plot_data_exact':True,
       'manual_visual_QA':'PENDING','new_inference':False,'new_independent_reference':False}
    target=ROOT/'results/render_v2_local_verification.json';assert not target.exists();target.write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result))
if __name__=='__main__':main()
