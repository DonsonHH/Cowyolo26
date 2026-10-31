from pathlib import Path
import os,json,time,hashlib,traceback,sys
from PIL import Image
ROOT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p=json.loads((ROOT/'protocol.json').read_text());out=ROOT/'encoding_results';out.mkdir(exist_ok=False);rows=[]
source=Path('/home/xilinx/jupyter_notebooks/cow_research_periodic_joint_20261030/results/foreground_with_identity/background')
try:
 for i,row in enumerate(p['photos']):
  file=source/row['file'];assert sha(file)==row['sha256']
  with Image.open(file) as im:im.load();photo=im.convert('RGB')
  expected=hashlib.sha256(photo.tobytes()).hexdigest()
  for level in ([6,0] if i%2==0 else [0,6]):
   path=out/('photo'+str(i).zfill(2)+'_level'+str(level)+'.png')
   cpu=time.process_time_ns();start=time.monotonic_ns();photo.save(path,compress_level=level);end=time.monotonic_ns();cpu_end=time.process_time_ns()
   with Image.open(path) as observed:observed.load();assert observed.size==photo.size and hashlib.sha256(observed.convert('RGB').tobytes()).hexdigest()==expected
   record={'photo_index':i,'source_file':row['file'],'PNG_compress_level':level,'encode_file_wall_ms':(end-start)/1e6,
    'encode_file_CPU_ms':(cpu_end-cpu)/1e6,'output_file':path.name,'output_bytes':path.stat().st_size,'output_sha256':sha(path),'decoded_RGB_sha256':expected,'pixels_exact':True}
   rows.append(record);print(json.dumps(record),flush=True)
 result={'status':'ALL11_PHOTOS_TWO_LOSSLESS_PNG_ENCODINGS_ACTUALLY_MEASURED','PID':os.getpid(),'rows':rows,'new_model_forwards':0,'PL_actions':0,'whole_goal_complete':False}
 (out/'summary.json').write_text(json.dumps(result,indent=2)+'\n')
except BaseException as e:
 (out/'failure.json').write_text(json.dumps({'error':repr(e),'traceback':traceback.format_exc()},indent=2)+'\n');raise
finally:
 (out/'terminal.json').write_text(json.dumps({'PID':os.getpid(),'success':(out/'summary.json').exists(),'rows':len(rows)},indent=2)+'\n')
