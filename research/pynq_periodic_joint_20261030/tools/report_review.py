from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
v=load(ROOT/'results/independent_verification.json');m=load(ROOT/'results/media_verification.json')
assert v['actual_O8_timed_frames']==781 and v['actual_background_identity_jobs']==11 and m['photo_panels']==11
files=[ROOT/'media_delivery/results/media'/name for name in ['periodic_and_identity.png','all11_actual_photos.png']]
visual={'created_UTC':datetime.now(timezone.utc).isoformat(),'figures_actually_viewed':2,'panels_actually_viewed':15,
 'files':[{'path':str(p.resolve()),'sha256':sha(p),'panels':4 if i==0 else 11,'actually_viewed':True} for i,p in enumerate(files)],
 'observations':['Allcasecountsanddeadlinecurvelegible;all11photosshownincluding10rejects.',
 'Somecount-timephotoscropbodyedgesandincludeothercowsorbackground;identityretrievalisprovisional,nottruth.',
 'Onlyaccepted009atf9790haslabelACCEPTandscore,notconfirmedidentity;source12humanreferencekept.',
 'Naiveactualbackgroundincreasestaildelays;nohardreal-timeorcameraacquisitionclaim.']}
(ROOT/'results/visual_review.json').write_text(json.dumps(visual,indent=2)+'\n')
table='\n'.join('| '+('前台独占' if r['case']=='foreground_only' else '前台＋实际身份后台')+' | '+str(r['processed_frames'])+'/392 | '+str(r['skipped_slots'])+' | '+str(r['deadline_misses'])+' | '+f"{r['P95_release_to_count_ms']:.2f}"+' | '+f"{r['processed_per_second_over_offered_duration']:.3f}"+' | '+str(r['source_down_count'])+' |' for r in v['cases'])
report=f'''# 同一块PYNQ：5Hz前台与高分辨率身份后台

**实时检测、跟踪计数、实际高分辨率图裁剪和身份网络，已经在同一块PYNQ-Z2上联合执行。** 加入后台后，本次78.4秒回放的前台吞吐为4.962FPS，完成11个后台作业；原片计数仍为11，人工总数12。平均吞吐接近用户提出的5FPS目标，但出现3个跳帧和128个200ms截止时间超限，后台调度还有优化空间。

## 固定对照

两条件均使用新192直角seed26、用户指定`yolo26_optimization_8`、相同5Hz释放规则和同一通行片段。每条件392时隙，从源帧8915至10870；完整0–8910的实际板端历史raw在板上重放，逐项精确复现原跟踪和计数状态，之后每个处理帧都运行真实FPGA／ARM模型。

| 条件 | 处理帧 | 跳帧 | 超过200ms | 释放至计数P95 ms | 78.4s内吞吐FPS | A→B计数 |
| --- | --- | --- | --- | --- | --- | --- |
{table}

实际前台定时推理合计781次，另8次原生BGR资格控制及4次预热。781份raw与此前实际板端对应时刻逐字节相同，输入整数量化没有改变。两个条件暂时同为11头，逐事件时间与track ID仍有差异，不能将总量相同当逐事件正确；原片没有可靠人审逐事件／永久身份真值。

后台仅由当次真实计数事件触发，全未读耳标为固定模拟压力条件。每个作业读取同帧1050×1440原生物理通道JPEG95，用当次跟踪框抓拍、旋转、在板上复现Pillow11几何、运行224身份编码器，并对Aug19跨日期图库检索和拒识。11个作业均实际执行，没有使用缓存身份特征替代网络。

后台最大排队{v['maximum_background_queue_wait_ms']:.2f}ms，最大入队至结果{v['maximum_background_enqueue_to_result_ms']:.2f}ms。固定阈值接受1个预测、拒绝10个；这不是1/11身份准确率，真实事件没有可采信的永久身份标签。所有照片、输入张量、576维特征和分数均保留，独立核查11张裁剪确实来自当次同帧图像与实时框。

## 已证明与仍需完成的内容

已证明的是固定公开视频回放中的同板实际计算，以及这一负载下约5FPS的平均吞吐。前台输入为已就绪192无损帧，图像由公开视频准备；高分辨率相机用原生通道JPEG回放，耳标全未应答为模拟。没有接入真实摄像头或RFID设备，也没有把后台检索结果自动认定为真实身份。

后台CPU解码、PNG保存、预处理和网络计算会与前台竞争；本轮只是一个78.4秒运行／条件，不能据此声称对所有牧场或所有负载稳定。先保留这个直接并发基线，下一步[空闲间隙调度单因素对照](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_idle_control_20261030/计划与验收.md>)只改变后台执行时机，比较前台迟到与后台等待。

计数模型仍未解决原片12头和Toros跨来源1/6的问题。时序与算法质量分开验收，后续需要普通俯视通道数据、独立逐事件复核与同通道双向样本，不能靠改变计数边界凑出12。

## 输出与核查

- [两条件时序和全部11个后台作业](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_periodic_joint_20261030/media_delivery/results/media/periodic_and_identity.png>)
- [全部11张实际触发照片与预测／拒识](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_periodic_joint_20261030/media_delivery/results/media/all11_actual_photos.png>)
- [原始数据独立复算](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_periodic_joint_20261030/results/independent_verification.json>) · [身份网络先行ARM资格检查](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_identity_ncnn_20261029/身份编码器ARM实机部署与一致性.md>)

11照片／张量、781原始输出、4347观察时刻（含两次既定历史）及4计数事件路径独立重算。61图柱、781曲线数据点、全部照片文件对应通过核查，2图15面板实际查看。主进程2648及后台进程2960已终态退出，O8保持。启动SSH曾超时，读取板端launch与进程后继续跟随原任务，没有重复启动。

独立检索分数复算出现最多6.66×10⁻¹⁶的Float64求和顺序差异，排名及接受判断相同；数值核查使用1e-12容差，并保留诊断，不改模型、阈值或预测。这一工程阶段完成，完整科研与现场验证目标保持进行中。
'''
(ROOT/'同板前后台周期实测与下一步.md').write_text(report,encoding='utf-8')
(ROOT/'Review与当前状态.md').write_text('''# Review与当前状态

392时隙的前台独占／同板后台基线完成，原始证据已取回。前台392与389帧、0与3跳帧、23与128迟到，两组计数11。后台真实解码、抓拍、Pillow、NCNN和检索完成11作业，接受1个预测；永久身份正确率未证明。

781实际raw逐字节回归、计数路径独立扫描、11同帧照片和实际输入重建，以及全部检索分数／拒识复算通过。61图柱和曲线数据核对、全部11照片及两张图实际查看。未把约4.96FPS平均吞吐称为零迟到，未声称摄像头和RFID已接入。

历史640的12头版本与本轮所有拒识、失败门禁和启动超时记录保持。下一步空闲间隙调度控制已冻结，不据结果改模型／阈值；整体目标继续。
''',encoding='utf-8')
docs=[ROOT/r for r in ['计划与验收.md','同板前后台周期实测与下一步.md','Review与当前状态.md']]
evidence=['protocol/workload_v1.json','protocol/run_template_v1.json','protocol/run_template_v2.json','protocol/media_v1.json',
 'results/independent_verification.json','results/media_verification.json','results/visual_review.json',
 'delivery/protocol.json','delivery/results/record.json','delivery/results/terminal.json','delivery/results/foreground_with_identity/background/record.json',
 'evidence/launch_timeout_inspection.json','evidence/verifier_float64_sum_roundoff.json','tools/board_periodic_v2.py','tools/background_worker_v2.py']
result={'status':'SAME_PYNQ_ACTUAL_PERIODIC_DETECTION_AND11_REAL_BACKGROUND_IDENTITY_JOBS_REVIEWED',
 'created_UTC':datetime.now(timezone.utc).isoformat(),'actual_O8_timed_forwards':781,'O8_qualification_forwards':8,'O8_warmups':4,
 'offered_slots_per_case':392,'case_processed_frames':[392,389],'case_skipped_slots':[0,3],'case_deadline_misses':[23,128],
 'case_source_counts':[11,11],'human_confirmed_total':12,'case_throughput_FPS':[5.,389/78.4],
 'actual_same_board_background_jobs':11,'identity_warmups':1,'all11_runtime_photo_and_tensor_reconstructed':True,
 'background_accepted_provisional_predictions':1,'new_identity_accuracy_proven':False,'highres_and_RFID_inputs_are_replay_and_simulation':True,
 'counter_observation_ticks_including_history':4347,'independent_counter_event_paths':4,'all781_actual_raw_byte_exact_to_prior_real_board':True,
 'approx5FPS_mean_throughput_observed':True,'all200ms_deadlines_met':False,'stable_joint5Hz_proven':False,
 'figures_actually_viewed':2,'panels_actually_viewed':15,'new_training_updates':0,'global_model_or_runtime_replaced':False,
 'actual_processes_terminal_and_absent':True,'next_idle_gate_control_planned':True,'whole_goal_complete':False,
 'evidence_hashes':{r:sha(ROOT/r) for r in evidence},'documents':[{'path':str(doc.resolve()),'sha256':sha(doc)} for doc in docs]}
file=ROOT/'results/final_review.json';assert not file.exists();file.write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['evidence_hashes','documents']}))
