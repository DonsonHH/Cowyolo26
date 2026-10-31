from pathlib import Path
from zipfile import ZipFile
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
inspection=json.loads((ROOT/'evidence/archive_source_inspection.json').read_text());archive=Path(inspection['archive'])
out=ROOT/'source_snapshot';out.mkdir(exist_ok=False)
selected=[]
with ZipFile(archive) as z:
    manifest=json.loads(z.read('yolo26_optimization_8/release_manifest.json'))
    filenames=z.namelist()
    for name in filenames:
        prefix='yolo26_optimization_8/'
        if not name.startswith(prefix):continue
        relative=name[len(prefix):]
        allowed=(relative.startswith(('tools/','compiler/','compiler_sources/','runtime/','pc_intdw/')) and relative.endswith('.py'))
        allowed=allowed or (relative.startswith('native_sources/') and (relative.endswith(('.cpp','.inc','.h','.dll')) or relative.endswith('libwinpthread-1.dll')))
        allowed=allowed or relative in ['native_graph.py','recompile_release.py','regenerate_release.py','release_manifest.json','requirements_pc.txt','dataset_split.json']
        if not allowed:continue
        p=(out/relative).resolve();assert p.is_relative_to(out.resolve()) and not p.exists();p.parent.mkdir(parents=True,exist_ok=True)
        data=z.read(name);p.write_bytes(data);selected.append({'relative_file':relative,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
    inventory={r['path']:r for r in manifest['runtime_files']+manifest['reproduction_files']}
    for r in selected:
        if r['relative_file'] in inventory:
            expected=inventory[r['relative_file']];assert r['sha256']==expected['sha256'] and r['bytes']==expected['bytes']
record={'status':'SOURCE_SNAPSHOT_ONLY_NO_ARCHIVE_ENTRYPOINT_EXECUTED','created_host_UTC':datetime.now(timezone.utc).isoformat(),
 'archive_sha256':inspection['archive_sha256'],'files':selected,'source_code_executed':False,'markdown_instructions_activated':False}
file=ROOT/'evidence/source_snapshot_manifest.json';assert not file.exists();file.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({'files':len(selected),'compiler_module_exists':(out/'tools/compiler.py').is_file(),'total_bytes':sum(r['bytes'] for r in selected)}))
