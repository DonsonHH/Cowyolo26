from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
board=ROOT/'board_results_delivery.tar.gz';assert board.exists()
p={'status':'FROZEN_BEFORE_ACTUAL_O8_VIDEO_RENDER','created_UTC':datetime.now(timezone.utc).isoformat(),
 'board_archive_sha256':sha(board),'board_members':23,'board_archive_bytes':board.stat().st_size,
 'scope_frame0_inclusive':[8912,10873],'source_anchor_frames':[8995,9345,9790,10830],
 'movie_size_WH':[1920,450],'playback_fps':25,'held_prediction_Hz':5,
 'columns':['FP32_ORT','INT8_QDQ_ORT','ACTUAL_PYNQ_O8_INTEGER'],
 'figure_panels':4,'no_model_or_frame_choice_using_best_count':True,
 'movie_source_context_is_not_actual192_network_input':True,'PYNQ_stable5FPS_proven':False,'whole_goal_complete':False}
file=ROOT/'protocol/media_v1.json';assert not file.exists();file.write_text(json.dumps(p,indent=2)+'\n')
job=f'''#!/bin/bash
#SBATCH --job-name=actual-O8-video-render
#SBATCH --partition=cu
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output={REMOTE}/{ROOT.name}/logs/media-%j.out
#SBATCH --error={REMOTE}/{ROOT.name}/logs/media-%j.err
set -euo pipefail
cd {REMOTE}/{ROOT.name}
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
../env/bin/python -B tools/render_media.py
'''
(ROOT/'tools/media.slurm').write_text(job,newline='\n')
print(json.dumps({'scope':[8912,10873],'expected_movie_frames':1962,'expected_anchor_panels':12,'board_archive_sha256':p['board_archive_sha256']}))
