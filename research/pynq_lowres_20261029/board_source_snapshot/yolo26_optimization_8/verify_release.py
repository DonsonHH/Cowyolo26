import pathlib,json,hashlib
def verify(root,full=False):
 root=pathlib.Path(root);m=json.loads((root/'release_manifest.json').read_text())
 for row in m['runtime_files']+(m['reproduction_files'] if full else []):
  p=root/row['path'];assert p.is_file(),str(p);assert hashlib.sha256(p.read_bytes()).hexdigest()==row['sha256'],'runtime hash mismatch: '+str(p)
 return m
if __name__=='__main__':
 import argparse
 p=argparse.ArgumentParser();p.add_argument('--full',action='store_true');a=p.parse_args();m=verify(pathlib.Path(__file__).resolve().parent,a.full);print('O8_RELEASE_HASHES_PASS',len(m['runtime_files'])+(len(m['reproduction_files']) if a.full else 0))
