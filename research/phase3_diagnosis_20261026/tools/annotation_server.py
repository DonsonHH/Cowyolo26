"""Loopback-only local preview server with byte ranges for source video seeking."""
from pathlib import Path
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
import argparse,re

ROOT=Path(__file__).resolve().parents[1]

class Handler(SimpleHTTPRequestHandler):
    def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
    def send_head(self):
        self.byte_range=None
        path=Path(self.translate_path(self.path))
        header=self.headers.get('Range')
        if not header or not path.is_file():return super().send_head()
        match=re.fullmatch(r'bytes=(\d*)-(\d*)',header)
        size=path.stat().st_size
        if not match or not size:
            self.send_error(416);return None
        start,end=match.groups()
        if not start:
            start=max(0,size-int(end));end=size-1
        else:
            start=int(start);end=min(size-1,int(end) if end else size-1)
        if start>end or start>=size:
            self.send_error(416);return None
        f=path.open('rb');f.seek(start);self.byte_range=(start,end)
        self.send_response(206);self.send_header('Content-Type',self.guess_type(str(path)))
        self.send_header('Accept-Ranges','bytes');self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
        self.send_header('Content-Length',str(end-start+1));self.end_headers();return f
    def copyfile(self,source,outputfile):
        try:
            if self.byte_range is None:return super().copyfile(source,outputfile)
            remaining=self.byte_range[1]-self.byte_range[0]+1
            while remaining:
                chunk=source.read(min(128*1024,remaining))
                if not chunk:break
                outputfile.write(chunk);remaining-=len(chunk)
        except (BrokenPipeError,ConnectionResetError,ConnectionAbortedError):pass

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8779)
    args=parser.parse_args()
    print(f'Local annotation server: http://127.0.0.1:{args.port}/annotation_workbench/index.html',flush=True)
    ThreadingHTTPServer(('127.0.0.1',args.port),Handler).serve_forever()
