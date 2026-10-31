set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,os,statistics
from pynq import PL
root=Path('/home/xilinx/jupyter_notebooks/cow_research_o8_rot192_qual_20261029')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
terminal=json.loads((root/'results/terminal.json').read_text());assert terminal['status']=='ALL8_ACTUAL_PYNQ_COW1_CLASS_O8_VECTORS_PASS_FIXED_CPU_REFERENCE_GATES'
assert terminal['vectors']==8 and terminal['warmups']==2 and terminal['close_error'] is None and not (Path('/proc')/str(terminal['PID'])).exists()
record=json.loads((root/'results/record.json').read_text());assert sha(root/'results/record.json')==terminal['record_sha256']
assert all(r['passes_gate'] for r in record['rows'])
final={'status':'COW_VECTOR_PROCESS_TERMINAL_ABSENT_AND_O8_STILL_LOADED','PID':terminal['PID'],'proc_exists':False,
       'PL_bitfile':PL.bitfile_name,'PL_bit_sha256':sha(PL.bitfile_name),'memory':Path('/proc/meminfo').read_text(),
       'protocol_sha256':sha(root/'protocol.json'),'new_overlay_or_inference_in_collection':0}
file=root/'final_state.json';assert not file.exists();file.write_text(json.dumps(final,indent=2)+'\n')
files=[f for f in sorted((root/'results').rglob('*')) if f.is_file()]
files.extend([root/'protocol.json',root/'board_cow_vectors.py',root/'launch.json',root/'run.log',file])
manifest=root/'board_result_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps([{'relative_file':f.relative_to(root).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files],indent=2)+'\n')
archive=root/'board_results.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
    for file in [*files,manifest]:tar.add(file,arcname=file.relative_to(root).as_posix(),recursive=False)
os.sync();transfer={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1,'manifest_files':len(files)}
file=root/'board_transfer.json';assert not file.exists();file.write_text(json.dumps(transfer,indent=2)+'\n')
print(json.dumps({'transfer':transfer,'maximum_box_error':max(r['maximum_box_error'] for r in record['rows']),
 'maximum_score_error':max(r['maximum_score_error'] for r in record['rows']),'mean_tensor_to_raw_ms':statistics.mean(r['tensor_to_raw_ms'] for r in record['rows']),
 'detections_above_conf02':[r['detections_above_conf02'] for r in record['rows']],'new_bitstream_programmed':False,'class_count':1,'size':192}))
PY
