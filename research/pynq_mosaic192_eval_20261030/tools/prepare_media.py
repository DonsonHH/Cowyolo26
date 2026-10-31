from pathlib import Path
from datetime import datetime,timezone
import ast,json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;OLD=PROJECT/'pynq_rot192_eval_20261029/tools'
REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
meta=load(ROOT/'evidence/board_transfer.json');verified=load(ROOT/'results/independent_board_verification.json')
assert verified['actual_video_model_forwards']==2654 and verified['actual8_video_anchor_CPU_integer_raw_bytes_exact']
text=(OLD/'render_media.py').read_text(encoding='utf-8')
text=text.replace('protocol/eval_v2.json','protocol/eval_v1.json').replace("ROOT/'results/quality_v2'","ROOT/'results/quality'").replace("ROOT/'board_delivery/results_v2'","ROOT/'board_delivery/results'")
before="   assert row['up']==1 and row['down']==0;value=1"
after="   formal=next(r for r in load(ROOT/'input/independent_board_verification.json')['publisher_event_scores'] if r['stride']==stride and r['counter']=='handoff_events');value=formal['TP']"
assert text.count(before)==1;text=text.replace(before,after)
text=text.replace("axes[1,0].set_ylim(0,410)","axes[1,0].set_ylim(0,float(np.ceil(values.max()/50)*50+50))")
text=text.replace("axes[1,0].set_title('PNG to counter+raw save:118/2654 over200ms')","axes[1,0].set_title('PNG to counter+raw save:'+str(int((values>200).sum()))+'/2654 over200ms')")
text=text.replace('Fixed192rot90seed26: FP32, QDQ and actual PYNQ-Z2 O8','Mosaic0.5 seed26 fixed192: FP32, QDQ and actual PYNQ-Z2 O8')
text=text.replace('Fixed192 rot90 seed26: source f','Mosaic0.5 seed26 actual O8: source f')
text=text.replace("'timing_total_ms':{'mean'","'timing_ymax':float(np.ceil(values.max()/50)*50+50),'timing_total_ms':{'mean'")
ast.parse(text);f=ROOT/'tools/render_media.py';assert not f.exists();f.write_text(text,encoding='utf-8',newline='\n')
f=ROOT/'input/independent_board_verification.json';assert not f.exists();f.write_bytes((ROOT/'results/independent_board_verification.json').read_bytes())
p={'status':'FROZEN_BEFORE_MOSAIC192_REAL_O8_VIDEO_AND_FIGURE_RENDER','created_UTC':datetime.now(timezone.utc).isoformat(),
    'board_archive_sha256':meta['sha256'],'board_archive_bytes':meta['bytes'],'board_members':meta['members'],
    'scope_frame0_inclusive':[8912,10873],'source_anchor_frames':[8995,9345,9790,10830],
    'movie_size_WH':[1920,450],'playback_fps':25,'held_prediction_Hz':5,'columns':['FP32_ORT','QDQ_ORT','actual_PYNQ_O8'],
    'source_context_not_actual_NN_input':True,'no_model_or_frame_choice_using_best_count':True,'new_model_forwards':0,'whole_goal_complete':False}
f=ROOT/'protocol/media_v1.json';assert not f.exists();f.write_text(json.dumps(p,indent=2)+'\n',encoding='utf-8')
job=f'''#!/bin/bash
#SBATCH --job-name=mosaic192-actual-O8-media
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=00:06:00
#SBATCH --output={REMOTE}/{ROOT.name}/logs/media-%j.out
#SBATCH --error={REMOTE}/{ROOT.name}/logs/media-%j.err
set -euo pipefail
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
cd {REMOTE}/{ROOT.name}
../env/bin/python -B tools/render_media.py
'''
f=ROOT/'tools/media.slurm';assert not f.exists();f.write_text(job,encoding='utf-8',newline='\n')
stage=(OLD/'stage_media.py').read_text(encoding='utf-8')
stage=stage.replace('import hashlib,tarfile,subprocess,sys,py_compile','import hashlib,tarfile,subprocess,sys,ast')
stage=stage.replace("py_compile.compile(str(ROOT/'tools/render_media.py'),doraise=True)","ast.parse((ROOT/'tools/render_media.py').read_text(encoding='utf-8'))")
stage=stage.replace("'tools/media.slurm']","'tools/media.slurm','input/independent_board_verification.json']")
f=ROOT/'tools/stage_media.py';assert not f.exists();f.write_text(stage,encoding='utf-8',newline='\n')
print(json.dumps({'board_members':meta['members'],'actual_video_raws_verified':2654,'new_model_forwards':0}))
