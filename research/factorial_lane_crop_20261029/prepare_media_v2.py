from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parent
old=ROOT/'tools/render_media.py';new=ROOT/'tools/render_media_v2.py';assert not new.exists()
text=old.read_text().replace('hashlib.sha256(p.read_bytes())','hashlib.sha256(Path(p).read_bytes())')
text=text.replace("out=ROOT/'results/media'","out=ROOT/'results/media_v2'")
new.write_text(text,newline='\n')
slurm=ROOT/'media_v2.slurm';assert not slurm.exists();slurm.write_text((ROOT/'media.slurm').read_text().replace('tools/render_media.py','tools/render_media_v2.py').replace('cow-factor-crop-media','cow-factor-crop-media2'),newline='\n')
record={'status':'MEDIA_READER_PATH_TYPE_FIX_AFTER_TERMINAL_FAILURE','created_host_UTC':datetime.now(timezone.utc).isoformat(),
        'prior_job':'130563','prior_error':'Pathhelpercalledwithstrbeforevideoopened','original_script_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),
        'new_script_sha256':hashlib.sha256(new.read_bytes()).hexdigest(),'new_output':'results/media_v2','weights_predictions_and_media_choices_changed':False,
        'new_NN_forwards':0,'partial_prior_media_preserved':True}
out=ROOT/'evidence/media_v2_fix.json';assert not out.exists();out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
