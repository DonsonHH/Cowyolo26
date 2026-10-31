"""Bounded official-source fetch with response/source hash; no executable downloads."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.request import Request,urlopen
from urllib.parse import urljoin,urlsplit
import argparse,hashlib,json
ROOT=Path(__file__).resolve().parents[1]


class Links(HTMLParser):
    def __init__(self):super().__init__();self.hrefs=[]
    def handle_starttag(self,tag,attributes):
        if tag=='a' and dict(attributes).get('href'):self.hrefs.append(dict(attributes)['href'])


def fetch(label,url,maximum=8*1024*1024):
    assert urlsplit(url).hostname in ['data.bris.ac.uk','api.github.com','raw.githubusercontent.com','arxiv.org']
    target=ROOT/'catalog'/label;target.parent.mkdir(parents=True,exist_ok=True)
    assert not target.exists(),target
    with urlopen(Request(url,headers={'User-Agent':'CattleResearch-public-label-audit/1.0'}),timeout=30) as response:
        data=response.read(maximum+1);assert len(data)<=maximum
        status=response.status;effective=response.url;content_type=response.headers.get('Content-Type','')
    target.write_bytes(data)
    record={'label':label,'requested_url':url,'effective_url':effective,'status':status,'bytes':len(data),
            'sha256':hashlib.sha256(data).hexdigest(),'content_type':content_type}
    if 'html' in content_type:
        parser=Links();parser.feed(data.decode('utf-8'))
        record['links']=[urljoin(effective,s) for s in parser.hrefs if not s.startswith('?')]
    (target.with_name(target.name+'.record.json')).write_text(json.dumps(record,indent=2),encoding='utf-8')
    return record


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('label');parser.add_argument('url');args=parser.parse_args()
    record=fetch(args.label,args.url)
    print(json.dumps({**{k:v for k,v in record.items() if k!='links'},
                      'link_count':len(record.get('links',[])),'links_first20':record.get('links',[])[:20]}),flush=True)
