"""Validated standalone O6 detector: reuses loaded firmware, never downloads FPGA."""
import pathlib,json,hashlib,time,sys,argparse,runpy,os
D=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--profile',choices=['fast192','balanced256'],default='fast192');p.add_argument('--image');p.add_argument('--camera',action='store_true');p.add_argument('--frames',type=int,default=1);a=p.parse_args();assert 1<=a.frames<=1000
m=json.loads((D/'release_manifest.json').read_text())
for n,h in m['runtime_files'].items():assert hashlib.sha256((D/n).read_bytes()).hexdigest()==h,'Release changed: '+n
candidate,size,runtime=('r192_fullptq',192,'runtime_fast') if a.profile=='fast192' else ('r256',256,'runtime')
os.environ.pop('O6_HEAD_LUT_DISABLE',None)
sys.argv=['run_board','--candidate',candidate,'--size',str(size),'--runtime',runtime,'--fixed','0' if a.camera else str(a.frames),'--camera',str(a.frames) if a.camera else '0','--warmups','0','--skip-diagnostic','--tag','demo_'+str(time.time_ns())]
if a.image:sys.argv.extend(['--image',a.image])
runpy.run_path(str(D/'run_board.py'),run_name='__main__')
