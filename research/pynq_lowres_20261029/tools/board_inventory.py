from __future__ import print_function
import os,sys,platform,json,glob,subprocess,importlib.util
def read(path,limit=10000):
    try:
        with open(path,'r') as f:return f.read(limit).replace('\x00',' ').strip()
    except Exception as e:return {'unavailable':type(e).__name__}
def command(args):
    try:
        p=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE,universal_newlines=True,timeout=5)
        return {'exit':p.returncode,'stdout':p.stdout[:2500],'stderr':p.stderr[:500]}
    except Exception as e:return {'error':type(e).__name__}
def module(name):
    try:
        spec=importlib.util.find_spec(name)
        return {'available':spec is not None,'origin':spec.origin if spec else None}
    except Exception as e:return {'available':False,'error':type(e).__name__}
cpu=read('/proc/cpuinfo');mem=read('/proc/meminfo')
result={'uname':list(platform.uname()),'machine':platform.machine(),'python':sys.version,'python_executable':sys.executable,
'uid':os.getuid(),'os_release':read('/etc/os-release'),'device_model':read('/proc/device-tree/model'),'device_compatible':read('/proc/device-tree/compatible'),
'cpuinfo_selected':[s for s in cpu.splitlines() if s.startswith(('processor','model name','Features','Hardware','CPU architecture','BogoMIPS'))] if isinstance(cpu,str) else cpu,
'memory_selected':[s for s in mem.splitlines() if s.startswith(('MemTotal','MemAvailable','CmaTotal','CmaFree','SwapTotal','SwapFree'))] if isinstance(mem,str) else mem,
'image_metadata':{p:read(p,2000) for p in ['/etc/pynq-release','/etc/image_version','/etc/issue'] if os.path.isfile(p)},
'modules':{n:module(n) for n in ['pynq','numpy','cv2','torch','torchvision','onnxruntime','ncnn','tensorflow','tflite_runtime','dnndk','finn']},
'tools':{n:command(['sh','-c','command -v '+n]) for n in ['gcc','g++','cmake','make','ffmpeg','python3','vivado','vitis_hls']},
'filesystem':command(['df','-h','/','/home/xilinx','/boot']),
'cpu_frequency':{p:read(p,500) for p in glob.glob('/sys/devices/system/cpu/cpu0/cpufreq/*') if os.path.basename(p) in ['cpuinfo_max_freq','scaling_cur_freq','scaling_governor']},
'cameras':glob.glob('/dev/video*'),'FPGA_manager':{p:read(p,1000) for p in ['/sys/class/fpga_manager/fpga0/name','/sys/class/fpga_manager/fpga0/state'] if os.path.isfile(p)}}
try:
    import pynq
    result['pynq_version']=getattr(pynq,'__version__',None)
    from pynq import PL
    result['current_PL_bitfile']=PL.bitfile_name
    result['current_PL_IP_names']=list(PL.ip_dict)
    result['available_overlay_files']=[]
    for root in [os.path.join(os.path.dirname(pynq.__file__),'overlays'),'/home/xilinx/jupyter_notebooks']:
        for directory,subdirs,files in os.walk(root):
            depth=os.path.relpath(directory,root).count(os.sep)
            if depth>=3:subdirs[:]=[]
            for name in files:
                if name.endswith(('.bit','.hwh','.tcl','.xsa','.onnx','.param')):
                    result['available_overlay_files'].append(os.path.join(directory,name))
except Exception as e:result['pynq_read_error']={'type':type(e).__name__,'detail':str(e)[:250]}
try:
    import numpy
    result['numpy_version']=numpy.__version__
except Exception:pass
try:
    import cv2
    result['opencv_version']=cv2.__version__
except Exception:pass
print(json.dumps(result,indent=2))
