"""Download an official TorchVision checkpoint only, with content hash guard."""
from pathlib import Path
from urllib.request import build_opener,ProxyHandler,Request
import hashlib,json
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/identity_baseline')
ROOT.joinpath('models').mkdir(parents=True,exist_ok=True)
url='https://download.pytorch.org/models/mobilenet_v3_small-047dcff4.pth'
dest=ROOT/'models/mobilenet_v3_small-047dcff4.pth'
if dest.exists():raise FileExistsError(dest)
opener=build_opener(ProxyHandler({}))
temporary=dest.with_suffix('.pth.partial')
with opener.open(Request(url,headers={'User-Agent':'cattle-research/1.0'}),timeout=45) as response,temporary.open('xb') as output:
    while data:=response.read(1024*1024):output.write(data)
digest=hashlib.sha256(temporary.read_bytes()).hexdigest()
assert digest.startswith('047dcff4') and temporary.stat().st_size>9_000_000
temporary.rename(dest)
record={'url':url,'file':str(dest),'bytes':dest.stat().st_size,'sha256':digest,'expected_hash_prefix':'047dcff4'}
(ROOT/'models/checkpoint_record.json').write_text(json.dumps(record,indent=2))
print(json.dumps(record),flush=True)
