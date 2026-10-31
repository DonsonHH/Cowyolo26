from pathlib import Path
import subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
baseline='--baseline' in sys.argv
path=ROOT/'results'/('behavior_baseline_red.txt' if baseline else 'behavior_candidate_green.txt')
assert not path.exists()
r=subprocess.run([sys.executable,'-X','utf8',str(ROOT/'tools/test_handoff.py'),*(['--baseline'] if baseline else [])],capture_output=True)
path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(r.stdout+r.stderr)
print((r.stdout+r.stderr).decode('utf-8',errors='replace'));raise SystemExit(r.returncode)
