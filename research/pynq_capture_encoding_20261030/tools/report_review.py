from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
e=load(ROOT/'results/encoding_verification.json');v=load(ROOT/'results/periodic_verification.json')
assert e['pixel_identical_photo_pairs']==11 and v['actual_O8_timed_forwards']==1170 and v['actual_background_identity_jobs']==22
names={'foreground_only':'前台独占','foreground_with_identity':'直接后台','foreground_idle_identity':'空闲后台'}
table='\n'.join('| '+names[r['case']]+' | '+str(r['processed_frames'])+'/392 | '+str(r['skipped_slots'])+' | '+str(r['deadline_misses'])+' | '+f"{r['P95_release_to_count_ms']:.2f}"+' | '+f"{r['processed_per_second_over_offered_duration']:.3f}"+' | '+str(r['source_down_count'])+' |' for r in v['cases'])
report=f'''# 抓拍PNG保存：像素相同、后台负担与完整实机对照

在PYNQ-Z2上，将抓拍PNG压缩级别由6改为0，11张同样照片的解码像素全部相同，平均文件保存时间由731.91ms降至99.82ms，文件总量约3倍。放回实际前后台后，直接后台完成392/392帧、平均5FPS，后台最大排队约650ms；仍有67帧超过200ms，不能宣称硬截止时间全部通过。

## 先做实际文件保存对照

全部11张此前真实抓拍均保留，按照片索引交替执行6→0或0→6，各级别各保存一次。记录实际新文件保存的CPU及墙钟时间，在计时外重新完整解码并核验RGB。没有训练、网络前向、缩图或有损照片变换。

| PNG级别 | 实际保存次数 | 平均墙钟ms | 平均CPU ms | 11文件总bytes |
| --- | --- | --- | --- | --- |
| 6 | 11 | 731.91 | 731.63 | 2593524 |
| 0 | 11 | 99.82 | 98.49 | 7753407 |

约7.33倍只对应文件保存微基准，不能直接当作系统FPS提升。

## 完整5Hz板端回放

三个条件均392时隙、78.4秒，模型、输入、阈值、跟踪、图库和全未读耳标模拟保持；两种后台条件只将PNG保存改为级别0。每一处理时刻实际运行O8模型，真实后台用当次计数、同帧高分辨率图和实际跟踪框。

| 条件 | 处理帧 | 跳帧 | 200ms迟到 | 释放至计数P95 ms | 吞吐FPS | 计数 |
| --- | --- | --- | --- | --- | --- | --- |
{table}

原片人工总数仍为12，三组都为11。1170份实际O8输出与此前对应帧逐字节一致；另有8次原生BGR控制和6次前台预热。六计数路径、6519观察时刻（含三次既定历史）独立复算。

| 后台阶段 | 原PNG6直接 | PNG0直接 | 原PNG6空闲 | PNG0空闲 |
| --- | --- | --- | --- | --- |
| 当轮前台跳帧 | 3 | 0 | 0 | 4 |
| 当轮200ms迟到 | 128 | 67 | 28 | 25 |
| 平均裁剪＋保存墙钟ms | 819.53 | 135.70 | 3159.68 | 873.06 |
| 最大后台排队ms | 1285.99 | 649.63 | 27603.60 | 5016.32 |
| 最大入队至结果ms | 2866.49 | 1878.01 | 32198.40 | 9225.38 |

空闲墙钟包括暂停，不能当作纯编码或网络速度。每个运行条件仅一次，不作统计显著性或必然优于的推断；本轮前台独占也发生2跳帧，说明还存在运行波动。不能挑无跳帧的一组就宣称系统完全达标。

## 照片与身份核查

两个后台共22次真实图像抓拍、预处理和NCNN身份网络，另各1次预热。22张照片均从当次原生通道图与当次框独立重建，输入张量及检索分数核对通过。17个新旧同帧且同框作业的照片RGB、输入张量和网络原始特征逐字节一致；其余作业因跳帧／轨迹输出变化而取帧或框不同，已保留，未假称全部配对一致。

两种后台各接受1个预测，拒绝10个。公开原片缺永久身份真值，接受数不是准确率；照片／向量／原始raw均可在本目录periodic_delivery/results内复核。输入仍是公开视频回放，RFID未应答为模拟，真实设备没有接入。

## Review与下一步

完整归档100成员、99文件哈希核查通过。保存微基准22文件／11对像素以及完整三个条件的计时、跳帧、raw、事件和后台输出独立核对完成。收集连接超时后检查到归档已完成且原任务退出，只读回既有文件和元数据，没有重复推理或覆盖产物。

这一步得到可执行取舍：PNG0显著减少保存CPU成本，但增大存储体积；空闲后台改善前台干扰却增加等待。后续需要重复会话与功耗／内存观测，以及真实相机／耳标输入，不能从单段回放外推现场性能。

当前计数质量仍为11而非12，反向跨来源只有1/6。下一步已经[定位固定192模型未计案例](<C:/Users/Donson/Documents/ChatGPT/奶牛/rot192_event_diagnosis_20261030/计划与验收.md>)，并[对齐256与320的同O8实现](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_o8_sizes_20261030/计划与验收.md>)，保持192主候选和原640成功版本。
'''
(ROOT/'抓拍无损编码与完整同板结果.md').write_text(report,encoding='utf-8')
(ROOT/'Review与当前状态.md').write_text('''# Review与当前状态

PNG微基准和三组完整5Hz实机控制完成。独立核对11对照片像素、22次文件保存；1170实际O8 raw、6事件路径、22实际后台作业与17新旧同帧／同框像素、张量、特征配对。

三个条件跳帧2／0／4、迟到20／67／25，计数均11。报告完整保留独占波动与空闲队列，未将PNG保存7.33倍提速当作整个系统提速或身份精度提升。源视频／RFID输入仍为回放和模拟。

任务5748及两后台均终态；收集超时后只读回已完成归档，未重跑或覆盖。哈希与独立数字复算后复查报告表格、计时口径、前次基线和身份真值边界。整体目标未结束，继续剩余计数案例和256／320同O8准入。
''',encoding='utf-8')
evidence=['protocol/encoding_v1.json','protocol/periodic_v1.json','results/encoding_verification.json','results/periodic_verification.json',
 'benchmark_delivery/encoding_results/summary.json','periodic_delivery/results/record.json','periodic_delivery/results/terminal.json',
 'periodic_delivery/results/foreground_with_identity/background/record.json','periodic_delivery/results/foreground_idle_identity/background/record.json',
 'evidence/collection_inspection01.json','evidence/periodic_collect_recovered.json','tools/board_periodic_capture0.py','tools/background_capture0_worker.py']
docs=[ROOT/f for f in ['计划与验收.md','抓拍无损编码与完整同板结果.md','Review与当前状态.md']]
r={'status':'PNG_PIXEL_EXACT22_WRITE_BENCHMARK_AND_THREE1170_O8_FRAME22_IDENTITY_JOB_CONTROLS_REVIEWED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'lossless_photo_pair_checks':11,'actual_board_PNG_writes':22,
 'mean_encode_wall_ms_level6':e['statistics'][0]['mean_wall_ms'],'mean_encode_wall_ms_level0':e['statistics'][1]['mean_wall_ms'],
 'actual_O8_timed_forwards':1170,'O8_qualification_forwards':8,'O8_warmups':6,'actual_background_identity_jobs':22,'identity_warmups':2,
 'case_processed_frames':[390,392,388],'case_skips':[2,0,4],'case_deadline_misses':[20,67,25],'case_source_counts':[11,11,11],
 'same_frame_same_box_prior_input_and_feature_exact_pairs':17,'all22_runtime_photos_and_tensors_reconstructed':True,
 'zero_deadline_misses_proven':False,'new_identity_accuracy_proven':False,'actual_camera_or_RFID_hardware':False,
 'all_conditions_single_run':True,'new_training_updates':0,'whole_goal_complete':False,
 'evidence_hashes':{f:sha(ROOT/f) for f in evidence},'documents':[{'path':str(f.resolve()),'sha256':sha(f)} for f in docs]}
file=ROOT/'results/final_review.json';assert not file.exists();file.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['evidence_hashes','documents']}))
