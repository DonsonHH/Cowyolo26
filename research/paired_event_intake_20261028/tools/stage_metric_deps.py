"""Install only the pinned original scoring dependency into this phase folder."""
from pathlib import Path
import hashlib,json,platform,subprocess,sys,urllib.request
ROOT=Path(__file__).resolve().parents[1]
def main():
    assert sys.platform=='win32' and sys.version_info[:2]==(3,12) and platform.machine().lower() in ['amd64','x86_64']
    deps=ROOT/'deps';wheels=ROOT/'wheels';assert not deps.exists() and not wheels.exists();wheels.mkdir()
    version='1.16.1';url=f'https://pypi.org/pypi/scipy/{version}/json'
    with urllib.request.urlopen(url,timeout=30) as response:metadata=json.load(response)
    item=next(r for r in metadata['urls'] if r['filename']==f'scipy-{version}-cp312-cp312-win_amd64.whl')
    assert item['url'].startswith('https://files.pythonhosted.org/')
    with urllib.request.urlopen(item['url'],timeout=30) as response:data=response.read()
    assert len(data)==item['size'] and hashlib.sha256(data).hexdigest()==item['digests']['sha256']
    wheel=wheels/item['filename'];wheel.write_bytes(data)
    run=subprocess.run([sys.executable,'-m','pip','install','--disable-pip-version-check','--no-index','--no-deps','--target',str(deps),str(wheel)],capture_output=True)
    (ROOT/'results/metric_dependency_install.log').write_bytes(run.stdout+run.stderr);assert run.returncode==0,run.stderr[-1000:]
    record={'package':'scipy','version':version,'registry_metadata_url':url,'download_url':item['url'],
            'wheel':wheel.name,'wheel_bytes':len(data),'wheel_sha256':item['digests']['sha256'],
            'target':str(deps),'global_or_bundled_environment_modified':False,
            'requires_python':metadata['info']['requires_python'],'requires_dist':metadata['info']['requires_dist']}
    (ROOT/'results/metric_dependency_record.json').write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps({k:record[k] for k in ['package','version','wheel','wheel_bytes','wheel_sha256','global_or_bundled_environment_modified']}))
if __name__=='__main__':main()
