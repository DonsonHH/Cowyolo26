from pathlib import Path
import sys,argparse,urllib.request,urllib.parse,http.cookiejar,json
BASE='http://192.168.2.99:9090'
def main():
    p=argparse.ArgumentParser();p.add_argument('--output',required=True);a=p.parse_args();out=Path(a.output);assert not out.exists()
    password=sys.stdin.readline().rstrip('\r\n');jar=http.cookiejar.CookieJar();op=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(jar))
    with op.open(BASE+'/login',timeout=8) as r:r.read()
    xsrf=next(c.value for c in jar if c.name=='_xsrf')
    form=urllib.parse.urlencode({'password':password,'_xsrf':xsrf}).encode()
    with op.open(urllib.request.Request(BASE+'/login?next=%2Ftree',data=form,headers={'Referer':BASE+'/login','Content-Type':'application/x-www-form-urlencoded'}),timeout=10) as r:r.read()
    del password,form
    result={'files':{},'kernel_states':None}
    for relative in ['launch.json','results/progress.json','results/summary.json','benchmark.log']:
        url=BASE+'/api/contents/cow_research_lowres_20261029/'+relative+'?content=1'
        try:
            with op.open(url,timeout=10) as r:obj=json.loads(r.read())
            text=obj['content']
            if relative.endswith('.json'):result['files'][relative]=json.loads(text)
            else:result['files'][relative]=text[-3000:]
        except Exception as e:result['files'][relative]={'read_error':type(e).__name__,'detail':str(e)[:120]}
    try:
        with op.open(BASE+'/api/kernels',timeout=8) as r:obj=json.loads(r.read())
        result['kernel_states']=[{k:v for k,v in x.items() if k in ['id','name','execution_state','connections']} for x in obj]
    except Exception as e:result['kernel_states']={'error':type(e).__name__}
    out.write_text(json.dumps(result,indent=2)+'\n')
    summary=result['files'].get('results/summary.json')
    print(json.dumps({'progress':result['files'].get('results/progress.json'),'status':summary.get('status') if isinstance(summary,dict) else None,'log_tail':result['files'].get('benchmark.log')}))
if __name__=='__main__':main()
