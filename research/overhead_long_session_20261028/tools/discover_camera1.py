"""Inspect the ordinary-overhead camera1 directory, before reading new pixels."""
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.parse import urljoin,unquote,urlparse
from html.parser import HTMLParser
import argparse,hashlib,json,time

ROOT=Path(__file__).resolve().parents[1]
URL='https://data.bris.ac.uk/datasets/2inu67jru7a6821kkgehxg3cv2/MultiCamCows2024Root/videos/camera1/'
class Links(HTMLParser):
    def __init__(self):super().__init__();self.values=[]
    def handle_starttag(self,t,a):
        if t=='a':self.values.extend(v for k,v in a if k=='href')

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--date',choices=['2023Aug17']);args=parser.parse_args()
    url=URL+(args.date+'/' if args.date else '')
    tag='camera1_'+args.date+'_listing' if args.date else 'camera1_listing'
    out=ROOT/'evidence';out.mkdir(parents=True,exist_ok=True);dest=out/(tag+'.html');assert not dest.exists()
    with urlopen(Request(url,headers={'User-Agent':'ID-Coo-overhead-long-session-audit'}),timeout=30) as r:
        assert r.status==200 and urlparse(r.url).hostname=='data.bris.ac.uk'
        b=r.read(2*1024*1024+1);assert len(b)<=2*1024*1024
    dest.write_bytes(b);parser=Links();parser.feed(b.decode('utf-8'))
    urls=sorted(set(urljoin(url,u) for u in parser.values if urljoin(url,u).startswith(url) and u.lower().endswith('.mp4')))
    rows=[{'filename':unquote(u.split('/')[-1]),'url':u} for u in urls]
    result={'status':'OFFICIAL_CAMERA1_LISTING_READ_BEFORE_PIXEL_INSPECTION','url':url,'sha256':hashlib.sha256(b).hexdigest(),'bytes':len(b),'videos':rows,'time_unix':time.time()}
    (out/(tag+'.json')).write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'status':result['status'],'video_entries':len(rows),'first':rows[:3],'last':rows[-3:],'dates':sorted(set(r['filename'][:10] for r in rows))}),flush=True)

if __name__=='__main__':main()
