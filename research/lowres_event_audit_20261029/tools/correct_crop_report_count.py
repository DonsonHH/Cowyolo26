from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,shutil
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
used=ROOT/'tools/run_crop_control.py';historical=ROOT/'tools/run_crop_control_v1.py';assert not historical.exists();shutil.copyfile(used,historical)
text=used.read_text().replace("out=ROOT/'crop_results'","out=ROOT/'crop_results_v2'")
assert "'counter_oracle_paths':162" in text;text=text.replace("'counter_oracle_paths':162","'counter_oracle_paths':casepaths")
target=ROOT/'tools/run_crop_control_v2.py';assert not target.exists();target.write_text(text,newline='\n')
record={'status':'CROP_EXTENSION_REPORTED_COUNT_CORRECTED_WITHOUT_CHANGING_ORACLE_LOGIC','created_host_UTC':datetime.now(timezone.utc).isoformat(),
 'original_script_sha256':sha(historical),'original_summary_sha256':sha(ROOT/'crop_results/summary.json'),
 'correction':'Originalextensionasserted72actualpathsbutinherited162constantinreportedsummary;v2reportscomputedcasepaths.',
 'new_output_directory':'crop_results_v2','model_or_training_forwards':0,'prior_outputs_preserved':True}
file=ROOT/'results/crop_report_count_correction.json';assert not file.exists();file.write_text(json.dumps(record,indent=2)+'\n')
verifier=(ROOT/'tools/verify_independent.py').read_text();prefix=verifier.split("primary05=load(",1)[0]
prefix=prefix.replace("ROOT/'protocol/audit_v1.json'","ROOT/'protocol/audit_crop_v1.json'").replace("ROOT/'results'","ROOT/'crop_results_v2'")
prefix=prefix.replace('checks==54 and oracles==162 and rows_checked==31374 and assignments==38664','checks==24 and oracles==72 and rows_checked==13944 and assignments==17184')
prefix=prefix.replace("assert len(candidates)==1 and candidates[0]['reference_track_id']==e['reference_track_id']",
                      "if e['reference_track_id'] is None:assert not candidates\n            else:assert len(candidates)==1 and candidates[0]['reference_track_id']==e['reference_track_id']")
tail='''
result={'status':'ALL24_FIXED_CROP_CASES17184_MATCHINGS72_ORACLE_PATHS_VERIFIED','created_host_UTC':datetime.now(timezone.utc).isoformat(),
 'cases':checks,'reference_case_rows':rows_checked,'matching_problems':assignments,'independent_counter_oracle_paths':oracles,
 'post_admission_checks':admission_checks,'new_network_forwards':0,'new_training_updates':0,'board_actions':0,
 'diagnostic_reference_is_independent_GT':False,'whole_goal_complete':False}
file=ROOT/'results/crop_independent_verification.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\\n')
with (ROOT/'results/crop_conditions.csv').open('x',newline='',encoding='utf-8-sig') as f:w=csv.DictWriter(f,fieldnames=list(fulltable[0]));w.writeheader();w.writerows(fulltable)
print(json.dumps(result))
'''
target=ROOT/'tools/verify_crop_independent.py';assert not target.exists();target.write_text(prefix+tail,newline='\n')
print('Correctedreportedextensioncount;prioroutputsretained;independentverifierprepared')
