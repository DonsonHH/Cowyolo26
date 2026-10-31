from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,ast,tarfile
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,x):
 assert not p.exists();p.write_text(json.dumps(x,indent=2)+'\n',encoding='utf-8')
failed=load(ROOT/'evidence/failed_run_record.json');assert failed['status']=='FAILED' and failed['rows']==[] and failed['actual_O8_forwards']==0 and "'/proc/self/io'" in failed['traceback']
probe=json.loads(load(ROOT/'evidence/accounting_probe.json')['stdout']);assert probe['process_io_file_exists'] is False and probe['resident_probe']['resident']<=probe['resident_probe']['pages']
source=(ROOT/'tools/board_benchmark.py').read_text(encoding='utf-8')
def replace(old,new):
 global source
 assert source.count(old)==1,(old,source.count(old));source=source.replace(old,new)
replace('import os,sys,json,time,hashlib,fcntl,traceback,resource,pickle,tarfile','import os,sys,json,time,hashlib,fcntl,traceback,resource,pickle,tarfile,mmap,ctypes,math')
replace("assert sha(ROOT/'board_benchmark.py')==p['runner_sha256']","assert sha(ROOT/'board_benchmark_v2.py')==p['runner_sha256']")
replace("def io_counters():return {k:int(v) for k,v in (line.split(':') for line in Path('/proc/self/io').read_text().splitlines())}","""LIBC=ctypes.CDLL(None,use_errno=True)
LIBC.mincore.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_ubyte)];LIBC.mincore.restype=ctypes.c_int
def io_counters():return {'device_sectors_read':int(Path('/sys/block/mmcblk0/stat').read_text().split()[2])}
def residency(file):
 with file.open('rb') as stream:
  mapping=mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_COPY);pointer=ctypes.c_char.from_buffer(mapping);n=math.ceil(len(mapping)/mmap.PAGESIZE);bits=(ctypes.c_ubyte*n)()
  code=LIBC.mincore(ctypes.addressof(pointer),len(mapping),bits);assert code==0,ctypes.get_errno()
  result={'pages':n,'resident_pages':sum(int(x)&1 for x in bits),'page_size':mmap.PAGESIZE};del pointer;mapping.close();return result""")
replace('before=snapshot();start=time.monotonic_ns();cpu_start=time.process_time_ns()', 'resident_before=residency(file);before=snapshot();start=time.monotonic_ns();cpu_start=time.process_time_ns()')
replace('cpu_end=time.process_time_ns();end=time.monotonic_ns();after=snapshot();outer_end=time.monotonic_ns()', 'cpu_end=time.process_time_ns();end=time.monotonic_ns();after=snapshot();resident_after=residency(file);outer_end=time.monotonic_ns()')
replace("'read_bytes_delta':after['io']['read_bytes']-before['io']['read_bytes'],'rchar_delta':after['io']['rchar']-before['io']['rchar'],", "'device_read_sectors_delta':after['io']['device_sectors_read']-before['io']['device_sectors_read'],'process_IO_bytes_unavailable':True,\n       'residency_before':resident_before,'residency_after':resident_after,")
runner=ROOT/'tools/board_benchmark_v2.py';assert not runner.exists();ast.parse(source);runner.write_text(source,encoding='utf-8')
p=load(ROOT/'protocol/run_v1.json');p.update({'status':'FROZEN_V2_MINCORE_AND_DEVICE_STATS_BEFORE_MEASUREMENTS','created_UTC':datetime.now(timezone.utc).isoformat(),
 'runner_sha256':sha(runner),'prior_protocol_sha256':sha(ROOT/'protocol/run_v1.json'),'instrumentation_revision_sha256':sha(ROOT/'计量兼容修正_v2.md'),
 'process_read_bytes_and_CPU_and_faults_recorded':False,'process_IO_counters_not_available':True,'actual_file_mincore_residency_before_and_after_recorded':True,
 'whole_device_sectors_cannot_be_attributed_to_our_process':True,'failed_v1_actual_model_forwards':0,'failed_v1_measurement_rows':0})
save(ROOT/'protocol/run_v2.json',p)
a=ROOT/'payload_v2.tar.gz';assert not a.exists()
with tarfile.open(a,'w:gz') as tar:
 tar.add(ROOT/'protocol/run_v2.json',arcname='protocol.json');tar.add(runner,arcname='board_benchmark_v2.py')
m={'bytes':a.stat().st_size,'sha256':sha(a),'protocol_sha256':sha(ROOT/'protocol/run_v2.json'),'members':2};save(ROOT/'results/payload_manifest_v2.json',m)
remote='/home/xilinx/jupyter_notebooks/cow_research_input_cost_v2_20261030'
script=(ROOT/'tools/launch.sh').read_text(encoding='utf-8')
oldmeta=load(ROOT/'results/payload_manifest.json');script=script.replace('cow_research_input_cost_20261030','cow_research_input_cost_v2_20261030').replace('payload_v1.tar.gz','payload_v2.tar.gz').replace(oldmeta['sha256'],m['sha256']).replace(oldmeta['protocol_sha256'],m['protocol_sha256']).replace('board_benchmark.py','board_benchmark_v2.py')
script=script.replace("prior=Path('/home/xilinx/jupyter_notebooks/cow_research_causal_photo_20261030/results/terminal.json')","prior=Path('/home/xilinx/jupyter_notebooks/cow_research_input_cost_20261030/results/terminal.json')")
(ROOT/'tools/launch_v2.sh').write_text(script,encoding='utf-8')
for original,new in [('create_task.sh','create_task_v2.sh'),('status.sh','status_v2.sh'),('collect.sh','collect_v2.sh')]:
 text=(ROOT/'tools'/original).read_text(encoding='utf-8').replace('cow_research_input_cost_20261030','cow_research_input_cost_v2_20261030').replace('board_benchmark.py','board_benchmark_v2.py')
 (ROOT/'tools'/new).write_text(text,encoding='utf-8')
print(json.dumps({'v1_measurements':0,'v1_forwards':0,'v2':m}))
