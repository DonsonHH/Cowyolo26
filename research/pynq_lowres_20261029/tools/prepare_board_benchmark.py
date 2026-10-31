from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile,io,base64
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def body(path):
    record=json.loads(path.read_text(encoding='utf-8'))
    return json.loads(''.join(m['content'].get('text','') for m in record['messages'] if m['type']=='stream'))
events=json.loads((PROJECT/'confirmed12_capture_identity_20261029/delivery/results/replay/events.json').read_text())
inputs=[]
files=[]
for event in events:
    s=event['selected_snapshot'];file=PROJECT/'confirmed12_capture_identity_20261029/delivery/results/replay'/s['native_path'];assert sha(file)==s['native_sha256']
    name='photos/'+event['event_id']+'.jpg';files.append((file,name));inputs.append({'query_id':event['event_id'],'file':name,'sha256':sha(file),'source_frame0':s['frame0'],'native_size_WH':[2560,1440]})
sources=body(ROOT/'evidence/board_sources.json')['source_files'];details=body(ROOT/'evidence/runtime_details.json')['sources'];release=body(ROOT/'evidence/release_evidence.json')
source_map={r['path']:r for r in sources+details}
for row in release['sources']:source_map['/home/xilinx/jupyter_notebooks/'+row['relative']]=row
runtime=[{'path':p,'sha256':row['sha256']} for p,row in source_map.items() if any(p.endswith('/'+n) for n in ['native_graph.py','device_initialize.py','board_runtime.py','queue_device.py','queue_conv.py','hybrid_executor.py','native_ops.py','verify_release.py'])]
firmware=json.loads((ROOT/'board_source_snapshot/yolo26_optimization_8/hardware/accepted/firmware_manifest.json').read_text())
protocol={'created_UTC':datetime.now(timezone.utc).isoformat(),'status':'FROZEN_BEFORE_HARDWARE_BENCHMARK','sizes':[192,256,320],'target_frontend_fps':5,'per_frame_target_ms':200,
'source_images':inputs,'runtime_files':runtime,'benchmarks':[{'size':192,'engine':'O8resident'},{'size':256,'engine':'O8resident'},{'size':320,'engine':'O6legacy'}],
'input_preprocess':'Original2560x1440JPEGdecode;CW90nativepixelpermutation;engine-specificsquareletterboxtoS,S;RGBfloatorint8routesasoriginalruntime;conf.2,cowclass19.',
'measured_per_profile':{'distinct_source_captures':12,'fixed_E010_repeats':20,'warmups':2,'detector_e2e':'preprocess+actualARM/PLfullnetwork+decode+copyraw;photoIOandnativeCWrotationseparate'},
'original_finetuned_model_sha256':'51b342c474ba321a438b86512c63b8bbeb78d1b86e32b9961fdc21f4ff186a74',
'fine_tuned_checkpoint_loaded_into_these_engines':False,'existing_engine_is_public_COCO80_model':True,'real_event_identity_or_count_accuracy_admitted':False,
'background_identity_active':False,'camera_hardware_active':False,'p95_budget_only_estimate_not_hard_realtime_guarantee':True,
'permission_context':'UserauthorizedPYNQ-Z2deploymentandprovidedliveconnection;boundedtestusesexistingknownfirmwareunderexistingexclusiveacceleratorlock,noexistingprojectfilesmodified.',
'initial_hardware_configuration_may_be_unknown':True,'after_benchmark_known_accepted_O8_firmware_loaded':True,'final_expected_O8_bit_SHA256':firmware['bit']['sha256'],
'new_training_updates':0,'whole_goal_complete':False}
protocolfile=ROOT/'protocol/board_benchmark_v1.json';protocolfile.parent.mkdir(exist_ok=True);assert not protocolfile.exists();protocolfile.write_text(json.dumps(protocol,indent=2)+'\n')
files.extend([(protocolfile,'protocol.json'),(ROOT/'tools/board_existing_benchmark.py','board_existing_benchmark.py')])
manifest=[{'name':name,'bytes':file.stat().st_size,'sha256':sha(file)} for file,name in files]
memory=io.BytesIO()
with tarfile.open(fileobj=memory,mode='w:gz') as tar:
    for file,name in files:tar.add(file,arcname=name,recursive=False)
archive=memory.getvalue();archivefile=ROOT/'board_inputs.tar.gz';assert not archivefile.exists();archivefile.write_bytes(archive)
launch="""from pathlib import Path
import base64,hashlib,tarfile,io,json,os,sys,subprocess
root=Path('/home/xilinx/jupyter_notebooks/cow_research_lowres_20261029')
data=base64.b64decode('BASE64')
assert hashlib.sha256(data).hexdigest()=='SHA256'
root.mkdir(exist_ok=False)
with tarfile.open(fileobj=io.BytesIO(data)) as tar:
    for m in tar.getmembers():
        assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
        f=(root/m.name).resolve();assert str(f).startswith(str(root.resolve())+'/');assert not f.exists()
        f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(m).read())
manifest=MANIFEST
for m in manifest:
    f=root/m['name'];assert f.stat().st_size==m['bytes'] and hashlib.sha256(f.read_bytes()).hexdigest()==m['sha256']
log=open(root/'benchmark.log','xb')
env=os.environ.copy();env['OMP_NUM_THREADS']='2';env['OPENBLAS_NUM_THREADS']='2'
p=subprocess.Popen([sys.executable,'-u',str(root/'board_existing_benchmark.py')],stdout=log,stderr=subprocess.STDOUT,cwd=str(root),env=env,start_new_session=True)
result={'status':'OWN_BOARD_BENCHMARK_PROCESS_STARTED','PID':p.pid,'root':str(root),'python':sys.executable,
        'input_archive_SHA256':'SHA256','input_archive_bytes':len(data),'manifest_files':len(manifest)}
(root/'launch.json').write_text(json.dumps(result,indent=2)+'\\n')
print(json.dumps(result))
""".replace('BASE64',base64.b64encode(archive).decode()).replace('SHA256',hashlib.sha256(archive).hexdigest()).replace('MANIFEST',repr(manifest))
launchfile=ROOT/'tools/launch_board_benchmark_generated.py';assert not launchfile.exists();launchfile.write_text(launch,encoding='utf-8',newline='\n')
record={'protocol_SHA256':sha(protocolfile),'input_archive_sha256':sha(archivefile),'input_archive_bytes':len(archive),'source_capture_photos':len(inputs),'launch_code_bytes':launchfile.stat().st_size}
out=ROOT/'results/staging_record.json';assert not out.exists();out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record))
