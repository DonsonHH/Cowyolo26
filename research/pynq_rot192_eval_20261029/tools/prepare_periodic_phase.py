from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
PROJECT=Path(__file__).resolve().parents[2];ROOT=PROJECT/'pynq_periodic_joint_20261030';ROOT.mkdir(exist_ok=False)
for d in ['protocol','tools','results','evidence']:(ROOT/d).mkdir()
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
p={'status':'FROZEN_BEFORE_PREPARING_PERIODIC_AND_CONCURRENT_WORKLOAD','created_UTC':datetime.now(timezone.utc).isoformat(),
 'frontend_model':'S192_rot90_seed26','source_scope_inclusive':[8912,10873],'sample_frame0_start':8915,'sample_frame0_end':10870,
 'offered_periodic_slots':392,'period_ns':200000000,'policy':'Fixed5Hzrelease,newestavailableonly,skipslogged;deadlinefromrelease+200ms;allstagewalltimecounted.',
 'frontend_cases':['foreground_only','foreground_with_actual_count_triggered_background_identity'],
 'backend_encoder':'C_letterbox_trained_seed26','backend_threads':1,'backend_nice_increment':10,'backend_gallery':'new_Aug19',
 'RFID_condition':'SimulatednoRFIDresponseforallactualconfirmedhandoffcount_events;noRFIDhardwareclaim.',
 'background_trigger':'OnlyactualfrontendA->B/B->Aevents;currenttrackedboxcroppedfromsameframehighresolutioncamera-replayimage.',
 'high_resolution_camera_replay':{'source_crop_native_xyxy':[870,0,1920,1440],'JPEG_quality':95,'output_size_WH':[1050,1440],
  'slots':392,'reencode_lossy':True,'network_resize':False,'actual_camera_connected':False,
  'no_preselected_cow_box':'StorephysicalROIonly;actualruntimeboxselectsthephotocrop.'},
 'prewarm_tracker_history':'ReplaypreviousactualO8raw0..8910inclusiveinsideboardcounter;exactobservationsandbothlistschecked;noneofthosecachedoutputsusedfor392timedslotinference.',
 'frontend_fast_entry':'ExistingO8run_imageBGRentry;all256inputquantcodesand8boardanchorrawexactrequired;noFP32runtimehashinsidetimedslots.',
 'expected_no_skip_count_control':11,'manual_confirmed_total':12,'same_clip_used_for_development':True,
 'no_camera_pipeline_latency_claim':True,'no_real_RF_readfailure_claim':True,'no_verified_permanent_ID_labels':True,
 'all_inputs_frozen_before_run_and_checked_before_timer':True,'global_O8_assets_modified':False,'new_training_updates':0,'whole_goal_complete':False}
(ROOT/'protocol/workload_v1.json').write_text(json.dumps(p,indent=2)+'\n')
(ROOT/'计划与验收.md').write_text('''# PYNQ同板前后台5Hz周期回放

先保留前一阶段真实O8计数11和118帧超过200ms的结果，再测试固定周期。公开视频的392个通行时刻每200ms释放一次，独立记录跳帧、释放至计数截止时间和计数事件。对照条件为前台独占与前台＋实际身份网络后台，不改模型、门限或计数规则。

输入以无损192帧已就绪控制模拟摄像头低分辨率输出；前台用既有O8原生BGR入口。完整0–8910跟踪历史由已实测raw在板上重放并精确回归，不计入通行区间5Hz吞吐，之后每一处理时刻均执行真实FPGA／ARM模型。

后台只由当次前台实际计数事件触发，RFID条件固定为全部未应答的模拟压力条件。公开源同时保存原生1050×1440物理通道JPEG95作为高分辨率相机回放；运行时用当次框抓拍和旋转，然后在同一板上完成Pillow预处理、224身份网络、跨日期图库检索与拒识。记录原始照片、实际张量、特征、队列等待和CPU竞争。该输入安排不等于接入真实摄像头或RFID传感器。

全部256种像素的整数输入码与8实际向量须通过原生BGR入口精确比较后才计时。身份网络须先完成ARM132图一致性门禁。两个条件都保留，包括任何跳帧、迟到或身份拒识；不按更好结果替换前次证据。

最终科研仍需原片人工12头对应的独立逐事件标注、独立来源和同通道双向数据；临时track ID和无身份标签的真实查询不能当作永久身份找回真值。
''',encoding='utf-8')
print(json.dumps({'phase':str(ROOT),'slots':392,'period_ms':200,'planned_cases':2,'simulated_camera_and_RFID_explicit':True}))
