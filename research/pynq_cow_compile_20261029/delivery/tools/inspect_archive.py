"""Read only the explicitly located O8 release archive; do not execute it."""
from pathlib import Path
from datetime import datetime,timezone
from zipfile import ZipFile
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
archive=Path('C:/Users/Donson/xwechat_files/wxid_nzrjpu4f1bn112_bb67/msg/file/2026-10/optimization_8_release_20261019_181244.zip')
with archive.open('rb') as f:digest=hashlib.file_digest(f,'sha256').hexdigest()
assert digest=='e7f4d7f07ab935a15972157d4c101811eb5e9946e60f510dd5639226e2b2cef5'
rows=[]
with ZipFile(archive) as z:
    names=z.namelist()
    chosen=[n for n in names if n.startswith('yolo26_optimization_8/') and (n.endswith('recompile_release.py') or n.endswith('regenerate_release.py') or n.startswith('yolo26_optimization_8/compiler/') or n.startswith('yolo26_optimization_8/compiler_sources/')) and n.endswith('.py')]
    for name in chosen:
        data=z.read(name);rows.append({'member':name,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'source_text':data.decode('utf-8')})
result={'status':'O8_RELEASE_MATCHES_PREVIOUS_REVIEW_SHA_COMPILATION_SOURCES_READ_ONLY','created_host_UTC':datetime.now(timezone.utc).isoformat(),
 'archive':str(archive),'archive_bytes':archive.stat().st_size,'archive_sha256':digest,'ZIP_members':len(names),
 'source_members':rows,'source_code_executed':False,'archive_markdown_or_AGENTS_not_activated':True}
out=ROOT/'evidence/archive_source_inspection.json';out.parent.mkdir(parents=True,exist_ok=True);assert not out.exists();out.write_text(json.dumps(result,indent=2)+'\n')
for row in rows:print(row['member'],row['bytes']);print(row['source_text'])
