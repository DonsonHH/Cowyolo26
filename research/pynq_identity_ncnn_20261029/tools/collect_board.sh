set -eu
test "$(id -un)" = xilinx
test "$(hostname)" = pynq
python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile
root=Path('/home/xilinx/jupyter_notebooks/cow_research_ncnn_identity_20261029')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
t=json.loads((root/'vectors_results_v2/terminal.json').read_text());s=json.loads((root/'vectors_results_v2/record.json').read_text())
assert t['status']==s['status']=='ALL132_ACTUAL_ARM_NCNN_VECTORS_PREPROCESS_AND_RETRIEVAL_PASS_FROZEN_GATES'
assert t['record_sha256']==sha(root/'vectors_results_v2/record.json') and not (Path('/proc')/str(t['PID'])).exists()
assert t['model_forwards']==s['model_forwards']==len(s['rows'])==132 and len(s['warmups'])==2
files=[p for p in sorted((root/'vectors_results_v2').rglob('*')) if p.is_file()]
files.extend(root/r for r in ['build_protocol.json','build_protocol_v2.json','build_ncnn_board.py','build_ncnn_board_v2.py',
 'build_result.json','build_v2_result.json','build_terminal.json','build_v2_terminal.json','launch.json','build_v2_launch.json',
 'run.log','run_build_v2.log','encoder_bridge.cpp','libcow_encoder.so','libcow_encoder_v2.so','encoder.ncnn.param','encoder.ncnn.bin',
 'vectors_protocol.json','vectors_protocol_v2.json','board_vectors.py','board_vectors_v2.py','ncnn_encoder.py','ncnn_encoder_v2.py',
 'vectors_launch.json','vectors_v2_launch.json','vectors.log','vectors_v2.log','diagnose_native.py','native_crash_diagnostic.json',
 'A9_library_attributes_v2.txt'])
files.extend(sorted(root.glob('stage_*.json'))+sorted(root.glob('stage_*.log'))+sorted(root.glob('v2_stage_*.json'))+sorted(root.glob('v2_stage_*.log')))
for rel in ['build/CMakeCache.txt','build_v2/CMakeCache.txt','build/src/CMakeFiles/ncnn.dir/flags.make','build_v2/src/CMakeFiles/ncnn.dir/flags.make']:
 p=root/rel
 if p.is_file():files.append(p)
manifest=root/'board_manifest.json';assert not manifest.exists();manifest.write_text(json.dumps([{'file':p.relative_to(root).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files],indent=2)+'\n')
archive=root/'board_delivery.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
 for file in files+[manifest]:tar.add(file,arcname=file.relative_to(root).as_posix(),recursive=False)
r={'archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),'members':len(files)+1,'manifest_files':len(files)}
(root/'board_transfer.json').write_text(json.dumps(r,indent=2)+'\n')
print(json.dumps({'transfer':r,'vectors':132,'warmups':2,'mean_model_ms':s['mean_model_ms'],
 'max_normalized_embedding_difference':s['max_normalized_embedding_difference'],'max_runtime_Pillow_tensor_difference':s['max_runtime_Pillow_tensor_difference'],
 'all_retrieval_checks':s['retrieval_checks'],'process_absent':True,'whole_goal_complete':False}))
PY
