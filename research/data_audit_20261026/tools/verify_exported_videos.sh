set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
srun -p cu --nodes=1 --ntasks=1 --cpus-per-task=1 --mem=2G --time=00:02:00 /share/home/renly/miniconda3/bin/python - <<'PY'
import cv2,json,os
from pathlib import Path
root=Path('/share/home/renly/projects/idcoo_research_20261026/results/delivery_bundle/media');rows=[]
for p in sorted(root.glob('*.mp4')):
 c=cv2.VideoCapture(str(p));n=int(c.get(7));fps=c.get(5);w=c.get(3);h=c.get(4);ok,im=c.read();c.set(cv2.CAP_PROP_POS_FRAMES,n-1);last,_=c.read();c.release()
 row={'file':p.name,'frame_count':n,'fps':fps,'width':w,'height':h,'first_frame_decodes':ok,'last_frame_decodes':last}
 assert ok and last and n>0
 rows.append(row)
out={'job_id':os.environ['SLURM_JOB_ID'],'videos':rows,'scope':'exported first/last frame readability check; not full accuracy review'}
print(json.dumps(out))
(root.parent/'evidence/exported_video_readability.json').write_text(json.dumps(out,indent=2))
PY
