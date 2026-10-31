set -euo pipefail
test "$(id -un)" = xilinx
python3 - <<'PY'
from pathlib import Path
import os,mmap,ctypes,math,json
file=Path('/home/xilinx/jupyter_notebooks/cow_research_periodic_joint_20261030/camera/highres/f08915.jpg')
libc=ctypes.CDLL(None,use_errno=True);libc.mincore.argtypes=[ctypes.c_void_p,ctypes.c_size_t,ctypes.POINTER(ctypes.c_ubyte)];libc.mincore.restype=ctypes.c_int
def resident():
 with file.open('rb') as stream:
  mapping=mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_COPY);pointer=ctypes.c_char.from_buffer(mapping);n=math.ceil(len(mapping)/mmap.PAGESIZE);bits=(ctypes.c_ubyte*n)()
  code=libc.mincore(ctypes.addressof(pointer),len(mapping),bits);assert code==0,ctypes.get_errno()
  result={'pages':n,'resident':sum(int(x)&1 for x in bits),'page_size':mmap.PAGESIZE};del pointer;mapping.close();return result
print(json.dumps({'process_io_file_exists':Path('/proc/self/io').exists(),'resident_probe':resident(),'block_stats':{str(p):p.read_text() for p in Path('/sys/block').glob('mmcblk*/stat')},'new_model_forwards':0,'cache_advice_in_probe':False}))
PY
