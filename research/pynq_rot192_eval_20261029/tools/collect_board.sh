set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,statistics,os
from pynq import PL
root=Path('/home/xilinx/jupyter_notebooks/cow_research_rot192_video_20261029')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
terminal=json.loads((root/'results_v2/terminal.json').read_text());s=json.loads((root/'results_v2/record.json').read_text())
assert terminal['status']==s['status']=='ALL2654_ACTUAL_O8_VIDEO_INPUTS_AND_REAL_ARM_COUNTER_PATHS_COMPLETE'
assert terminal['actual_video_model_forwards']==len(s['rows'])==s['actual_video_model_forwards']==2654 and len(s['warmups'])==2
assert terminal['record_sha256']==sha(root/'results_v2/record.json') and terminal['close_error'] is None and not (Path('/proc')/str(terminal['PID'])).exists()
assert s['actual_anchor_integer_parity_bytes_exact']==8 and s['hardware_status']['error']=='0x0'
p=json.loads((root/'board_protocol_v2.json').read_text())
assert s['PL_after_sha256']==sha(PL.bitfile_name)==p['O8_bit_sha256']
final={'status':'ACTUAL_VIDEO_PROCESS_TERMINAL_ABSENT_AND_O8_RETAINED','PID':terminal['PID'],'proc_exists':False,
 'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'PL_bitfile':PL.bitfile_name,'PL_bit_sha256':sha(PL.bitfile_name),
 'memory':Path('/proc/meminfo').read_text(),'additional_model_forwards':0,'new_PL_actions':0}
file=root/'final_state.json';assert not file.exists();file.write_text(json.dumps(final,indent=2)+'\n')
files=[f for f in sorted((root/'results_v2').rglob('*')) if f.is_file()]
files.extend(root/r for r in ['board_video.py','board_video_v2.py','frozen_input.py','board_protocol.json','board_protocol_v2.json',
 'board_input_manifest.json','launch.json','launch_v2.json','run.log','run_v2.log','failed_v1_forensic.json','final_state.json'])
manifest=root/'board_result_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps([{'file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files],indent=2)+'\n')
archive=root/'board_results_delivery.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for file in files+[manifest]:tar.add(file,arcname=file.relative_to(root).as_posix(),recursive=False)
os.sync();result={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1,'manifest_files':len(files)}
(root/'board_results_transfer.json').write_text(json.dumps(result,indent=2)+'\n')
rows=s['rows'];times={k:statistics.mean(r[k] for r in rows) for k in ['PNG_read_ms','preprocess_ms','tensor_to_raw_ms','decode_restore_ms','tracker_counter_ms','PNG_to_counter_with_raw_save_ms']}
print(json.dumps({'transfer':result,'mean_stage_ms':times,'actual_video_model_forwards':len(rows),'warmups':len(s['warmups']),
 'frame_times_over200ms':sum(r['PNG_to_counter_with_raw_save_ms']>200 for r in rows),
 'scenes':s['scenes'],'actual8_anchor_raw_bytes_exact':True,'whole_goal_complete':False}))
PY
