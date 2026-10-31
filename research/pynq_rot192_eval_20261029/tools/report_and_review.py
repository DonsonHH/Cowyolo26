from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import unquote
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
q=load(ROOT/'results/independent_quality_verification.json');b=load(ROOT/'results/independent_board_verification.json');m=load(ROOT/'results/media_verification.json')
assert q['validation_matching_problems']==3142 and q['counter_paths']==12 and b['actual_video_model_forwards']==2654 and b['independent_counter_paths']==6
assert b['actual8_video_anchor_CPU_integer_raw_bytes_exact'] and b['frame_times_over200ms']==118
assert m['strict_decoded_video_frames']==1962 and m['SVG_bar_geometries']==19
media=ROOT/'media_delivery/results/media';files=[media/'quality_and_actual_board.png']+[media/('source_f'+str(f)+'.png') for f in [8995,9345,9790,10830]]
visual={'created_UTC':datetime.now(timezone.utc).isoformat(),'figures_actually_viewed':5,'panels_actually_viewed':16,
 'files':[{'path':str(p.resolve()),'sha256':sha(p),'panels':4 if i==0 else 3,'actually_viewed':True} for i,p in enumerate(files)],
 'review':'All19figurebarsandvalueslegible;source12referenceandToros6kept;fourmovieanchorsshowFP32/QDQ/actualboardonidenticalsourcecontextandorangeROI;IDsarenotpermanentidentities;futureframeandFPSclaimsabsent.'}
(ROOT/'results/visual_review.json').write_text(json.dumps(visual,indent=2)+'\n')
timings=b['timing_ms'];rows='\n'.join('| '+name+' | '+f"{timings[k]['mean']:.2f}"+' | '+f"{timings[k]['p95']:.2f}"+' | '+f"{timings[k]['max']:.2f}"+' |' for k,name in [
 ('PNG_read_ms','读取无损192图'),('preprocess_ms','转CHW／归一化'),('input_hash_check_ms','审计张量哈希'),('tensor_to_raw_ms','真实O8完整模型'),
 ('decode_restore_ms','解码及坐标还原'),('tracker_counter_ms','真实ARM跟踪计数'),('raw_memorymap_and_row_save_ms','raw写入内存映射'),('PNG_to_counter_with_raw_save_ms','读取至计数并保存raw')])
report=f'''# 新192模型：量化损失、真实PYNQ视频计数与下一步

**新192直角seed26已在用户指定的`yolo26_optimization_8`上完成整个源视频采样序列的真实检测、跟踪和计数。原片统计11头，人工确认12头；固定方法仍未满足最终采用条件。** 板端原始输出、逐时刻轨迹及事件均取回，独立复算通过。

## 模型及对照结果

模型沿用裁剪实验读取前固定的`S192_rot90_seed26`末轮权重，SHA-256为`7b01cead4841f17d561f2a6bd768f9b229f1b3bd142818d8302135d3c69ffd45`。保持192、固定通道裁剪、conf0.2、既定BYTETracker和两区域计数器。128图校准全部来自训练集，未用原片、Toros或验证图校准。本轮不新增训练、调整门限或选择seed。

| 评价条件 | FP32 ONNX | INT8 QDQ ONNX | 真实PYNQ O8整数模型 |
| --- | --- | --- | --- |
| 原片8912–10873，计数含入口确认交接 | 10 | 11 | 11 |
| 原片，仅已确认观察计数 | 9 | 9 | 10 |
| Toros，5Hz交接计数TP／FP／FN | 1／0／5 | 1／0／5 | 1／0／5 |
| Toros，30Hz采样序列交接TP／FP／FN | 1／0／5 | 1／0／5 | 1／0／5 |
| 验证集1571图，对1864躯干AABB参考的匹配 | 1819 | 1814 | 本阶段未逐图上板 |

验证匹配使用固定IoU0.5和一对一最大匹配，FP32／QDQ未匹配参考45／50、未匹配预测587／563，召回97.59%／97.32%。它不是COCO mAP，也不是原片的逐事件准确率。原片只有人工总数12，不能将“差1”解释为已经证明仅漏一头；重计和漏计可能抵消。

QDQ ONNX与O8完整整数前向不是同一个数值实现：全部2654个视频时刻的raw数组存在字节差异，原片仅确认计数也不同。选定8个实际视频输入的O8 raw与独立CPU整数参考逐字节一致，表明这8个控制向量通过硬件实现核查；没有将QDQ输出冒充板上输出。

Toros仍只识别到6个参考通行事件中的1个，来源泛化问题未解决。旧640模型原片12头里程碑保持，不被当前192结果替换。

## 实机执行范围及耗时

同一块PYNQ-Z2上完成2654个源图条件前向，另有2次预热：原片0–10873每5帧取样2175次，保留全部历史，只统计8912–10873；Toros479帧全部执行网络，再按1／6步长分别跟踪计数。94卷积使用PL，8深度卷积使用ARM；跟踪和两计数器也确实在ARM上执行。

输入是从原视频准备并逐图核验的无损192 PNG，全部2654份输入的张量哈希已独立检查，8个锚点与先前GPU真实输入逐字节一致。**这是无定时约束的板端回放；还没有真实摄像头、RFID设备或同时运行的身份编码器。** Toros按30Hz源时刻回放不表示板卡每秒处理30帧。

| 阶段 | 平均ms | P95 ms | 最大ms |
| --- | --- | --- | --- |
{rows}

两来源无定时回放吞吐分别为5.613／5.352FPS。2654帧中118帧处理时间超过200ms，不能由平均178.24ms或平均吞吐推断每帧稳定5Hz。哈希审计单独占平均12.99ms；后续时序实验会将全输入校验放在计时前，再测试原生BGR入口，必须实际比较整数输出，不能仅从表里减时间宣布提速。

## 核查和失败记录

- 服务器成功作业130568新增8450个FP32／QDQ实际前向，另8个原生整数视频锚点；3142项验证图关联、2834个视频框逆变换、12计数路径及8个Toros评分独立复算。
- 板端2654份raw、1428个还原框、2734个跟踪时刻、6计数路径及8个实际视频锚点独立核对。最终PID26302已退出，安全释放完成，已知O8固件保持。
- 首个服务器作业130567在精确像素门禁失败，发现GPU用FP32乘`1/255`、参考函数用除法，相差最多5.96×10⁻⁸；原结果保留，v2统一为原GPU张量。128训练图校准和既有权重均保持。全部256种输入像素在当前输入量化尺度下，两种归一化恰好得到相同INT8码；此项另存穷举证据，不据此宣称FP32字节相同。
- 首个板端PID25957在字符串路径哈希处、图实例化与推理前失败，空结果和日志保留；修正函数支持Path／str后在results_v2执行，原失败未覆盖。
- 视频和图没有新增推理。19个图柱、完整1962视频帧、4个视频锚点12面板计数已独立核查，5图16面板已实际查看。

## 查看输出及下一步

- [FP32／QDQ／真实PYNQ三栏视频：仅8912–10873](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_rot192_eval_20261029/media_delivery/results/media/FP32_QDQ_actual_PYNQ_8912_10873.mp4>)
- [质量与实机耗时图](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_rot192_eval_20261029/media_delivery/results/media/quality_and_actual_board.png>)
- [板端独立复算](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_rot192_eval_20261029/results/independent_board_verification.json>) · [量化质量独立复算](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_rot192_eval_20261029/results/independent_quality_verification.json>)
- [跟踪移植与ARM回归](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_frontend_port_20261029/NumPy跟踪移植与实机回归.md>) · [同板身份编码器部署计划](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_identity_ncnn_20261029/部署依据与计划.md>)

接下来测392个真实通行时刻的5Hz周期释放、跳帧及截止时间，完整记录控制条件；再接入在板上实际执行的后台身份网络，测队列等待和前台性能变化。后台仍需实际高分辨率照片预处理和图库检索；已有12事件查询不含永久身份真值，端侧执行一致性不能成为掉标找回准确率。

研究目标保持：提高低分辨率跨来源计数可靠性、建立可采信独立参考与同通道双向测试，并验证实时检测及后台身份均在PYNQ-Z2运行。当前是一个可复现的实机阶段结果，完整科研结论和稳定同板5Hz尚未达成。
'''
(ROOT/'新192量化与PYNQ视频计数结果.md').write_text(report,encoding='utf-8')
(ROOT/'Review与当前状态.md').write_text('''# Review与当前状态

本轮固定192权重的FP32／QDQ质量、真实O8视频检测和真实ARM跟踪计数已完成自审；整体研究目标仍进行中。

独立复核覆盖：3142项验证图匹配、两组5308视频raw时刻、12服务器计数路径；2654实际板端raw、6板端计数路径、1428坐标逆变换、8个板端与CPU整数向量。FP32／QDQ／O8的原片交接计数分别10／11／11，公开Toros均1／0／5，所有不利结果保留。QDQ与实际整数raw全部时刻有差异，没有拼接证据称其相同。

实际输入为服务器准备的无损PNG，全部输入哈希和8先前GPU锚点已核对。118帧超过200ms、摄像头／RFID未接入、身份未并发，故稳定完整5FPS为未证明。主候选未替换原640的12头组合。

失败130567与PID25957均保留；服务器只修正归一化以通过原GPU精确张量门禁，板端只修正路径类型支持，使用新脚本／协议／输出目录。成功130568、130575及实际PID26302均终态已核对。19个图柱及1962视频帧通过独立解码，5图16面板实际查看。

下一步5Hz周期调度和同板后台身份执行；不能按平均吞吐直接宣称达标，也不把公开源查询的临时track ID当永久奶牛身份。
''',encoding='utf-8')
docs=[ROOT/r for r in ['计划与验收.md','新192量化与PYNQ视频计数结果.md','Review与当前状态.md']];links=0
for doc in docs:
 for match in re.finditer(r'!?\[[^\]]*\]\((?:<([^>]+)>|([^\)]+))\)',doc.read_text(encoding='utf-8')):
  target=match.group(1) or match.group(2)
  if target.startswith(('http://','https://','#')):continue
  path=Path(unquote(target));path=path if path.is_absolute() else doc.parent/path;assert path.exists(),(doc,target);links+=1
accepted=PROJECT/'human_count_confirmation_20261028/results/frozen_development_candidate.json';assert sha(accepted)=='5536882add54dc5315a3865b01782c5838c5c39adcce1ea984ec8963a7079d9b'
evidence=['protocol/eval_v1.json','protocol/eval_v2.json','protocol/execution_v2.json','protocol/board_video_v1.json','protocol/board_video_v2.json','protocol/media_v1.json',
 'results/quality_transfer_verification.json','results/independent_quality_verification.json','results/independent_board_verification.json','results/media_verification.json',
 'results/visual_review.json','results/input_quant256_equivalence.json','evidence/input_normalization_diagnostic.json','board_delivery/failed_v1_forensic.json',
 'board_delivery/results_v2/record.json','board_delivery/results_v2/terminal.json','board_delivery/final_state.json',
 'delivery/results/quality_v2/summary.json','tools/evaluate_quality_v2.py','tools/board_video_v2.py','tools/frozen_input.py']
result={'status':'FIXED_ROT192_QUALITY2654_REAL_O8_VIDEO_FORWARDS6_ARM_COUNTER_PATHS_AND16_VISUAL_PANELS_REVIEWED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'model':'S192_rot90_seed26','successful_quality_job':'130568','failed_quality_job':'130567','successful_media_job':'130575',
 'real_quality_ORT_forwards':8450,'native_integer_video_anchor_forwards':8,'actual_O8_video_forwards':2654,'actual_O8_warmups':2,
 'server_validation_matching_problems':3142,'server_counter_paths':12,'actual_ARM_counter_paths':6,'actual_ARM_counter_observation_ticks':2734,
 'FP32_QDQ_actual_O8_original_counts':[10,11,11],'actual_O8_Toros_handoff_TP_FP_FN_both_sampling_rates':[1,0,5],
 'prior_human_total12_preserved':True,'original_human_event_level_GT':False,'new_independent_test':False,
 'actual8_video_anchor_raw_bytes_exact':True,'QDQ_ORT_raw_equals_actual_O8_raw':False,'actual_O8_raw_archive_arrays':2654,
 'mean_PNG_to_counter_ms':b['timing_ms']['PNG_to_counter_with_raw_save_ms']['mean'],
 'P95_PNG_to_counter_ms':b['timing_ms']['PNG_to_counter_with_raw_save_ms']['p95'],'processing_over200ms_frames':118,
 'periodic_deadline_scheduler_tested':False,'livecamera_tested':False,'simultaneous_identity_tested':False,
 'figures_actually_viewed':5,'panels_actually_viewed':16,'strict_decoded_movie_frames':1962,
 'all_input_PNG_tensors_verified':2654,'retained_historical_failures':True,'first_failed_board_forwards':0,
 'actual_board_process_terminal_and_absent':True,'original_O8_firmware_reprogrammed':False,
 'global_runtime_changed':False,'new_training_updates':0,'foreground_background_joint5FPS_proven':False,'whole_goal_complete':False,
 'retained_artifact_hashes':{accepted.relative_to(PROJECT).as_posix():sha(accepted)},'evidence_hashes':{r:sha(ROOT/r) for r in evidence},
 'documents':[{'path':str(doc.resolve()),'sha256':sha(doc)} for doc in docs],'local_links_checked':links}
file=ROOT/'results/final_review.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['evidence_hashes','documents','retained_artifact_hashes']}))
