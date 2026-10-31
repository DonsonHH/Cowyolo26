from pathlib import Path
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=PROJECT/'phase3_diagnosis_20261026/results/qa_fixture_annotation.json'
before=sha(source);packet=ROOT/'results/known_QA_cli_final';assert not packet.exists()
cmd=[sys.executable,'-X','utf8',str(ROOT/'tools/intake_pipeline.py')]
r=subprocess.run([*cmd,'stage',str(source),'--output',str(packet)],capture_output=True)
assert r.returncode==2 and sha(source)==before
value=json.loads(r.stdout.decode('utf-8'));assert value['status']=='DRAFT_INTAKE_BLOCKED' and value['metrics_computed'] is False
output=ROOT/'results/known_QA_scores_must_not_exist';assert not output.exists()
s=subprocess.run([*cmd,'score',str(packet),'--acceptance',str(ROOT/'acceptance_TEMPLATE.json'),'--output',str(output)],capture_output=True)
assert s.returncode!=0 and not output.exists() and sha(source)==before
refused=subprocess.run([*cmd,'stage',str(source),'--output',str(packet)],capture_output=True)
assert refused.returncode!=0 and b'FileExistsError' in refused.stderr and sha(source)==before
protocol=json.loads((ROOT/'protocol/evaluation_v1.json').read_text(encoding='utf-8'))
for item in protocol['source_files'].values():assert sha(item['path'])==item['sha256']
record={'status':'CLI_BLOCKED_KNOWN_QA_REJECTED_UNFILLED_REVIEW_AND_REFUSED_OVERWRITE',
 'checks':3,'stage_exit_code':r.returncode,'score_unfilled_template_exit_code':s.returncode,
 'overwrite_exit_code':refused.returncode,'input_SHA_before_after':before,'input_preserved':True,
 'original_matching_and_validation_sources_unchanged':True,'score_output_created':False,'real_reference_received':False}
target=ROOT/'results/cli_verification.json';assert not target.exists();target.write_text(json.dumps(record,indent=2),encoding='utf-8')
(ROOT/'results/cli_verification.log').write_bytes(r.stdout+r.stderr+s.stdout+s.stderr+refused.stdout+refused.stderr)
print(json.dumps(record))
