from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
from urllib.parse import unquote
import gzip,hashlib,json,re,subprocess
C=Path(__file__).resolve().parent;R=C/'repo'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
status=json.loads((R/'archive_inventory/ARCHIVE_STATUS.json').read_text(encoding='utf-8'))
assert status['all_requested_scopes_collected']
with gzip.open(R/'archive_inventory/selected_files.jsonl.gz','rt',encoding='utf-8')as f:rows=[json.loads(line)for line in f]
assert len(rows)==status['selected_original_files']
for row in rows:
 p=R/row['repository_path'];assert p.stat().st_size==row['bytes']and sha(p)==row['sha256'],row['repository_path']
with gzip.open(R/'archive_inventory/readable_copies.jsonl.gz','rt',encoding='utf-8')as f:derivatives=[json.loads(line)for line in f]
for row in derivatives:assert sha(R/row['source'])==row['source_sha256']and sha(R/row['readable_copy'])==row['readable_copy_sha256']
bad_models=[];credentials=[];weak=[];files=[]
strong=[re.compile(rb'\bgh[pousr]_[A-Za-z0-9]{30,255}\b'),re.compile(rb'github_pat_[A-Za-z0-9_]{40,255}'),re.compile(rb'-----BEGIN (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----[\s\S]{100,12000}?-----END (?:RSA |OPENSSH |EC |DSA )?PRIVATE KEY-----')]
for p in R.rglob('*'):
 if not p.is_file()or'.git'in p.relative_to(R).parts:continue
 rel=p.relative_to(R).as_posix();files.append(p)
 if p.suffix.lower()in{'.pt','.pth','.onnx','.bin','.npy','.npz','.safetensors','.bit','.so','.dll','.pyd','.mp4'}:bad_models.append(rel)
 if p.stat().st_size>90*1024*1024:raise AssertionError(('too_large_for_review',rel))
 if p.suffix.lower()in{'.md','.txt','.json','.jsonl','.yaml','.yml','.py','.sh','.html','.log','.out','.err'}:
  data=p.read_bytes()
  if any(regex.search(data)for regex in strong):credentials.append(rel)
  if p.suffix.lower()=='.json':
   for m in re.finditer(rb'"(access_token|authorization|cookie|password|secret|api_key)"\s*:\s*"([^"\n]+)"',data,re.I):
    v=m[2]
    if len(v)>12 and not any(w in v.lower()for w in[b'redact',b'environ',b'example',b'placeholder',b'prompt',b'not_saved',b'not-saved']):weak.append({'path':rel,'field':m[1].decode(),'line':data[:m.start()].count(b'\n')+1})
assert not bad_models,bad_models
assert not credentials,credentials
broken=[];links=0
documents=list((R/'docs').rglob('*.md'))+[R/n for n in['README.md','HANDOFF.md','STAGE_INDEX.md','ARCHIVE_CONTENTS.md','NOTICES.md']]
for p in documents:
 for m in re.finditer(r'\]\((?:<([^>]+)>|([^\)]+))\)',p.read_text(encoding='utf-8')):
  target=unquote((m[1]or m[2]).strip())
  if target.startswith(('http://','https://','mailto:','#')):continue
  path=target.partition('#')[0]
  if not(p.parent/path).exists():broken.append({'document':str(p.relative_to(R)),'target':target})
  links+=1
assert not broken,broken[:20]
result={'status':'SELECTED_ORIGINAL_HASHES_READABLE_LINKS_AND_NO_MODEL_DATA_PAYLOAD_AUDITED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'selected_originals':len(rows),'readable_copies':len(derivatives),
 'repository_files_before_audit':len(files),'repository_bytes_before_audit':sum(p.stat().st_size for p in files),
 'internal_readable_links_checked':links,'broken_readable_links':0,'model_dataset_binary_files':0,
 'strong_credential_findings':0,'additional_credential_fields_requiring_review':weak,
 'source_scopes':status['source_scopes'],'new_experiments':0,'user_requested_automatic_research_stop':True}
with(R/'archive_inventory/archive_audit.json').open('w',encoding='utf-8')as f:json.dump(result,f,ensure_ascii=False,indent=2);f.write('\n')
print(json.dumps({k:v for k,v in result.items()if k!='source_scopes'},ensure_ascii=False))
