from pathlib import Path
import sys,subprocess,hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py';REMOTE='/share/home/renly/projects/idcoo_research_20261026/detector_factorial_20261029'
manifest=ROOT/'protocol/evaluation_runtime_v1.json';record=json.loads(manifest.read_text())
for relative,digest in record['files'].items():assert hashlib.sha256((ROOT/relative).read_bytes()).hexdigest()==digest
assert not (ROOT/'tools/submit_evaluation.sh').exists(),'Initialsubmissionfileunexpectedlyexists;inspectbeforecontinuing'
for relative in [*record['files'],'protocol/evaluation_runtime_v1.json']:
    subprocess.run([sys.executable,str(bridge),'put',str(ROOT/relative),REMOTE+'/'+relative],check=True)
template=(ROOT/'tools/stage_evaluation.py').read_text().split("script.write_text('''",1)[1].split("''',newline=",1)[0]
script=ROOT/'tools/submit_evaluation.sh';script.write_text(template,newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(script),'--output',str(ROOT/'evidence/evaluation_submit.txt')],check=True)
