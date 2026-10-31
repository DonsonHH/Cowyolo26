from pathlib import Path
from zipfile import ZipFile
from datetime import datetime,timezone
import hashlib,json,shutil
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=json.loads((ROOT/'evidence/archive_source_inspection.json').read_text());archive=Path(old['archive'])
snapshot=ROOT/'source_snapshot';extra=[]
with ZipFile(archive) as z:
    names=[n for n in z.namelist() if n.startswith('yolo26_optimization_8/runtime_fast/') and n.endswith('.py')]
    names.append('yolo26_optimization_8/test_images/bus.jpg')
    for name in names:
        relative=name[len('yolo26_optimization_8/'):];target=snapshot/relative
        assert not target.exists();target.parent.mkdir(parents=True,exist_ok=True);data=z.read(name);target.write_bytes(data)
        extra.append({'relative_file':relative,'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()})
record=ROOT/'evidence/additional_source_snapshot_manifest.json';assert not record.exists();record.write_text(json.dumps({'archive_sha256':old['archive_sha256'],'files':extra,'code_executed':False},indent=2)+'\n')
workspace=ROOT/'compiler_workspace';assert not workspace.exists();shutil.copytree(snapshot,workspace)
head=workspace/'pc_intdw/head_lut.py';text=head.read_text();before=sha(head)
assert "spec['Cout']==80" in text and 'np.array([1,80,-1]' in text
text=text.replace("assert spec['FPGA_supported'] and spec['Cout']==80","assert spec['FPGA_supported'] and spec['Cout'] in (1,80)\n  classes=int(spec['Cout'])")
text=text.replace('np.array([1,80,-1]','np.array([1,classes,-1]')
head.write_text(text,newline='\n')
changes=[{'relative_file':'pc_intdw/head_lut.py','original_sha256':before,'modified_sha256':sha(head),
 'reason':'UseactualvalidatedCout1or80inclassheadreshape;sigmoidformula/codeLUTunchanged;all3headsassertsameclasscountviaexportaudit.'}]
out=ROOT/'evidence/compiler_modifications_v1.json';assert not out.exists();out.write_text(json.dumps({'created_host_UTC':datetime.now(timezone.utc).isoformat(),'source_archive_sha256':old['archive_sha256'],
 'changes':changes,'original_snapshot_preserved':True,'hardware_sources_changed':False,'active_board_assets_changed':False},indent=2)+'\n')
print(json.dumps({'workspace_files':sum(p.is_file() for p in workspace.rglob('*')),'class_count_generalized_to':[1,80],'original_compiler_hashes_preserved':True}))
