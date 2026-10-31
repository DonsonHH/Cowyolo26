from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile,ast
ROOT=Path(__file__).resolve().parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
meta=json.loads(load(ROOT/'board_collect.json')['stdout']);archive=ROOT/'board_results_delivery.tar.gz'
assert archive.stat().st_size==meta['bytes'] and sha(archive)==meta['sha256']
out=ROOT/'board_delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
 members=tar.getmembers();assert len(members)==meta['members']
 for m in members:
  assert m.isfile() and not m.name.startswith('/') and '..' not in Path(m.name).parts
  path=(out/m.name).resolve();assert path.is_relative_to(out.resolve()) and not path.exists()
  path.parent.mkdir(parents=True,exist_ok=True);path.write_bytes(tar.extractfile(m).read())
manifest=load(out/'result_manifest.json')
for row in manifest:
 path=out/row['file'];assert sha(path)==row['sha256'] and path.stat().st_size==row['bytes']
protocol=load(ROOT/'board_regression_v1.json');server=load(ROOT/'server_regression_summary.json');board=load(out/'regression_results/summary.json');terminal=load(out/'regression_results/terminal.json')
assert sha(out/'board_regression_v1.json')==sha(ROOT/'board_regression_v1.json')==board['protocol_sha256']
assert terminal['summary_sha256']==sha(out/'regression_results/summary.json')
assert terminal['status']==board['status']=='ALL90_REAL_ARM_TRACES180_COUNTER_PATHS82020_TICKS_PASS_FROZEN_TOLERANCES'
assert server['trace_count']==len(board['reports'])==90 and server['observation_ticks']==board['observation_ticks']==82020
assert server['post_tracker_rows']==board['post_tracker_rows']==40893 and board['counter_paths']==server['counter_paths']==180
assert board['torch_imported'] is False and board['real_network_forwards']==board['PL_actions']==0
for a,b in zip(board['reports'],server['traces']):
 assert all(a[k]==b[k] for k in ['mode','scene','condition','stride','observation_ticks'])
 assert a['IDs_and_events_exact'] and b['complete_trace_exact']
 assert a['max_box_difference']<=.002 and a['max_axis_difference']<=2e-6
assert max(r['max_box_difference'] for r in board['reports'])==board['maximum_box_pixel_difference']==.0001220703125
assert max(r['max_axis_difference'] for r in board['reports'])==board['maximum_normalized_axis_difference']
for row in protocol['files']:
 if not row['file'].startswith('cached/'):
  assert sha(out/row['file'])==sha(ROOT/row['file'])==row['sha256']
upstream=load(ROOT/'upstream_manifest.json');classes_checked=functions_checked=0
for module,name in [('ultralytics.trackers.byte_tracker','byte_tracker.py'),('ultralytics.trackers.basetrack','basetrack.py'),
                    ('ultralytics.trackers.utils.kalman_filter','kalman_filter.py'),('ultralytics.trackers.utils.stracks','stracks.py'),
                    ('ultralytics.trackers.utils.matching','matching.py')]:
 original=ast.parse((ROOT/'upstream'/upstream['sources'][module]['file']).read_text(encoding='utf-8'))
 ported=ast.parse((ROOT/'cow_tracker'/name).read_text(encoding='utf-8'))
 for node in original.body:
  if isinstance(node,(ast.ClassDef,ast.FunctionDef,ast.AsyncFunctionDef)):
   other=next(x for x in ported.body if isinstance(x,type(node)) and x.name==node.name)
   assert ast.dump(node,include_attributes=False)==ast.dump(other,include_attributes=False)
   classes_checked+=isinstance(node,ast.ClassDef);functions_checked+=isinstance(node,(ast.FunctionDef,ast.AsyncFunctionDef))
result={'status':'FROZEN_TRACKER_CORE_AST_AND90_SERVER_PLUS90_REAL_ARM_TRACES_REVIEWED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'upstream_class_definitions_AST_exact':classes_checked,
 'upstream_top_level_functions_AST_exact':functions_checked,'server_traces_exact':90,'actual_board_traces':90,
 'server_and_board_counter_paths_each':180,'server_and_board_observation_ticks_each':82020,'actual_board_post_tracker_rows':40893,
 'maximum_board_vs_reference_box_pixels':board['maximum_box_pixel_difference'],
 'maximum_board_vs_reference_normalized_axis_difference':board['maximum_normalized_axis_difference'],
 'all_board_track_IDs_and_counter_events_runtime_checked_exact':True,
 'archived_board_evidence_scope':'All90case comparison summaries and logs; full intermediate board regression traces not serialized. Next actual video replay stores raw and all traces.',
 'board_numpy_global_version':'1.21.5','LAP_version':'0.5.13','LAP_upstream_min_numpy':'1.21.6',
 'task_specific_compilation_and_regression_proven':True,'general_LAP_numpy_compatibility_certified':False,'global_dependency_changes':False,
 'model_forwards':0,'PL_actions':0,'new_training_updates':0,'board_regression_process_terminal_and_absent':True,
 'whole_goal_complete':False,'archive_sha256':sha(archive),'archive_members':len(members),
 'evidence_hashes':{r:sha(ROOT/r) for r in ['regression_v1.json','board_regression_v1.json','server_regression_summary.json','board_regression.py','frame_pipeline.py','source_import_changes.diff','lap_source_provenance.json','board_regression_status02.json']}}
file=ROOT/'independent_verification.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n')
(ROOT/'NumPy跟踪移植与实机回归.md').write_text('''# NumPy跟踪计数移植与实机回归

PYNQ-Z2已经能在不加载Torch的情况下执行既定BYTETracker和两种计数器。服务器对90条轨迹、180条计数路径、82020个时刻完整重放，结果与原缓存精确一致；实际ARM板上相同90条轨迹全部通过，track ID和计数事件保持一致。

板端40893个跟踪框与服务器最多相差0.0001220703125像素，归一化轴坐标最多相差约4.24×10⁻⁸，均低于事先冻结的0.002像素与2×10⁻⁶门限。服务器作业130566完成／0:0；板端PID23488正常终态且已退出，耗时431.68秒。该时间对应纯CPU缓存回归，不是模型推理吞吐。

移植从实际使用的Ultralytics8.4.63源码提取：跟踪类、Kalman数学、关联及轨迹池函数的AST保持；只调整包导入、NumPy边界框接口与依赖加载。AABB路径、置信度、LAP0.5.13求解器、空输出时保留未确认框的原行为及计数规则保持。所有源文件保留AGPL标记，局部差异见source_import_changes.diff；旋转框路径明确不支持。

LAP0.5.13在独立任务目录从原始源码编译，没有修改系统包。原包声明NumPy最低1.21.6，现有板卡为1.21.5；这里以原板头文件完成扩展编译并通过本任务全部回归，不能据此认证整个LAP库的兼容性。板卡全局NumPy保持。

本轮板端保留90组比较摘要和日志，完整中间回归轨迹未另行序列化；后续真实模型视频回放将保存全部raw和逐时刻轨迹。当前通过说明移植可用于下一步实机视频检测计数，尚未证明实时摄像头采集、后台身份识别或同板联合5FPS。
''',encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='evidence_hashes'}))
