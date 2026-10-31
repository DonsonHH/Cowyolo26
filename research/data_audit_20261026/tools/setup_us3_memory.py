"""Create an isolated loopback proxy using only the requested US3 entry.
The subscription and credential-bearing configuration stay in RAM; output is sanitized.
"""
import sys,os,subprocess,time,json,re,socket
from urllib.request import build_opener,ProxyHandler,Request
import yaml

url=sys.stdin.readline().strip()
if not url.startswith('https://'):raise SystemExit('Missing HTTPS subscription input')
try:
 with build_opener(ProxyHandler({})).open(Request(url,headers={'User-Agent':'clash.meta'}),timeout=25) as r:raw=r.read(8*1024*1024)
 cfg=yaml.safe_load(raw);proxies=cfg.get('proxies',[])
 matches=[p for p in proxies if re.search(r'US3',str(p.get('name','')),re.I)]
 print(json.dumps({'candidate_names':[p['name'] for p in matches]},ensure_ascii=False),flush=True)
 ordinary=[p for p in matches if not re.search(r'IPLC|IEPL|专线|游戏|高级|premium|倍率',str(p.get('name','')),re.I)]
 if len(ordinary)!=1:raise SystemExit('Exact ordinary US3 entry needs clarification')
 chosen=dict(ordinary[0]);chosen['name']='TASK-US3'
 port=27831
 with socket.socket() as s:
  if s.connect_ex(('127.0.0.1',port))==0:raise SystemExit('Task proxy port already occupied; inspect existing instance')
 conf={'mixed-port':port,'allow-lan':False,'bind-address':'127.0.0.1','mode':'rule','log-level':'silent','ipv6':False,'proxies':[chosen],'proxy-groups':[{'name':'TASK-DOWNLOAD','type':'select','proxies':['TASK-US3']}],'rules':['MATCH,TASK-DOWNLOAD'],'profile':{'store-selected':False,'store-fake-ip':False}}
 fd=os.memfd_create('idcoo-us3-config',0);os.write(fd,yaml.safe_dump(conf,allow_unicode=True).encode());os.lseek(fd,0,0)
 cache='/share/home/renly/.cache/idcoo_us3_20261026';os.makedirs(cache,mode=0o700,exist_ok=True)
 proc=subprocess.Popen(['/share/home/renly/.local/bin/mihomo','-d',cache,'-f','/proc/self/fd/'+str(fd)],stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,pass_fds=(fd,),start_new_session=True)
 os.close(fd)
 for _ in range(30):
  if proc.poll() is not None:raise SystemExit('Task proxy startup failed; credentials not logged')
  with socket.socket() as s:
   if s.connect_ex(('127.0.0.1',port))==0:break
  time.sleep(.3)
 op=build_opener(ProxyHandler({'https':'http://127.0.0.1:'+str(port),'http':'http://127.0.0.1:'+str(port)}))
 with op.open('https://www.cloudflare.com/cdn-cgi/trace',timeout=30) as r:trace=r.read().decode()
 loc=next((x.split('=',1)[1] for x in trace.splitlines() if x.startswith('loc=')),None)
 print(json.dumps({'pid':proc.pid,'listen':'127.0.0.1:'+str(port),'selection':'ordinary US3 only','https_verified':True,'exit_country':loc,'credentials_on_disk':False}),flush=True)
except Exception as e:
 print(json.dumps({'error_type':type(e).__name__,'detail':'Proxy setup failed; private inputs suppressed'}),flush=True);raise SystemExit(1)
