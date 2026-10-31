from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile,subprocess,sys,ast
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
for name in ['input','protocol','results','logs','evidence']:(ROOT/name).mkdir(exist_ok=True)
source=PROJECT/'detector_torso_pairs_20261029/input/images_and_references.json'
train=json.loads(source.read_text(encoding='utf-8'))['train']
assert len(train)==6809 and sum(len(r['reference_annotations']) for r in train)==8888
save(ROOT/'input/train_only.json',train)
geo=ROOT/'input/geometry.py';assert not geo.exists();geo.write_bytes((PROJECT/'pynq_rot192_eval_20261029/tools/geometry.py').read_bytes())
p={'status':'FROZEN_TRAINING_ONLY_COVERAGE_PROXIES_BEFORE_PIXEL_STATISTICS','created_host_UTC':datetime.now(timezone.utc).isoformat(),
    'source_manifest_sha256':sha(source),'train_images':6809,'body_rectangles':8888,'image_wh':[1280,720],
    'brightness':'OpenCV_BGR_to_YCrCb_Y_uint8_in_rounded_visible_rotated_rectangle_mask',
    'background':'33square_dilation_minus_union_of_all_body_rectangles;atleast64pixels',
    'thresholds':{'Y_median_le':80,'absolute_median_contrast_le':15,'short_side192_lt':24,'intersection_over_min_area_ge':.1,'visible_fraction_lt':.99},
    'sizes':[192,256,320],'mask_rounding':'np.rint_visible_polygon_vertices_cv2.fillConvexPoly_line8',
    'pair_intersection':'cv2.intersectConvexConvex_FP32;independent_double_clip_later',
    'source_pixel_controls':'first32_training_manifest_images',
    'example_rule':'3lowestmedian,3lowestcontrast,3largestoverlap,3smallest192shortside;annotation_key_ties;skip_duplicate_keys',
    'no_independent_occlusion_or_coatcolor_GT':True,'validation_or_holdout_or_video_pixels_allowed':False,
    'model_forwards':0,'new_training_updates':0,'whole_goal_complete':False}
save(ROOT/'protocol/audit_v1.json',p)
slurm='''#!/bin/bash
#SBATCH --job-name=train-coverage-audit
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=6G
#SBATCH --time=00:15:00
#SBATCH --output=REMOTE/PHASE/logs/audit-%j.out
#SBATCH --error=REMOTE/PHASE/logs/audit-%j.err
set -euo pipefail
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
cd REMOTE/PHASE
../env/bin/python -B tools/run_audit.py
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name)
f=ROOT/'tools/audit.slurm';assert not f.exists();f.write_text(slurm,encoding='utf-8',newline='\n')
files=[ROOT/'input/train_only.json',geo,ROOT/'tools/run_audit.py',f]
for file in files:
    if file.suffix=='.py':ast.parse(file.read_text(encoding='utf-8'))
save(ROOT/'protocol/execution_v1.json',{'protocol_sha256':sha(ROOT/'protocol/audit_v1.json'),'files_sha256':{f.relative_to(ROOT).as_posix():sha(f) for f in files}})
a=ROOT/'audit_inputs_v1.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz') as tar:
    for file in [*files,ROOT/'protocol/audit_v1.json',ROOT/'protocol/execution_v1.json']:tar.add(file,arcname=file.relative_to(ROOT).as_posix())
bridge=PROJECT/'data_audit_20261026/tools/remote_bridge.py'
check=ROOT/'tools/unique_remote.sh';assert not check.exists();check.write_text('set -euo pipefail\ntest ! -e '+REMOTE+'/'+ROOT.name+'\ntest ! -e '+REMOTE+'/'+ROOT.name+'_audit_inputs_v1.tar.gz\nsqueue -u renly -o "%.18i|%.9P|%.28j|%.8T|%R"\n',encoding='utf-8',newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(check),'--output',str(ROOT/'evidence/remote_unique.txt')],check=True)
subprocess.run([sys.executable,str(bridge),'put',str(a),REMOTE+'/'+ROOT.name+'_audit_inputs_v1.tar.gz'],check=True)
submit='''set -euo pipefail
squeue -u renly -o '%.18i|%.9P|%.28j|%.8T|%R'
cd REMOTE
env/bin/python - <<'PY'
from pathlib import Path
import hashlib,tarfile
a=Path('PHASE_audit_inputs_v1.tar.gz');root=Path('PHASE');assert not root.exists()
assert hashlib.sha256(a.read_bytes()).hexdigest()=='HASH'
root.mkdir()
with tarfile.open(a) as tar:
 for m in tar.getmembers():
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  f=(root/m.name).resolve();assert f.is_relative_to(root.resolve()) and not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
for name in ['results','logs','evidence']:(root/name).mkdir(exist_ok=True)
PY
sbatch --parsable PHASE/tools/audit.slurm
'''.replace('REMOTE',REMOTE).replace('PHASE',ROOT.name).replace('HASH',sha(a))
f=ROOT/'tools/submit_generated.sh';assert not f.exists();f.write_text(submit,encoding='utf-8',newline='\n')
subprocess.run([sys.executable,str(bridge),'run',str(f),'--output',str(ROOT/'evidence/submission.txt')],check=True)
