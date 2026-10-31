"""Pinned-key SSH and task-local file transfers; passwords are stdin-only."""
from pathlib import Path,PurePosixPath
from datetime import datetime,timezone
import argparse,sys,json,base64,hashlib,shlex
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tool_deps'));import paramiko
p=argparse.ArgumentParser();p.add_argument('--host',default='192.168.2.99');p.add_argument('--output',required=True)
g=p.add_mutually_exclusive_group(required=True);g.add_argument('--run-file');g.add_argument('--put-local');g.add_argument('--get-remote')
p.add_argument('--remote');p.add_argument('--local');p.add_argument('--sudo',action='store_true');p.add_argument('--timeout',type=int,default=30);a=p.parse_args();out=Path(a.output);assert not out.exists()
raw=json.loads((ROOT/'evidence/board_project_inventory.json').read_text());obj=json.loads(''.join(r['content'].get('text','') for r in raw['messages'] if r['type']=='stream'))
public=obj['ssh_public_host_key'].split();assert public[0]=='ssh-ed25519';key=paramiko.Ed25519Key(data=base64.b64decode(public[1]))
fingerprint='SHA256:'+base64.b64encode(hashlib.sha256(key.asbytes()).digest()).decode().rstrip('=')
assert fingerprint=='SHA256:TB0FfGjfMzgZUv/reJgTpeq/AM68sMCpGC5xm6Pit7o'
client=paramiko.SSHClient();client.get_host_keys().add(a.host,'ssh-ed25519',key);client.set_missing_host_key_policy(paramiko.RejectPolicy())
password=sys.stdin.readline().rstrip('\r\n');assert password
record={'created_UTC':datetime.now(timezone.utc).isoformat(),'host':a.host,'user':'xilinx','host_fingerprint_SHA256':fingerprint,
        'authentication_material_saved':False};exit_code=1
def allowed(remote):
    path=PurePosixPath(remote);assert path.is_absolute() and '..' not in path.parts
    assert str(path).startswith('/home/xilinx/jupyter_notebooks/cow_research_'),remote
try:
    client.connect(a.host,username='xilinx',password=password,look_for_keys=False,allow_agent=False,timeout=10,banner_timeout=20,auth_timeout=35)
    if a.run_file:
        command=Path(a.run_file).read_text(encoding='utf-8');assert command.strip()
        stdin,stdout,stderr=client.exec_command('sudo -S -p "" -- bash -s' if a.sudo else 'bash -s',timeout=a.timeout)
        stdin.write((password+'\n' if a.sudo else '')+command);del password;stdin.channel.shutdown_write()
        record['stdout']=stdout.read().decode('utf-8','replace');record['stderr']=stderr.read().decode('utf-8','replace')
        exit_code=stdout.channel.recv_exit_status();record.update({'status':'SSH_COMMAND_FINISHED','exit_code':exit_code,'sudo':a.sudo,'command_file':str(Path(a.run_file).resolve())})
    elif a.put_local:
        assert a.remote;allowed(a.remote);local=Path(a.put_local);assert local.is_file();sftp=client.open_sftp()
        try:sftp.stat(a.remote);raise FileExistsError(a.remote)
        except FileNotFoundError:pass
        sftp.put(str(local),a.remote);remote=sftp.file(a.remote,'rb');digest=hashlib.sha256()
        for block in iter(lambda:remote.read(1024*1024),b''):digest.update(block)
        remote.close();assert digest.hexdigest()==hashlib.sha256(local.read_bytes()).hexdigest();stat=sftp.stat(a.remote);sftp.close()
        assert stat.st_size==local.stat().st_size;record.update({'status':'SSH_TASK_FILE_PUT_AND_REMOTE_HASH_VERIFIED','remote':a.remote,'bytes':stat.st_size,'sha256':digest.hexdigest()});exit_code=0
    else:
        assert a.local;allowed(a.get_remote);local=Path(a.local);assert not local.exists();local.parent.mkdir(parents=True,exist_ok=True)
        sftp=client.open_sftp();stat=sftp.stat(a.get_remote);sftp.get(a.get_remote,str(local));sftp.close()
        assert stat.st_size==local.stat().st_size;record.update({'status':'SSH_TASK_FILE_GET_COMPLETE','remote':a.get_remote,'local':str(local.resolve()),'bytes':stat.st_size,'sha256':hashlib.sha256(local.read_bytes()).hexdigest()});exit_code=0
except Exception as e:record.update({'status':'SSH_ERROR','error_type':type(e).__name__,'detail':str(e)[:800]})
finally:client.close()
out.write_text(json.dumps(record,indent=2)+'\n');print(json.dumps(record));sys.exit(exit_code)
