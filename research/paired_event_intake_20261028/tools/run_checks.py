from pathlib import Path
import argparse,json,re,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser();parser.add_argument('--tag',default='directional_final');options=parser.parse_args()
assert re.fullmatch(r'[a-z0-9_]+',options.tag)
records=[]
for name,args,count in [('pipeline',[str(ROOT/'tools/test_pipeline.py'),'--output',str(ROOT/f'results/pipeline_test_results_{options.tag}.json')],22),
                       ('legacy_metrics',[str(ROOT/'tools/run_legacy_metric_tests.py')],6)]:
    target=ROOT/f'results/{name}_{options.tag}_tests.log';assert not target.exists()
    r=subprocess.run([sys.executable,'-X','utf8',*args],capture_output=True);target.write_bytes(r.stdout+r.stderr)
    text=(r.stdout+r.stderr).decode('utf-8',errors='replace');assert r.returncode==0,text[-2000:]
    assert f'Ran {count} tests' in text
    records.append({'suite':name,'tests':count,'exit_code':r.returncode,'log':str(target)})
out={'status':'ALL28_INTAKE_AND_ORIGINAL_MATCHER_TESTS_PASS','suites':records,'reference_fixtures_are_software_only':True,'real_reference_received':False}
target=ROOT/f'results/all_test_results_{options.tag}.json';assert not target.exists();target.write_text(json.dumps(out,indent=2),encoding='utf-8');print(json.dumps(out))
