from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import hashlib,json
from fetch_author_sources import request,capture,ROOT,load
def main():
    manifest=[]
    for repo in ['DailyCowIdentifier','SpeciesIdentifier']:
        c=load(ROOT/'evidence/primary'/(repo+'_commit.json'));tree=load(ROOT/'evidence/primary'/(repo+'_tree.json'))
        assert not tree.get('truncated')
        suffixes={'.py','.txt','.md','.yml','.yaml','.json','.csv','.xml'}
        blobs=[r for r in tree['tree'] if r['type']=='blob' and (Path(r['path']).suffix in suffixes or r['path']=='LICENSE') and r['size']<=262144]
        assert sum(r['size'] for r in blobs)<2*1024*1024
        dest=ROOT/'evidence/author_sources'/repo;dest.mkdir(exist_ok=False)
        def fetch(row):
            url='https://raw.githubusercontent.com/Phoenix4582/'+repo+'/'+c['sha']+'/'+row['path']
            data,meta=request(url,262144);blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
            assert blob==row['sha'] and len(data)==row['size']
            path=dest/row['path'];path.parent.mkdir(parents=True,exist_ok=True);assert not path.exists();path.write_bytes(data)
            return {**meta,'repo_path':row['path'],'git_blob_sha':blob,'local_file':path.relative_to(ROOT).as_posix()}
        with ThreadPoolExecutor(max_workers=4) as pool:files=list(pool.map(fetch,blobs))
        manifest.append({'repository':'Phoenix4582/'+repo,'commit_sha':c['sha'],'commit_tree_sha':c['commit']['tree']['sha'],
                         'tree_blob_files':sum(r['type']=='blob' for r in tree['tree']),'selected_source_files':len(files),
                         'source_bytes':sum(r['bytes'] for r in files),'files':files})
    path=ROOT/'evidence/related_source_manifest.json';assert not path.exists();path.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf-8')
    extra=capture('camera1_day14.html','https://data.bris.ac.uk/datasets/2inu67jru7a6821kkgehxg3cv2/MultiCamCows2024Root/videos/camera1/2023Aug14/')
    path=ROOT/'evidence/camera1_day14_capture.json';assert not path.exists();path.write_text(json.dumps(extra,indent=2)+'\n',encoding='utf-8')
    for repo in manifest:print(json.dumps({k:v for k,v in repo.items() if k!='files'}))
    print(json.dumps(extra))
if __name__=='__main__':main()
