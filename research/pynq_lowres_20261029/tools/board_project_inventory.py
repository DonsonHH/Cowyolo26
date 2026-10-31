import os,json,glob,hashlib,subprocess
root='/home/xilinx/jupyter_notebooks'
result={'project_directories':[n for n in os.listdir(root) if 'yolo26' in n.lower()],
'relevant_files':[],'processes':[],'ssh_public_host_key':None}
for project in ['yolo26_optimization_6','yolo26_optimization_5','yolo26_optimization_4','yolo26_stage_d']:
    directory=os.path.join(root,project)
    if not os.path.isdir(directory):continue
    found=[]
    for path,dirs,files in os.walk(directory):
        depth=os.path.relpath(path,directory).count(os.sep)
        if depth>=2:dirs[:]=[]
        dirs[:]=[d for d in dirs if d not in ['model','model_final','__pycache__','.ipynb_checkpoints']]
        for name in files:
            if name.endswith(('.py','.json','.csv','.sh','.md','.txt','.so')) or name in ['Makefile']:
                f=os.path.join(path,name);found.append({'path':f,'bytes':os.path.getsize(f)})
    result['relevant_files'].append({'project':project,'files':found})
for path in glob.glob('/proc/[0-9]*/cmdline'):
    try:
        data=open(path,'rb').read().decode('utf-8','replace').split('\x00')
        if any('yolo26_' in a or 'railway_' in a for a in data):
            result['processes'].append({'pid':int(path.split('/')[2]),'executable':os.path.basename(data[0]),
                'script_basenames':[os.path.basename(a) for a in data[1:] if a.endswith(('.py','.sh'))]})
    except Exception:pass
try:result['ssh_public_host_key']=open('/etc/ssh/ssh_host_ed25519_key.pub').read().strip()
except Exception:pass
try:
    f=glob.glob('/sys/bus/soc/devices/soc0/*')
    result['soc_fields']={p:open(p).read().strip() for p in f if os.path.basename(p) in ['family','machine','soc_id','revision']}
except Exception:pass
print(json.dumps(result,indent=2))
