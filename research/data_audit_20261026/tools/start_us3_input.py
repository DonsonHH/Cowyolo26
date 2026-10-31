from pathlib import Path
import subprocess,sys
script=Path(__file__).with_name('setup_us3_memory.py')
r=subprocess.run(['ssh','-o','BatchMode=yes','-o','StrictHostKeyChecking=yes','-o','ConnectTimeout=12','renly@219.143.38.36','python /share/home/renly/projects/idcoo_research_20261026/tools/setup_us3_memory.py'],input=sys.stdin.buffer.readline(),stdout=subprocess.PIPE,stderr=subprocess.PIPE)
sys.stdout.buffer.write(r.stdout)
if r.stderr: print('Remote stderr suppressed to preserve private connection data')
raise SystemExit(r.returncode)
