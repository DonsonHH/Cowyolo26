set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,statistics
root=Path('/home/xilinx/jupyter_notebooks/cow_research_capture_encoding_20261030');archive=root/'periodic_delivery.tar.gz'
s=json.loads((root/'results/record.json').read_text());t=json.loads((root/'results/terminal.json').read_text())
assert s['status']==t['status']=='ALL_THREE392_SLOT_LOSSLESS_CAPTURE_ENCODING_CONTROLS_COMPLETE' and not (Path('/proc')/str(t['PID'])).exists()
assert hashlib.sha256((root/'results/record.json').read_bytes()).hexdigest()==t['record_sha256']
with tarfile.open(archive) as tar:members=len(tar.getmembers())
manifest=json.loads((root/'periodic_manifest.json').read_text());assert members==len(manifest)+1
transfer={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'members':members,'manifest_files':len(manifest)}
backends=[]
for case in ['foreground_with_identity','foreground_idle_identity']:
 folder=root/'results'/case/'background';bg=json.loads((folder/'record.json').read_text());bt=json.loads((folder/'terminal.json').read_text())
 assert bg['status']==bt['status']=='ALL_ACTUAL_TRIGGERED_IDENTITY_JOBS_COMPLETE' and not (Path('/proc')/str(bt['PID'])).exists()
 backends.append({'case':case,'actual_jobs':bg['model_forwards'],'PNG_level':bg['PNG_compress_level'],'mean_photo_save_elapsed_ms':statistics.mean(r['runtime_native_crop_and_photo_save_ms'] for r in bg['jobs']),
 'maximum_queue_ms':max(r['queue_wait_ms'] for r in bg['jobs']),'maximum_enqueue_to_result_ms':max(r['enqueue_to_result_ms'] for r in bg['jobs']),'accepted':sum(r['accepted'] for r in bg['jobs'])})
print(json.dumps({'transfer':transfer,'cases':[{k:v for k,v in r.items() if k!='periodic_events'} for r in s['cases']],
 'actual_O8_timed_forwards':s['actual_O8_forwards'],'O8_warmups':s['warmup_forwards'],'qualification_forwards':s['qualification_forwards'],
 'backends':backends,'collection_only_read_existing_archive_after_timeout':True,'whole_goal_complete':False}))
PY
