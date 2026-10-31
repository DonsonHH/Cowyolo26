"""Task-local SSH/SCP bridge; preserves host verification and never reads secrets."""
from pathlib import Path
import argparse, subprocess, shlex, json, sys

HOST='renly@219.143.38.36'
SSH=['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=15','-o','ServerAliveInterval=20',HOST]
GUARD='test "$(id -un)" = renly && test "$(hostname)" = mu01 && test "$HOME" = /share/home/renly || exit 97\n'

def main():
 p=argparse.ArgumentParser(); sub=p.add_subparsers(dest='action',required=True)
 x=sub.add_parser('run');x.add_argument('script');x.add_argument('--output')
 x=sub.add_parser('put');x.add_argument('local');x.add_argument('remote')
 x=sub.add_parser('get');x.add_argument('remote');x.add_argument('local')
 a=p.parse_args()
 if a.action=='run':
  data=(GUARD+Path(a.script).read_text(encoding='utf-8')).encode()
  r=subprocess.run(SSH+['bash -l -s'],input=data,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
  if a.output: Path(a.output).parent.mkdir(parents=True,exist_ok=True);Path(a.output).write_bytes(r.stdout)
  sys.stdout.buffer.write(r.stdout);sys.stderr.buffer.write(r.stderr);return r.returncode
 if a.action=='put':
  remote=a.remote
  if not remote.startswith('/share/home/renly/'): raise ValueError('Remote path outside authorized home')
  cmd=GUARD+'mkdir -p -- '+shlex.quote(str(Path(remote).parent).replace('\\','/'))+'\ncat > '+shlex.quote(remote)
  # Paths below are POSIX even when this script runs on Windows.
  import posixpath
  cmd=GUARD+'mkdir -p -- '+shlex.quote(posixpath.dirname(remote))+'\ncat > '+shlex.quote(remote)
  with Path(a.local).open('rb') as f:r=subprocess.run(SSH+['bash -lc '+shlex.quote(cmd)],stdin=f)
  return r.returncode
 if not a.remote.startswith('/share/home/renly/'): raise ValueError('Remote path outside authorized home')
 dest=Path(a.local);dest.parent.mkdir(parents=True,exist_ok=True)
 if dest.exists(): raise FileExistsError(dest)
 with dest.open('wb') as f:r=subprocess.run(SSH+['cat -- '+shlex.quote(a.remote)],stdout=f)
 return r.returncode
if __name__=='__main__':raise SystemExit(main())
