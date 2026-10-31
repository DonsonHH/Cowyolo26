"""Read public author sources at one immutable commit; do not execute them."""
from pathlib import Path
from urllib.request import Request, urlopen
import base64, hashlib, json, time

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://api.github.com/repos/SDU-Robotics/MooTrack360'

def get(url):
    with urlopen(Request(url, headers={'User-Agent': 'CowResearch-source-audit/1.0'}), timeout=35) as r:
        assert r.status == 200
        b = r.read(2*1024*1024+1)
        assert len(b) <= 2*1024*1024
        return b

def main():
    out = ROOT/'evidence/author'; out.mkdir(parents=True, exist_ok=True)
    assert not (out/'manifest.json').exists()
    commit_b = (out/'commit.json').read_bytes() if (out/'commit.json').exists() else get(BASE+'/commits/main')
    if not (out/'commit.json').exists():(out/'commit.json').write_bytes(commit_b)
    commit = json.loads(commit_b)['sha']
    tree_b = (out/'tree.json').read_bytes() if (out/'tree.json').exists() else get(BASE+f'/git/trees/{commit}?recursive=1')
    if not (out/'tree.json').exists():(out/'tree.json').write_bytes(tree_b)
    tree = json.loads(tree_b); assert not tree.get('truncated')
    items = [e for e in tree['tree'] if e['type']=='blob' and (e['path'].endswith('.py') or e['path'] in ['README.md','LICENSE'])
             and '/tracker_models/' not in e['path'] and '/dscamera/' not in e['path']]
    assert sum(e.get('size',0) for e in items) < 2*1024*1024
    rows=[]
    for e in items:
        url=f"https://raw.githubusercontent.com/SDU-Robotics/MooTrack360/{commit}/{e['path']}"
        blob=json.loads(get(BASE+f"/git/blobs/{e['sha']}"));assert blob['encoding']=='base64'
        b=base64.b64decode(blob['content']); assert len(b)==e['size']
        assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==e['sha']
        p=out/'files'/e['path']; p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b)
        rows.append({'path':e['path'],'url':url,'bytes':len(b),'git_blob_sha1':e['sha'],'sha256':hashlib.sha256(b).hexdigest()})
    result={'status':'AUTHOR_SOURCE_PINNED_READ_ONLY','commit':commit,'selection':'Python and root README/LICENSE, excluding vendored tracker_models and dscamera libraries',
            'initial_all_python_budget_guard':'stopped before any source downloads when total exceeded 2MiB; tree and commit retained',
            'raw_host_attempt':'first raw.githubusercontent.com source request timed out before files were written; source obtained via GitHub Git blob API',
            'files':rows,'author_code_executed':False,'time_unix':time.time()}
    (out/'manifest.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'commit':commit,'files':len(rows),'bytes':sum(x['bytes'] for x in rows),'paths':[x['path'] for x in rows]}),flush=True)

if __name__=='__main__':main()
