"""Upload an artifact to the task-owned Jupyter directory; no credential persistence."""
from pathlib import Path
import sys,argparse,urllib.request,urllib.parse,http.cookiejar,json,base64,hashlib
BASE='http://192.168.2.99:9090';DIRECTORY='cow_research_lowres_20261029'
def main():
    p=argparse.ArgumentParser();p.add_argument('--file',required=True);p.add_argument('--record',required=True);a=p.parse_args()
    file=Path(a.file);out=Path(a.record);assert file.name=='board_inputs.tar.gz' and not out.exists()
    password=sys.stdin.readline().rstrip('\r\n');jar=http.cookiejar.CookieJar();op=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPCookieProcessor(jar))
    with op.open(BASE+'/login',timeout=8) as r:r.read()
    xsrf=next(c.value for c in jar if c.name=='_xsrf')
    form=urllib.parse.urlencode({'password':password,'_xsrf':xsrf}).encode()
    with op.open(urllib.request.Request(BASE+'/login?next=%2Ftree',data=form,headers={'Referer':BASE+'/login','Content-Type':'application/x-www-form-urlencoded'}),timeout=8) as r:r.read()
    del password,form
    def call(path,data=None,method=None):
        headers={'X-XSRFToken':xsrf,'Origin':BASE,'Referer':BASE+'/'}
        if isinstance(data,dict):headers['Content-Type']='application/json';data=json.dumps(data).encode()
        with op.open(urllib.request.Request(BASE+path,data=data,method=method,headers=headers),timeout=40) as r:return json.loads(r.read())
    from urllib.error import HTTPError
    try:
        current=call('/api/contents/'+DIRECTORY)
        assert current['type']=='directory' and not current.get('content'),'Ownboarddirectoryalreadyhasfiles;inspectbeforeupload'
    except HTTPError as e:
        if e.code!=404:raise
        call('/api/contents/'+DIRECTORY,{'type':'directory'},'PUT')
    data=file.read_bytes();remote=DIRECTORY+'/'+file.name
    created=call('/api/contents/'+remote,{'type':'file','format':'base64','content':base64.b64encode(data).decode()},'PUT')
    assert created['path']==remote and created['size']==len(data)
    saved={'status':'HTTP_CONTENTS_UPLOAD_COMPLETE_SIZE_VERIFIED_HASH_AWAITS_BOARD_READ','remote_path':remote,'bytes':len(data),
    'local_sha256':hashlib.sha256(data).hexdigest(),'authentication_material_saved':False}
    out.write_text(json.dumps(saved,indent=2)+'\n');print(json.dumps(saved))
if __name__=='__main__':main()
