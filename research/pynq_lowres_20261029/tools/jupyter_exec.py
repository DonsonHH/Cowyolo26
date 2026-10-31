"""Use the user-authorized Jupyter service; create and delete only our own kernel."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,sys,uuid,time,http.cookiejar,urllib.request,urllib.parse
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tool_deps'))
import websocket
BASE='http://192.168.2.99:9090'
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--code',required=True);parser.add_argument('--output',required=True);parser.add_argument('--quiet',action='store_true');args=parser.parse_args()
    output=Path(args.output);assert not output.exists();output.parent.mkdir(parents=True,exist_ok=True)
    password=sys.stdin.readline().rstrip('\r\n');assert password
    jar=http.cookiejar.CookieJar();opener=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(jar))
    def request(path,data=None,method=None):
        headers={'Referer':BASE+'/','Origin':BASE}
        xsrf=next((c.value for c in jar if c.name=='_xsrf'),None)
        if xsrf:headers['X-XSRFToken']=xsrf
        if isinstance(data,dict):data=json.dumps(data).encode();headers['Content-Type']='application/json'
        with opener.open(urllib.request.Request(BASE+path,data=data,headers=headers,method=method),timeout=8) as r:
            raw=r.read();return json.loads(raw) if raw and path.startswith('/api/') else None
    request('/login')
    xsrf=next(c.value for c in jar if c.name=='_xsrf')
    form=urllib.parse.urlencode({'password':password,'_xsrf':xsrf}).encode()
    with opener.open(urllib.request.Request(BASE+'/login?next=%2Ftree',data=form,headers={'Referer':BASE+'/login','Content-Type':'application/x-www-form-urlencoded'}),timeout=8) as r:
        r.read()
    del password,form
    specs=request('/api/kernelspecs');name=specs['default'];assert name in specs['kernelspecs']
    kernel=request('/api/kernels',{'name':name},'POST');kernel_id=kernel['id'];ws=None;messages=[];error=None
    session=uuid.uuid4().hex;msgid=uuid.uuid4().hex;started=time.monotonic();removed=False
    try:
        cookie='; '.join(c.name+'='+c.value for c in jar)
        ws=websocket.create_connection(BASE.replace('http://','ws://')+'/api/kernels/'+kernel_id+'/channels?session_id='+session,
            cookie=cookie,origin=BASE,timeout=10,http_proxy_host=None,http_no_proxy=['192.168.2.99'])
        code=Path(args.code).read_text(encoding='utf-8')
        ws.send(json.dumps({'header':{'msg_id':msgid,'username':'codex','session':session,'date':datetime.now(timezone.utc).isoformat(),'msg_type':'execute_request','version':'5.3'},
        'parent_header':{},'metadata':{},'content':{'code':code,'silent':False,'store_history':False,'user_expressions':{},'allow_stdin':False,'stop_on_error':True},'channel':'shell','buffers':[]}))
        idle=False;reply=False;deadline=time.monotonic()+50
        while time.monotonic()<deadline:
            try:raw=ws.recv()
            except websocket.WebSocketTimeoutException:continue
            if not raw:raise ConnectionError('OwnJupyterWebSocketclosedbeforeexecutionconfirmation')
            message=json.loads(raw)
            if message.get('parent_header',{}).get('msg_id')!=msgid:continue
            kind=message['header']['msg_type'];content=message.get('content',{})
            if kind in ['stream','error','execute_result','execute_reply']:messages.append({'type':kind,'content':content})
            if kind=='error':error={'error_type':content.get('ename'),'detail':content.get('evalue')}
            if kind=='execute_reply':reply=True
            if kind=='status' and content.get('execution_state')=='idle':idle=True
            if idle and reply:break
        assert idle and reply,'Ownkernel execution did not confirm idle and reply within50s'
    except Exception as e:
        error=error or {'error_type':type(e).__name__,'detail':str(e)[:350]}
        raise
    finally:
        if ws:ws.close()
        try:request('/api/kernels/'+kernel_id,method='DELETE');removed=True
        except Exception as e:error=error or {'cleanup_error':type(e).__name__}
        record={'created_UTC':datetime.now(timezone.utc).isoformat(),'base_URL':BASE,'own_kernel_id':kernel_id,'kernel_name':name,'own_kernel_removed':removed,
        'elapsed_s':time.monotonic()-started,'messages':messages,'error':error,'authentication_material_saved':False}
        output.write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    for r in messages if not args.quiet else []:
        if r['type']=='stream':print(r['content'].get('text',''),end='')
        if r['type']=='error':print(json.dumps({'kernel_error':r['content'].get('ename'),'detail':r['content'].get('evalue')}))
    print(json.dumps({'own_kernel_removed':removed,'record':str(output.resolve())}))
    if error:raise SystemExit(1)
if __name__=='__main__':main()
