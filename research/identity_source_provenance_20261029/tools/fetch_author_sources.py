from pathlib import Path
from urllib.request import Request,build_opener,ProxyHandler
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def request(url,limit=5*1024*1024):
    with build_opener(ProxyHandler({})).open(Request(url,headers={'User-Agent':'cow-source-provenance-audit/1.0'}),timeout=40) as r:
        data=r.read(limit+1);assert len(data)<=limit
        return data,{'url':url,'final_url':r.url,'content_type':r.headers.get('Content-Type'),'status':r.status,
                     'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest(),'fetched_UTC':datetime.now(timezone.utc).isoformat()}
def capture(name,url):
    row={'name':name,'url':url}
    try:
        data,meta=request(url);path=ROOT/'evidence/primary'/name;assert not path.exists();path.write_bytes(data)
        row={**meta,'name':name,'file':path.relative_to(ROOT).as_posix()}
    except Exception as e:row.update(error_type=type(e).__name__,error=str(e)[:200])
    return row
def main():
    current=load(ROOT/'evidence/primary/author_repo_commit.json');tree_sha=current['commit']['tree']['sha']
    repos=load(ROOT/'evidence/primary/author_public_repos.json');by_name={r['name']:r for r in repos}
    urls=[('author_repo_exact_tree.json','https://api.github.com/repos/Phoenix4582/CowIDentifier/git/trees/'+tree_sha+'?recursive=1'),
          ('arxiv_v2.html','https://arxiv.org/html/2410.12695v2'),
          ('camera1_index.html','https://data.bris.ac.uk/datasets/2inu67jru7a6821kkgehxg3cv2/MultiCamCows2024Root/videos/camera1/')]
    for name in ['DailyCowIdentifier','SpeciesIdentifier']:
        branch=by_name[name]['default_branch'];api='https://api.github.com/repos/Phoenix4582/'+name
        urls.extend([(name+'_commit.json',api+'/commits/'+branch),(name+'_tree.json',api+'/git/trees/'+branch+'?recursive=1')])
    with ThreadPoolExecutor(max_workers=4) as pool:records=list(pool.map(lambda x:capture(*x),urls))
    path=ROOT/'evidence/secondary_metadata_manifest.json';assert not path.exists();path.write_text(json.dumps(records,indent=2)+'\n',encoding='utf-8')
    tree=load(ROOT/'evidence/primary/author_repo_exact_tree.json');assert not tree.get('truncated')
    assert tree['sha']==tree_sha
    suffixes={'.py','.md','.txt','.json','.csv','.yaml','.yml','.xml'}
    blobs=[r for r in tree['tree'] if r['type']=='blob' and (Path(r['path']).suffix.lower() in suffixes or r['path']=='LICENSE') and r['size']<=262144]
    assert sum(r['size'] for r in blobs)<2*1024*1024
    dest=ROOT/'evidence/author_sources/CowIDentifier';dest.mkdir(parents=True,exist_ok=False)
    def fetch(row):
        url='https://raw.githubusercontent.com/Phoenix4582/CowIDentifier/'+current['sha']+'/'+row['path']
        data,meta=request(url,262144);blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        assert blob==row['sha'] and len(data)==row['size']
        path=dest/row['path'];path.parent.mkdir(parents=True,exist_ok=True);assert not path.exists();path.write_bytes(data)
        return {**meta,'repo_path':row['path'],'git_blob_sha':blob,'local_file':path.relative_to(ROOT).as_posix()}
    with ThreadPoolExecutor(max_workers=4) as pool:files=list(pool.map(fetch,blobs))
    report={'repository':'Phoenix4582/CowIDentifier','commit_sha':current['sha'],'exact_tree_sha':tree_sha,
            'tree_total_entries':len(tree['tree']),'tree_total_blob_files':sum(r['type']=='blob' for r in tree['tree']),
            'selected_source_files':len(files),'source_bytes':sum(r['bytes'] for r in files),'files':files,
            'selection':'Alltext/source suffixes <=256KiB, total<2MiB; bytecode not executed or inspected as source.'}
    path=ROOT/'evidence/author_source_manifest.json';assert not path.exists();path.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    for row in records:print(json.dumps(row),flush=True)
    print(json.dumps({k:v for k,v in report.items() if k!='files'}),flush=True)
if __name__=='__main__':main()
