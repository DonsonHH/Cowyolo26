from pathlib import Path
import urllib.request,json,hashlib,tarfile
ROOT=Path(__file__).resolve().parent
url='https://pypi.org/pypi/lap/0.5.13/json'
with urllib.request.urlopen(url,timeout=30) as response:metadata=json.load(response)
record=next(x for x in metadata['urls'] if x['packagetype']=='sdist')
file=ROOT/record['filename'];assert not file.exists()
with urllib.request.urlopen(record['url'],timeout=30) as response:contents=response.read()
assert len(contents)==record['size'] and hashlib.sha256(contents).hexdigest()==record['digests']['sha256']
file.write_bytes(contents)
with tarfile.open(file) as tar:
 for name in tar.getnames():
  if name.endswith(('setup.py','pyproject.toml')):
   print(name);print(tar.extractfile(name).read().decode()[:11000])
(ROOT/'lap_source_provenance.json').write_text(json.dumps({'metadata_URL':url,'source_URL':record['url'],'version':'0.5.13',
 'file':file.name,'bytes':len(contents),'sha256':record['digests']['sha256'],'downloaded_source_only':True,'executed':False},indent=2)+'\n')
