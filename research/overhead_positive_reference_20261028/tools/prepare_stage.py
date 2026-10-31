from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
previous=PROJECT/'overhead_long_session_20261028';protocol=previous/'protocol/positive_candidate_v1.json'
p=json.loads(protocol.read_text(encoding='utf-8'));manifest=previous/'input/positive_video_ranges/manifest.json';m=json.loads(manifest.read_text(encoding='utf-8'))
source=Path(m['local_path']);assert sha(source)==m['source_sha256']=='8210a5bf206dd7f2356bc3d4653b439ab6de12ccfdc8209fe301ac7f02807058'
assert m['source_bytes']==source.stat().st_size==260358184
out=ROOT/'protocol';out.mkdir(exist_ok=False);input_dir=ROOT/'input';input_dir.mkdir(exist_ok=False)
p.update(name='Cow-present ordinary-overhead long source: full native admission and pre-model event reference preparation',
         upstream_protocol_sha256=sha(protocol),upstream_manifest_sha256=sha(manifest),upstream_source_bytes=m['source_bytes'],upstream_source_sha256=m['source_sha256'])
(out/'selection_v1.json').write_text(json.dumps(p,indent=2),encoding='utf-8');(input_dir/'video_manifest.json').write_bytes(manifest.read_bytes())
rows=[]
for name in ['prepare_native_review.py','diagnose_decode.py']:
    src=previous/'tools'/name;b=src.read_text(encoding='utf-8')
    old='/idcoo_research_20261026/overhead_long_session_20261028';new='/idcoo_research_20261026/overhead_positive_reference_20261028'
    assert b.count(old)==1
    dst=ROOT/'tools'/name;assert not dst.exists();dst.write_text(b.replace(old,new),encoding='utf-8')
    rows.append({'file':name,'upstream_sha256':sha(src),'adapted_sha256':sha(dst),'only_change':'ROOT directory literal'})
(out/'source_adaptation.json').write_text(json.dumps({'files':rows,'models_used':False},indent=2),encoding='utf-8')
print(json.dumps({'source':str(source),'source_sha256':sha(source),'adapted_sources':rows}),flush=True)
