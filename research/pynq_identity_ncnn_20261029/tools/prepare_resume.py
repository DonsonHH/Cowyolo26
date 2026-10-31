from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,ast
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/'tools/export_encoder.py';text=source.read_text();assert text.count('pnnx.export(encoder,')==1
start=text.index(' before=Path.cwd();os.chdir(out)');end=text.index(" assert (out/'encoder.ncnn.param').exists()",start)
new=''' # NCNN files were produced before the wrapper tried to import invalid numeric Python attribute names.
 import shutil
 old=ROOT/'results/export';reuse=[]
 for name in ['encoder.pt','encoder.ncnn.param','encoder.ncnn.bin']:
  original=old/name;assert original.is_file();shutil.copyfile(original,out/name)
  reuse.append({'file':name,'sha256':sha(original),'bytes':original.stat().st_size})
 save(out/'converted_asset_reuse.json',{'failed_job':'130569','assets':reuse,'conversion_repeated':False,
  'old_failure':'GeneratedPNNXPythonhasnumericself.0_*attribute;NCNNparamandbinwerealreadywritten;do not execute generatedPython.',
  'measured_real_image_forwards_in_old_failed_job':0,'export_trace_probes_in_old_job_not_claimed_zero':True})
'''
text=text[:start]+new+text[end:]
text=text.replace("out=ROOT/'results/export'","out=ROOT/'results/export_v2'")
text=text.replace("old=ROOT/'results/export_v2'","old=ROOT/'results/export'")
text=text.replace('protocol/execution_v1.json','protocol/execution_v2.json')
file=ROOT/'tools/export_encoder_v2.py';assert not file.exists();file.write_text(text,newline='\n');ast.parse(text)
execution={'created_UTC':datetime.now(timezone.utc).isoformat(),'script_sha256':sha(file),'protocol_sha256':sha(ROOT/'protocol/encoder_v1.json'),
 'repair':'Reuse convertedNCNN assets; skip invalid generatedPNNXPython constructor, no source weights/preprocessing/threshold changes.',
 'failed_job':'130569','original_export_script_sha256':sha(source)}
(ROOT/'protocol/execution_v2.json').write_text(json.dumps(execution,indent=2)+'\n')
job=(ROOT/'tools/export.slurm').read_text().replace('export_encoder.py','export_encoder_v2.py')
(ROOT/'tools/export_v2.slurm').write_text(job,newline='\n')
print(json.dumps({'repair':'Wrapper-return-only generatedPython failure; full132parity pending','newscript_sha256':sha(file),'protocol_unchanged':True}))
