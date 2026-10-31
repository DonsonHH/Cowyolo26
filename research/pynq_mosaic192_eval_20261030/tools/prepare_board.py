from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
old=PROJECT/'pynq_rot192_eval_20261029/tools'
runner=(old/'board_video_v2.py').read_text(encoding='utf-8')
runner=runner.replace('cow_research_o8_rot192_qual_20261029','cow_research_o8_mosaic192_qual_20261030')
runner=runner.replace("ROOT/'board_protocol_v2.json'","ROOT/'board_protocol.json'").replace("ROOT/'results_v2'","ROOT/'results'")
file=ROOT/'tools/board_video.py';assert not file.exists();file.write_text(runner,encoding='utf-8',newline='\n');ast.parse(runner)
tree=ast.parse(runner);node=next(n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='sha')
import hashlib
ns={'Path':Path,'hashlib':hashlib};exec(compile(ast.Module(body=[node],type_ignores=[]),'real_board_hash_helper','exec'),ns)
assert ns['sha'](str(file))==ns['sha'](file)
helper=(old/'prepare_board_payload.py').read_text(encoding='utf-8')
helper=helper.replace("Q=ROOT/'delivery/results/quality_v2'","Q=ROOT/'delivery/results/quality'").replace('protocol/eval_v2.json','protocol/eval_v1.json')
helper=helper.replace('cow_research_rot192_video_20261029','cow_research_mosaic192_video_20261030')
helper=helper.replace("py_compile.compile(str(ROOT/'tools/board_video.py'),doraise=True)","ast.parse((ROOT/'tools/board_video.py').read_text(encoding='utf-8'))")
helper=helper.replace('json,hashlib,tarfile,py_compile','json,hashlib,tarfile,ast')
file=ROOT/'tools/prepare_board_payload_generated.py';assert not file.exists();file.write_text(helper,encoding='utf-8',newline='\n');ast.parse(helper)
import subprocess,sys
subprocess.run([sys.executable,'-X','utf8',str(file)],check=True)
status=(old/'board_status_v2.sh').read_text(encoding='utf-8')
status=status.replace('cow_research_rot192_video_20261029','cow_research_mosaic192_video_20261030').replace('launch_v2.json','launch.json').replace('results_v2/','results/').replace('run_v2.log','run.log')
file=ROOT/'tools/board_status.sh';assert not file.exists();file.write_text(status,encoding='utf-8',newline='\n')
collect=(old/'collect_board.sh').read_text(encoding='utf-8').replace('cow_research_rot192_video_20261029','cow_research_mosaic192_video_20261030')
collect=collect.replace('results_v2/','results/').replace("root/'results_v2'","root/'results'").replace('board_protocol_v2.json','board_protocol.json')
before="['board_video.py','board_video_v2.py','frozen_input.py','board_protocol.json','board_protocol.json',\n 'board_input_manifest.json','launch.json','launch_v2.json','run.log','run_v2.log','failed_v1_forensic.json','final_state.json']"
after="['board_video.py','frozen_input.py','board_protocol.json','board_input_manifest.json','launch.json','run.log','final_state.json']"
assert collect.count(before)==1;collect=collect.replace(before,after)
file=ROOT/'tools/collect_board.sh';assert not file.exists();file.write_text(collect,encoding='utf-8',newline='\n')
