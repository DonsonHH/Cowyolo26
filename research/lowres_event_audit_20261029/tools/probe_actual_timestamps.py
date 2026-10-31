from pathlib import Path
from datetime import datetime,timezone
from PIL import Image
import subprocess,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
source=PROJECT/'phase3_diagnosis_20261026/inputs/multicam_original.mp4';manifest=json.loads((ROOT/'results/native_frame_manifest.json').read_text())
command=['ffprobe','-v','error','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',str(source)]
result=subprocess.run(command,capture_output=True,check=True);data=json.loads(result.stdout);frames=data['frames'];requested=[r['source_frame0'] for r in manifest['frames']]
pts=[float(r['best_effort_timestamp_time']) for r in frames]
row=manifest['frames'][0];frame=row['source_frame0'];absolute=pts[frame]
command2=['ffmpeg','-v','error','-threads','2','-seek_timestamp','1','-ss',format(absolute,'.9f'),'-i',str(source),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','pipe:1']
raw=subprocess.run(command2,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True).stdout
with Image.open(row['file']) as image:a=np.asarray(image.convert('RGB'))
same=raw==a.tobytes();diff=np.abs(np.frombuffer(raw,np.uint8).reshape(a.shape).astype(np.int16)-a.astype(np.int16))
record={'status':'ACTUAL_FRAME_PTS_INSPECTED_AFTER_RELATIVE_NOMINAL_SEEK_MISMATCH','created_host_UTC':datetime.now(timezone.utc).isoformat(),
 'total_frames':len(frames),'first_PTS':pts[0],'last_PTS':pts[-1],'requested_frames':[{'frame0':f,'PTS':pts[f],'nominal_elapsed_s':f/25,'actual_elapsed_s':pts[f]-pts[0]} for f in requested],
 'minimum_frame_PTS_delta':min(b-a for a,b in zip(pts,pts[1:])),'maximum_frame_PTS_delta':max(b-a for a,b in zip(pts,pts[1:])),
 'first_anchor_absolute_timestamp_seek_matches_exact':same,'mean_RGB_difference':float(diff.mean()),
 'model_or_counter_data_changed':False,'no_tolerance_relaxed':True}
file=ROOT/'results/actual_frame_timestamps.json';assert not file.exists();file.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
