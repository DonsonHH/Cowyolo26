set -eu
test "$(id -un)" = root
test "$(hostname)" = pynq
export XILINX_XRT=/usr
export OMP_NUM_THREADS=2
export OPENBLAS_NUM_THREADS=2
export PYTHONDONTWRITEBYTECODE=1
/usr/local/share/pynq-venv/bin/python3 - <<'PY'
from pathlib import Path
import json,hashlib,tarfile,os,fcntl
from pynq import PL,Overlay
root=Path('/home/xilinx/jupyter_notebooks/cow_research_validation_v2_20261029')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
rows=[]
for run in ['probe192','formal192','formal256','formal320']:
    terminal=json.loads((root/run/'terminal.json').read_text());record=json.loads((root/run/'record.json').read_text())
    assert terminal['status']==('PROBE_COMPLETED' if run=='probe192' else 'PROFILE_COMPLETED') and terminal['close_error'] is None
    assert not (Path('/proc')/str(terminal['PID'])).exists(),(run,'Processstillpresent')
    assert sha(root/run/'record.json')==terminal['record_sha256'] and len(record['rows'])==(1 if run=='probe192' else 32)
    rows.append({'run':run,'size':record['size'],'status':record['status'],'PID':record['PID'],'engine':record['engine'],
       'detector':record['detector_e2e_statistics'],'photo_rotation_detector':record['photo_rotation_detector_statistics'],
       'record_sha256':sha(root/run/'record.json'),'actual_forwards':len(record['rows'])+len(record['warmups']),
       'cow_present_photos':sum(bool(r['cow_boxes_rotated_native']) for r in record['rows'][:12])})
file=root/'board_state_after_profiles.json';assert not file.exists()
state={'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),'PL_before_final_O8_attach_or_load':PL.bitfile_name,
       'profiles_terminal':rows,'probe_and_formal_image_forwards':sum(r['actual_forwards'] for r in rows)}
assert state['probe_and_formal_image_forwards']==103
lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
o8=Path('/home/xilinx/jupyter_notebooks/yolo26_optimization_8');manifest=json.loads((o8/'hardware/accepted/firmware_manifest.json').read_text())
bit=o8/'hardware/accepted/optimization_8_resident.bit'
assert sha(bit)==manifest['bit']['sha256'] and sha(bit.with_suffix('.hwh'))==manifest['hwh']['sha256']
if not PL.bitfile_name or sha(Path(PL.bitfile_name))!=manifest['bit']['sha256']:
    Overlay(str(bit));state['programmed_known_O8_for_next192_stage']=True
else:state['programmed_known_O8_for_next192_stage']=False
state['PL_after']=PL.bitfile_name;state['PL_after_bit_sha256']=sha(Path(PL.bitfile_name));state['PL_after_IP_names']=list(PL.ip_dict)
state['memory']=Path('/proc/meminfo').read_text();state['no_inference_in_collection']=True
fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
with file.open('x') as f:json.dump(state,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
files=[]
for run in ['probe192','formal192','formal256','formal320']:
    files.extend(f for f in sorted((root/run).rglob('*')) if f.is_file())
    files.extend([root/(run+'.log'),root/('launch_'+run+'.json')])
files.extend([root/'protocol.json',root/'board_profile.py',root/'recovery_record.json',root/'prior_interrupted_manifest.json',file])
assembly=root/'profile_artifact_manifest.json';assert not assembly.exists()
assembly.write_text(json.dumps([{'relative_file':f.relative_to(root).as_posix(),'bytes':f.stat().st_size,'sha256':sha(f)} for f in files],indent=2)+'\n')
archive=root/'profiles_complete.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tar:
    for f in [*files,assembly]:tar.add(f,arcname=f.relative_to(root).as_posix(),recursive=False)
os.sync()
transfer={'status':'ALL3_BOARD_PROFILES_AND_PROBE_TERMINAL_CLOSED','archive':str(archive),'bytes':archive.stat().st_size,'sha256':sha(archive),
          'members':len(files)+1,'manifest_files':len(files),'total_image_forwards':103,'formal_samples':96,'warmups':6,'probe_samples':1}
file=root/'profiles_transfer.json';assert not file.exists();file.write_text(json.dumps(transfer,indent=2)+'\n');os.sync()
print(json.dumps({'transfer':transfer,'profiles':rows,'final_known_O8_bit_sha256':state['PL_after_bit_sha256']}))
PY
