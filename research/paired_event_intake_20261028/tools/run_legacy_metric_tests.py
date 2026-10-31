from pathlib import Path
import runpy,sys
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
sys.path.insert(0,str(ROOT/'deps'));sys.path.insert(0,str(PROJECT/'counting_eval_20261026/tools'))
import scipy
assert scipy.__version__=='1.16.1'
sys.argv=['test_event_metrics.py']
runpy.run_path(str(PROJECT/'counting_eval_20261026/tools/test_event_metrics.py'),run_name='__main__')
