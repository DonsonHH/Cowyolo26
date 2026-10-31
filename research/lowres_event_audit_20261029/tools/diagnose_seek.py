from pathlib import Path
import subprocess,json,hashlib
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
row=json.loads((ROOT/'results/native_frame_manifest.json').read_text())['frames'][0]
source=PROJECT/'phase3_diagnosis_20261026/inputs/multicam_original.mp4';frame=row['source_frame0']
with Image.open(row['file']) as image:actual=np.asarray(image.convert('RGB'))
probe=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_entries','stream=avg_frame_rate,r_frame_rate,start_time,time_base,pix_fmt,width,height','-of','json',str(source)],capture_output=True,text=True,check=True)
rows=[]
for delta in [-1,0,1]:
    command=['ffmpeg','-v','error','-threads','2','-ss',format((frame+delta)/25,'.8f'),'-i',str(source),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','pipe:1']
    raw=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
    array=np.frombuffer(raw,np.uint8).reshape(1440,2560,3);diff=np.abs(array.astype(np.int16)-actual.astype(np.int16))
    rows.append({'seek_frame':frame+delta,'RGB_sha256':hashlib.sha256(raw).hexdigest(),'mean_RGB_difference':float(diff.mean()),'maximum_RGB_difference':int(diff.max()),'different_channel_values':int(np.count_nonzero(diff))})
result={'status':'MEDIA_TIMESTAMP_SEEK_FAILED_EXACT_GATE_DIAGNOSTIC','source_frame0':frame,'stream':json.loads(probe.stdout),
 'frame_selected_RGB_sha256':hashlib.sha256(actual.tobytes()).hexdigest(),'seek_results':rows,'no_tolerance_relaxed':True}
file=ROOT/'results/timestamp_seek_diagnostic.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
