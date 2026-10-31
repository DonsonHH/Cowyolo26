from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
v=load(ROOT/'results/independent_verification.json');g=load(ROOT/'results/idle_gate_verification.json');m=load(ROOT/'results/media_verification.json')
assert v['actual_O8_timed_frames']==783 and g['actual_stop_resume_pairs']==392 and m['photo_links']==11
files=[ROOT/'media_delivery/results/media'/f for f in ['idle_control_all_runs.png','all11_idle_photos.png']]
visual={'created_UTC':datetime.now(timezone.utc).isoformat(),'figures_actually_viewed':2,'panels_actually_viewed':15,
 'files':[{'path':str(f.resolve()),'sha256':sha(f),'panels':4 if i==0 else 11,'actually_viewed':True} for i,f in enumerate(files)],
 'review':'Allfourhistorical/currentrunsvisible;28latenotzero;queuecost27.6sdisclosed;all11photosincludingrejects;pausebarsareacknowledgedintervals,networkbarselapsedincludespauses.'}
(ROOT/'results/visual_review.json').write_text(json.dumps(visual,indent=2)+'\n')
report=f'''# 空闲间隙身份推理：前台保护与后台等待

同一块PYNQ-Z2上，只改变后台执行时机：每次前台关键处理前暂停唯一自有身份进程并等待系统确认，前台计数完成后恢复后台真实计算。本次空闲后台条件完成392/392帧、无跳帧、11个身份作业，原片计数11，吞吐5FPS；仍有28帧超过200ms截止时间。

| 单次运行条件 | 处理帧 | 跳帧 | 200ms迟到 | 释放至计数P95 ms |
| --- | --- | --- | --- | --- |
| 上轮前台独占 | 392 | 0 | 23 | 206.26 |
| 上轮直接并发身份 | 389 | 3 | 128 | 335.18 |
| 本轮前台独占 | 391 | 1 | 17 | 189.48 |
| 本轮空闲后台 | 392 | 0 | 28 | 225.56 |

所有运行计数均11，对照人工总数12。保留本轮独占也有跳帧这一结果；每条件单次78.4秒，不能据此推断统计显著性或对所有负载的保证。

记录含392对SIGSTOP确认／SIGCONT时刻，全部前台关键处理位于已确认停止区间。11个真实身份网络调用跨空闲间隙推进，网络进程CPU均值{g['mean_network_CPU_ms']:.2f}ms，而计入暂停的网络墙钟均值{g['mean_network_elapsed_ms']:.2f}ms；后者不是纯网络推理速度。最长队列等待{g['max_queue_ms']/1000:.2f}秒、最长入队至结果{g['max_enqueue_to_result_ms']/1000:.2f}秒，前台保护带来明显后台延迟。

后台照片裁剪及PNG保存阶段计入暂停后平均{g['mean_photo_crop_and_save_elapsed_ms']:.2f}ms。上一轮直接并发该阶段平均819.53ms，已高于身份网络本身；下一步[无损抓拍编码对照](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_capture_encoding_20261030/计划与验收.md>)只改变PNG压缩级别，保持照片像素、模型和阈值。

783实际前台raw与此前对应帧逐字节一致，4349观察时刻含历史、4计数路径及11同帧原生照片／网络输入和检索独立复算。系统实际暂停区间和进程CPU时间核查通过。SIGCONT后的时间戳是父进程返回时刻，不能把它全部当成“仍暂停”；独立复算只将停止确认到前台完成的区间认定为确定暂停，并保留原诊断。

两网络、照片预处理与检索均在板上运行。输入依然为公开图像回放和全未读RFID模拟，实际永久身份标签没有补齐；接受1个预测不代表身份找回正确率。PID3918及身份进程4177已退出，原O8固件保持。

- [四条件时序、CPU与暂停区间图](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_idle_control_20261030/media_delivery/results/media/idle_control_all_runs.png>)
- [全部11张实际照片](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_idle_control_20261030/media_delivery/results/media/all11_idle_photos.png>)
- [独立核查](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_idle_control_20261030/results/independent_verification.json>) · [暂停与CPU核查](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_idle_control_20261030/results/idle_gate_verification.json>)

30图柱、1564个四运行曲线数据点、392暂停区间及11照片文件对应通过核查，2图15面板已实际查看。当前完成调度单因素实测，仍未达成零200ms迟到、人工12头及独立现场论文验证。
'''
(ROOT/'空闲后台调度结果与等待代价.md').write_text(report,encoding='utf-8')
(ROOT/'Review与当前状态.md').write_text('''# Review与当前状态

空闲后台控制完成并独立复算。保留全部四运行：直接后台128迟到／3跳帧，空闲后台28迟到／0跳帧；对应前台独占23／0及17／1。所有计数11，不把总数一致当逐事件相同或人工12头完成。

392系统确认暂停区间、11真实网络CPU记录与全部照片／张量／检索核对。后台最长排队27.60秒、入队至结果32.20秒已明确报告。SIGCONT父进程返回时刻不被当作精确子进程恢复瞬间；核对采用确定暂停区间。2图15面板实际查看，保留所有拒识。

媒体收集第一次字段名检查失败，尚未生成archive；修正检查键后只收集既有产物，没有重做模型或板端任务。下一步无损PNG保存控制已冻结，原历史、模型及阈值保持。整体研究目标进行中。
''',encoding='utf-8')
evidence=['protocol/run_v1.json','protocol/media_v1.json','results/independent_verification.json','results/idle_gate_verification.json',
 'results/media_verification.json','results/visual_review.json','delivery/results/record.json','delivery/results/terminal.json',
 'delivery/results/foreground_idle_identity/worker_pause_intervals.json','delivery/results/foreground_idle_identity/background/record.json',
 'evidence/CPU_clock_vs_resume_timestamp_diagnostic.json','tools/board_idle.py','tools/background_idle_worker.py']
docs=[ROOT/f for f in ['计划与验收.md','空闲后台调度结果与等待代价.md','Review与当前状态.md']]
r={'status':'ACTUAL_IDLE_GATED_PYNQ783_FRAMES392_STOP_WINDOWS_AND11_BACKGROUND_JOBS_REVIEWED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'actual_O8_timed_forwards':783,'O8_qualification_forwards':8,'O8_warmups':4,
 'case_processed_frames':[391,392],'case_skipped_slots':[1,0],'case_late_frames':[17,28],'case_source_down_counts':[11,11],
 'actual_same_board_identity_jobs':11,'actual_stop_resume_pairs':392,'actual_worker_network_CPU_mean_ms':g['mean_network_CPU_ms'],
 'background_max_queue_ms':g['max_queue_ms'],'background_max_enqueue_to_result_ms':g['max_enqueue_to_result_ms'],
 'actual_idle_throughput_FPS':5.,'all200ms_deadlines_met':False,'source_human12_complete':False,
 'real_camera_or_RFID_connected':False,'new_permanent_identity_accuracy_proven':False,'new_training_updates':0,
 'figures_actually_viewed':2,'panels_actually_viewed':15,'each_condition_single_run_not_statistical_significance':True,
 'whole_goal_complete':False,'evidence_hashes':{f:sha(ROOT/f) for f in evidence},
 'documents':[{'path':str(f.resolve()),'sha256':sha(f)} for f in docs]}
file=ROOT/'results/final_review.json';assert not file.exists();file.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k not in ['evidence_hashes','documents']}))
