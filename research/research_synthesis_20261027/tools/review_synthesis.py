"""Check report links, captured author blobs, frame arithmetic and QAT status.

This bounded check supports, and does not replace, scientific/manual review.
"""
from pathlib import Path
from datetime import datetime, timezone
import argparse, hashlib, json, re
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    name = Path(args.output)
    assert name.name == args.output and name.suffix == '.json'
    target = ROOT / 'results' / name
    assert not target.exists()
    documents = [PROJECT / '研究总览_从想法到论文.md', ROOT / '文献补充与主张边界.md', ROOT / 'Review与当前状态.md',
                 PROJECT / 'paper_readiness_20261030/计划与范围.md',
                 PROJECT / 'paper_readiness_20261030/论文主张与证据对应.md',
                 PROJECT / 'paper_readiness_20261030/论文方法与实验草稿.md',
                 PROJECT / 'paper_readiness_20261030/文献对照_原始来源.md',
                 PROJECT / 'paper_readiness_20261030/Review与当前状态.md',
                 PROJECT / 'independent_source_recheck_20261030/计划与准入.md',
                 PROJECT / 'independent_source_recheck_20261030/原始来源检索.md',
                 PROJECT / 'independent_source_recheck_20261030/BECA身份数据准入与冲突核查.md',
                 PROJECT / 'independent_source_recheck_20261030/Review与当前状态.md',
                 PROJECT / 'beca_fixed_transfer_20261030/计划与验收.md',
                 PROJECT / 'beca_fixed_transfer_20261030/固定模型外来源结果与阈值失配.md',
                 PROJECT / 'beca_fixed_transfer_20261030/Review与当前状态.md',
                 PROJECT / 'beca_score_diagnosis_20261031/计划与范围.md',
                 PROJECT / 'beca_score_diagnosis_20261031/单阈值能解决多少问题.md',
                 PROJECT / 'beca_score_diagnosis_20261031/Review与当前状态.md',
                 PROJECT / 'paper_readiness_20261030/论文主张与证据对应_v2.md',
                 PROJECT / 'paper_readiness_20261030/论文方法与实验草稿_v2.md',
                 PROJECT / 'paper_readiness_20261030/Review与当前状态_v2.md',
                 PROJECT / 'identity_trigger_pair_20261030/实际计数触发四轮恢复结果与时序取舍.md',
                 PROJECT / 'identity_trigger_pair_20261030/Review与恢复后当前状态.md',
                 PROJECT / 'pynq_access_resume_20261031/USB与网络恢复记录.md',
                 PROJECT / 'paper_readiness_20261030/论文主张与证据对应_v3.md',
                 PROJECT / 'paper_readiness_20261030/论文方法与实验草稿_v3.md',
                 PROJECT / 'paper_readiness_20261030/Review与当前状态_v3.md',
                 PROJECT / 'paper_readiness_20261030/论文补充_板上负载退化与启动失败_20261031.md',
                 PROJECT / 'pynq_workload_ablation_20261031/计划与验收.md',
                 PROJECT / 'pynq_workload_ablation_20261031/高分输入与身份负载_五轮结果和启动超时.md',
                 PROJECT / 'pynq_workload_ablation_20261031/Review与当前状态.md',
                 PROJECT / 'pynq_startup_probe_20261031/计划与验收.md',
                 PROJECT / 'pynq_startup_probe_20261031/后台导入与启动内存_四次测量.md',
                 PROJECT / 'pynq_startup_probe_20261031/Review与当前状态.md',
                 PROJECT / 'pynq_parent_only_workload_20261031/计划与验收.md',
                 PROJECT / 'pynq_parent_only_workload_20261031/精简后台导入_八轮负载与剩余问题.md',
                 PROJECT / 'pynq_parent_only_workload_20261031/Review与当前状态.md',
                 PROJECT / 'paper_readiness_20261030/论文补充_启动开销与完整八轮_20261031.md',
                 PROJECT / '研究进度.md', PROJECT / 'phase3_diagnosis_20261026/方案与执行状态.md',
                 PROJECT / 'cows2021_labels_20261027/原始标注准入与来源恢复.md',
                 PROJECT / 'cows2021_labels_20261027/Review与复现状态.md',
                 PROJECT / 'cows2021_adaptation_20261027/图像准入与后续训练.md',
                 PROJECT / 'cows2021_adaptation_20261027/官方归档与作者权重核查.md',
                 PROJECT / 'cows2021_adaptation_20261027/Review与当前状态.md',
                 PROJECT / 'orientation_validation_20261027/固定模型朝向对照与下一步.md',
                 PROJECT / 'orientation_validation_20261027/Review与当前状态.md',
                 PROJECT / 'orientation_video_20261027/视频输入旋转配对与结论.md',
                 PROJECT / 'orientation_video_20261027/Review与当前状态.md',
                 PROJECT / 'qat_study_20261026/QAT导出检查与后续训练.md',
                 PROJECT / 'qat_study_20261026/Review与复现状态.md',
                 PROJECT / 'integer_reference_20261028/整数卷积参考与导出边界.md',
                 PROJECT / 'integer_reference_20261028/Review与当前状态.md',
                 PROJECT / 'integer_reference_20261028/图优化残差加法定位与下一步.md',
                 PROJECT / 'integer_reference_20261028/图优化Review.md',
                 PROJECT / 'integer_trainable_20261028/三seed可训练整数前向与准入结果.md',
                 PROJECT / 'integer_trainable_20261028/Review与当前状态.md',
                 PROJECT / 'integer_qat_20261028/六轮配对QAT与身份验证结果.md',
                 PROJECT / 'integer_qat_20261028/Review与当前状态.md',
                 PROJECT / 'identity_risk_diagnosis_20261028/身份错配拒识与下一步.md',
                 PROJECT / 'identity_risk_diagnosis_20261028/公开计数候选入口复查.md',
                 PROJECT / 'identity_risk_diagnosis_20261028/Review与当前状态.md',
                 PROJECT / 'activation_range_20261028/量化范围与截断对照.md',
                 PROJECT / 'activation_range_20261028/Review与当前状态.md',
                 PROJECT / 'evaluation_intake_20261028/README.md',
                 PROJECT / 'evaluation_intake_20261028/Review与当前状态.md',
                 PROJECT / 'counting_recovery_20261028/源片漏计优化与下一步.md',
                 PROJECT / 'counting_recovery_20261028/Review与当前状态.md',
                 PROJECT / 'tracker_clock_20261028/计划与验收.md',
                 PROJECT / 'tracker_clock_20261028/跟踪时钟与稳定区间诊断.md',
                 PROJECT / 'tracker_clock_20261028/Review与当前状态.md',
                 PROJECT / 'confirmation_handoff_20261028/计划与验收.md',
                 PROJECT / 'confirmation_handoff_20261028/入口观察交接与配对结果.md',
                 PROJECT / 'confirmation_handoff_20261028/Review与当前状态.md',
                 PROJECT / 'paired_event_intake_20261028/评价入口与下一步.md',
                 PROJECT / 'paired_event_intake_20261028/B区中断与关联门槛.md',
                 PROJECT / 'paired_event_intake_20261028/Review与当前状态.md',
                 PROJECT / 'secondstage_iou_20261028/计划与验收.md',
                 PROJECT / 'secondstage_iou_20261028/第二阶段代价对照与结果.md',
                 PROJECT / 'secondstage_iou_20261028/Review与当前状态.md',
                 PROJECT / 'lost_recovery_20261028/计划与验收.md',
                 PROJECT / 'lost_recovery_20261028/Lost低分恢复与完整事件结果.md',
                 PROJECT / 'lost_recovery_20261028/Review与当前状态.md',
                 PROJECT / 'external_method_regression_20261028/计划与验收.md',
                 PROJECT / 'external_method_regression_20261028/外部方法回归与结果.md',
                 PROJECT / 'external_method_regression_20261028/Review与当前状态.md',
                 PROJECT / 'duplicate_track_audit_20261028/计划与验收.md',
                 PROJECT / 'duplicate_track_audit_20261028/双ID冗余审计与研究决策.md',
                 PROJECT / 'duplicate_track_audit_20261028/Review与当前状态.md',
                 PROJECT / 'mootrack_alignment_20261028/计划与验收.md',
                 PROJECT / 'mootrack_alignment_20261028/MooTrack原片对齐核查与准入决策.md',
                 PROJECT / 'mootrack_alignment_20261028/Review与当前状态.md',
                 PROJECT / 'mootrack_continuous_20261028/分支归档说明.md',
                 PROJECT / 'human_count_confirmation_20261028/人工确认12头与后续数据路线.md',
                 PROJECT / 'human_count_confirmation_20261028/Review与当前状态.md',
                 PROJECT / 'overhead_session_validation_20261028/计划与验收.md',
                 PROJECT / 'overhead_session_validation_20261028/普通俯视新视频回放与研究决策.md',
                 PROJECT / 'overhead_session_validation_20261028/Review与当前状态.md',
                 PROJECT / 'overhead_long_session_20261028/计划与验收.md',
                 PROJECT / 'overhead_long_session_20261028/普通俯视长视频筛选与下一步.md',
                 PROJECT / 'overhead_long_session_20261028/Review与当前状态.md',
                 PROJECT / 'overhead_positive_reference_20261028/计划与验收.md',
                 PROJECT / 'overhead_positive_reference_20261028/新长片通行参考草案与下一步.md',
                 PROJECT / 'overhead_positive_reference_20261028/逐事件草案复核入口.md',
                 PROJECT / 'overhead_positive_reference_20261028/Review与当前状态.md',
                 PROJECT / 'event_timing_refinement_20261029/计划与验收.md',
                 PROJECT / 'event_timing_refinement_20261029/完成时间细化与复核重点.md',
                 PROJECT / 'event_timing_refinement_20261029/Review与当前状态.md',
                 PROJECT / 'long_video_fixed_replay_20261029/计划与验收.md',
                 PROJECT / 'long_video_fixed_replay_20261029/普通俯视长片四模型回放与研究决策.md',
                 PROJECT / 'long_video_fixed_replay_20261029/Review与当前状态.md',
                 PROJECT / 'long_video_track_gap_20261029/计划与验收.md',
                 PROJECT / 'long_video_track_gap_20261029/新片轨迹分段定位与单因素对照.md',
                 PROJECT / 'long_video_track_gap_20261029/Review与当前状态.md',
                 PROJECT / 'firststage_iou_regression_20261029/计划与验收.md',
                 PROJECT / 'firststage_iou_regression_20261029/多seed与反向回归结果及采用决策.md',
                 PROJECT / 'firststage_iou_regression_20261029/Review与当前状态.md',
                 PROJECT / 'confirmed12_capture_identity_20261029/计划与验收.md',
                 PROJECT / 'confirmed12_capture_identity_20261029/12事件原图抓拍与身份查询结果.md',
                 PROJECT / 'confirmed12_capture_identity_20261029/Review与当前状态.md',
                 PROJECT / 'confirmed12_rf_stream_20261029/计划与验收.md',
                 PROJECT / 'confirmed12_rf_stream_20261029/12事件流式读码与真实查询异常验证.md',
                 PROJECT / 'confirmed12_rf_stream_20261029/Review与当前状态.md',
                 PROJECT / 'identity_source_provenance_20261029/计划与验收.md',
                 PROJECT / 'identity_source_provenance_20261029/原视频身份来源核查与评价准入.md',
                 PROJECT / 'identity_source_provenance_20261029/Review与当前状态.md',
                 PROJECT / 'crossdate_gallery_20261029/计划与验收.md',
                 PROJECT / 'crossdate_gallery_20261029/跨日期图库与真实抓拍身份结果.md',
                 PROJECT / 'crossdate_gallery_20261029/Review与当前状态.md',
                 PROJECT / 'crop_domain_20261029/计划与验收.md',
                 PROJECT / 'crop_domain_20261029/裁剪域验证与采用决策.md',
                 PROJECT / 'crop_domain_20261029/Review与当前状态.md',
                 PROJECT / 'detector_torso_pairs_20261029/计划与验收.md',
                 PROJECT / 'detector_torso_pairs_20261029/检测框躯干配对与尺度诊断.md',
                 PROJECT / 'detector_torso_pairs_20261029/Review与当前状态.md',
                 PROJECT / 'detector_factorial_20261029/计划与验收.md',
                 PROJECT / 'pynq_lowres_20261029/计划与当前状态.md',
                 PROJECT / 'pynq_lowres_20261029/PYNQ低分辨率部署与连接核查.md',
                 PROJECT / 'lowres_baseline_20261029/计划与验收.md',
                 PROJECT / 'lowres_baseline_20261029/低分辨率基线与5Hz计数结果.md',
                 PROJECT / 'lowres_baseline_20261029/Review与当前状态.md',
                 PROJECT / 'lowres_roi_20261029/计划与验收.md',
                 PROJECT / 'lowres_roi_20261029/固定通道裁剪与低分辨率结果.md',
                 PROJECT / 'lowres_roi_20261029/Review与当前状态.md',
                 PROJECT / 'pynq_board_validation_20261029/计划与验收.md',
                 PROJECT / 'pynq_board_validation_20261029/PYNQ实机三尺寸结果与下一步.md',
                 PROJECT / 'pynq_board_validation_20261029/Review与当前状态.md',
                 PROJECT / 'pynq_cow_compile_20261029/计划与验收.md',
                 PROJECT / 'pynq_cow_compile_20261029/奶牛单类权重O8实机准入.md',
                 PROJECT / 'pynq_cow_compile_20261029/Review与当前状态.md',
                 PROJECT / 'detector_factorial_20261029/低分辨率训练对照与采用决定.md',
                 PROJECT / 'detector_factorial_20261029/Review与当前状态.md',
                 PROJECT / 'lowres_event_audit_20261029/计划与验收.md',
                 PROJECT / 'lowres_event_audit_20261029/低分辨率漏计分解与下一步.md',
                 PROJECT / 'lowres_event_audit_20261029/Review与当前状态.md',
                 PROJECT / 'factorial_lane_crop_20261029/计划与验收.md',
                 PROJECT / 'factorial_lane_crop_20261029/固定裁剪结果与部署下一步.md',
                 PROJECT / 'factorial_lane_crop_20261029/Review与当前状态.md',
                 PROJECT / 'pynq_rot192_compile_20261029/计划与验收.md',
                 PROJECT / 'pynq_rot192_compile_20261029/新192模型O8实机准入.md',
                 PROJECT / 'pynq_rot192_compile_20261029/Review与当前状态.md',
                 PROJECT / 'pynq_frontend_port_20261029/NumPy跟踪移植与实机回归.md',
                 PROJECT / 'pynq_rot192_eval_20261029/计划与验收.md',
                 PROJECT / 'pynq_rot192_eval_20261029/新192量化与PYNQ视频计数结果.md',
                 PROJECT / 'pynq_rot192_eval_20261029/Review与当前状态.md',
                 PROJECT / 'pynq_periodic_joint_20261030/计划与验收.md',
                 PROJECT / 'pynq_identity_ncnn_20261029/部署依据与计划.md',
                 PROJECT / '研究阶段总结_20261030.md',
                 PROJECT / 'pynq_identity_ncnn_20261029/身份编码器ARM实机部署与一致性.md',
                 PROJECT / 'pynq_identity_ncnn_20261029/Review与当前状态.md',
                 PROJECT / 'pynq_periodic_joint_20261030/同板前后台周期实测与下一步.md',
                 PROJECT / 'pynq_periodic_joint_20261030/Review与当前状态.md',
                 PROJECT / 'pynq_idle_control_20261030/计划与验收.md',
                 PROJECT / 'pynq_idle_control_20261030/空闲后台调度结果与等待代价.md',
                 PROJECT / 'pynq_idle_control_20261030/Review与当前状态.md',
                 PROJECT / 'pynq_capture_encoding_20261030/计划与验收.md',
                 PROJECT / 'pynq_capture_encoding_20261030/抓拍无损编码与完整同板结果.md',
                 PROJECT / 'pynq_capture_encoding_20261030/Review与当前状态.md',
                 PROJECT / 'rot192_event_diagnosis_20261030/计划与验收.md',
                 PROJECT / 'rot192_event_diagnosis_20261030/固定192剩余未计案例与训练方向.md',
                 PROJECT / 'rot192_event_diagnosis_20261030/Review与当前状态.md',
                 PROJECT / 'pynq_o8_sizes_20261030/计划与验收.md',
                 PROJECT / 'pynq_o8_sizes_20261030/同O8三尺寸实机与320数值口径.md',
                 PROJECT / 'pynq_o8_sizes_20261030/Review与当前状态.md',
                 PROJECT / 'photometric_input_20261030/计划与验收.md',
                 PROJECT / 'photometric_input_20261030/输入亮度对照结果与训练决策.md',
                 PROJECT / 'photometric_input_20261030/Review与当前状态.md',
                 PROJECT / 'training_coverage_20261030/计划与验收.md',
                 PROJECT / 'training_coverage_20261030/训练覆盖审计与下一组对照.md',
                 PROJECT / 'training_coverage_20261030/Review与当前状态.md',
                 PROJECT / 'mosaic_pair_20261030/计划与验收.md',
                 PROJECT / 'mosaic_pair_20261030/配对训练结果与量化候选.md',
                 PROJECT / 'mosaic_pair_20261030/Review与当前状态.md',
                 PROJECT / 'pynq_mosaic192_compile_20261030/计划与验收.md',
                 PROJECT / 'pynq_mosaic192_compile_20261030/新主候选量化与O8实机准入.md',
                 PROJECT / 'pynq_mosaic192_compile_20261030/Review与当前状态.md',
                 PROJECT / 'pynq_mosaic192_eval_20261030/计划与验收.md',
                 PROJECT / 'pynq_mosaic192_eval_20261030/新候选量化与真实视频结果.md',
                 PROJECT / 'pynq_mosaic192_eval_20261030/Review与当前状态.md',
                 PROJECT / 'pynq_mosaic192_joint_20261030/计划与验收.md',
                 PROJECT / 'pynq_mosaic192_joint_20261030/新候选同板周期与两轮复测.md',
                 PROJECT / 'pynq_mosaic192_joint_20261030/Review与当前状态.md',
                 PROJECT / 'mosaic_event_diagnosis_20261030/计划与验收.md',
                 PROJECT / 'mosaic_event_diagnosis_20261030/新旧O8计数差异与确认瓶颈.md',
                 PROJECT / 'mosaic_event_diagnosis_20261030/Review与当前状态.md',
                 PROJECT / 'unconfirmed_iou_20261030/计划与验收.md',
                 PROJECT / 'unconfirmed_iou_20261030/未确认关联控制与不采用决定.md',
                 PROJECT / 'unconfirmed_iou_20261030/Review与当前状态.md',
                 PROJECT / 'causal_photo_20261030/计划与验收.md',
                 PROJECT / 'causal_photo_20261030/补充计时口径.md',
                 PROJECT / 'causal_photo_20261030/实现边界与事后核对.md',
                 PROJECT / 'causal_photo_20261030/因果抓拍实机结果与不采用决定.md',
                 PROJECT / 'causal_photo_20261030/Review与当前状态.md',
                 PROJECT / 'input_cost_20261030/计划与验收.md',
                 PROJECT / 'input_cost_20261030/计量兼容修正_v2.md',
                 PROJECT / 'input_cost_20261030/高分输入取得成本与下一步.md',
                 PROJECT / 'input_cost_20261030/Review与当前状态.md',
                 PROJECT / 'async_highres_20261030/计划与验收.md',
                 PROJECT / 'async_highres_20261030/有界输入四次实机结果与下一步.md',
                 PROJECT / 'async_highres_20261030/Review与当前状态.md',
                 PROJECT / 'backend_service_20261030/计划与验收.md',
                 PROJECT / 'backend_service_20261030/串口恢复与数值复核说明.md',
                 PROJECT / 'backend_service_20261030/后台服务四次实机结果与取舍.md',
                 PROJECT / 'backend_service_20261030/Review与当前状态.md',
                 PROJECT / 'backend_service_20261030/完整归档恢复与复核补充_v2.md',
                 PROJECT / 'external_sources_20261030/计划与验收.md',
                 PROJECT / 'external_sources_20261030/公开俯视数据来源与准入结论.md',
                 PROJECT / 'colo_eval_20261030/计划与验收.md',
                 PROJECT / 'colo_eval_20261030/COLO三模型三尺寸外来源检测与下一步.md',
                 PROJECT / 'colo_error_diagnosis_20261030/计划与验收.md',
                 PROJECT / 'colo_error_diagnosis_20261030/检测对象与标注使用约定.md',
                 PROJECT / 'colo_error_diagnosis_20261030/低召回分解与检测对象约定.md',
                 PROJECT / 'cpu_partition_20261030/计划与验收.md',
                 PROJECT / 'cpu_partition_free_20261030/计划与验收.md',
                 PROJECT / 'cpu_partition_combined_20261030/固定照片负载八次实机与CPU分配取舍.md',
                 PROJECT / 'cows2021_identity_intake_20261030/计划与验收.md',
                 PROJECT / 'cows2021_identity_intake_20261030/身份来源核查与跨日期评价准入.md',
                 PROJECT / 'cows2021_identity_eval_20261030/计划与验收.md',
                 PROJECT / 'cows2021_identity_eval_20261030/跨日期身份检索与拒识结果.md',
                 PROJECT / 'cows2021_identity_gallery_control_20261030/计划与验收.md',
                 PROJECT / 'cows2021_identity_gallery_control_20261030/图库规模控制与拒识限制.md',
                 PROJECT / 'identity_domain_adapt_20261030/计划与验收.md',
                 PROJECT / 'identity_domain_adapt_20261030/身份域适配配对训练与开发结果.md',
                 PROJECT / 'identity_rejection_scores_20261030/计划与验收.md',
                 PROJECT / 'identity_rejection_scores_20261030/拒识分数对照与校准选择.md',
                 PROJECT / 'identity_domain_ncnn_20261030/计划与验收.md',
                 PROJECT / 'identity_domain_ncnn_20261030/新身份编码器NCNN转换与一致性验证.md',
                 PROJECT / 'identity_domain_arm_20261030/计划与验收.md',
                 PROJECT / 'identity_domain_arm_20261030/新身份候选ARM实机与研究决定.md',
                 PROJECT / 'identity_joint_pair_20261030/计划与验收.md',
                 PROJECT / 'identity_joint_pair_20261030/新旧身份模型固定负载同板对照.md',
                 PROJECT / 'identity_final20_20261030/计划与验收.md',
                 PROJECT / 'identity_final20_20261030/校准冻结结果与像素状态.md',
                 PROJECT / 'identity_final20_20261030/保留20身份结果与自动接受限制.md',
                 PROJECT / 'identity_final20_arm_20261030/计划与验收.md',
                 PROJECT / 'identity_final20_arm_20261030/同90图ARM实机一致性与计时范围.md',
                 PROJECT / 'identity_trigger_pair_20261030/计划与验收.md',
                 PROJECT / 'identity_trigger_pair_20261030/实际触发对照_部分观察与恢复.md']
    links = []
    for path in documents:
        content = path.read_text(encoding='utf-8')
        assert '\ufffd' not in content
        for match in re.finditer(r'\]\((?:<([^>]+)>|([^\s)]+))\)', content):
            url = match[1] or match[2]
            if re.match(r'^[A-Za-z]:[/\\]', url):
                decoded = unquote(url)
                line_link = re.match(r'^(.*):(\d+)$', decoded)
                local = Path(line_link[1] if line_link else decoded)
                assert local.exists(), f'Missing local link {local}'
                if line_link:
                    assert local.is_file() and 1 <= int(line_link[2]) <= len(local.read_text(encoding='utf-8').splitlines())
                links.append({'document': path.name, 'target': str(local)})
    captured = []
    for path in sorted((ROOT / 'evidence').glob('*README.md')):
        record = json.loads(path.with_name(path.name + '.record.json').read_text(encoding='utf-8'))
        data = path.read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest()
        assert blob == record['git_blob_sha']
        captured.append({'file': path.name, 'git_blob_sha': blob, 'sha256': sha(path)})
    assert len(captured) == 2
    frames = 10873 - 8912 + 1
    assert frames == 1962 and frames / 25 == 78.48
    qat_path = PROJECT / 'qat_study_20261026/results/independent_verification.json'
    qat = json.loads(qat_path.read_text(encoding='utf-8'))
    assert qat['formal_QAT_or_paired_training_updates'] == 0
    assert qat['remaining_original_tolerance_failures'] == 1
    assert qat['FPGA_execution_verified'] is False
    labels = json.loads((PROJECT / 'cows2021_labels_20261027/results/label_audit/summary.json').read_text(encoding='utf-8'))
    assert labels['total_published_images'] == 10402 and labels['total_published_annotations'] == 13165
    source_summary = PROJECT / 'cows2021_labels_20261027/results/source_recovery_summary.json'
    source_verified = PROJECT / 'cows2021_labels_20261027/results/source_recovery_independent_verification.json'
    full_source_rechecked = False
    date_counts = None
    if source_verified.exists():
        verification = json.loads(source_verified.read_text(encoding='utf-8'))
        source = json.loads(source_summary.read_text(encoding='utf-8'))
        folder = source_verified.parent
        assert verification['status'] == 'ALL_10402_XML_HASHES_FIELDS_AND_ROLE_OVERLAPS_INDEPENDENTLY_VERIFIED'
        assert verification['XML_count'] == source['complete_XML'] == 10402
        assert verification['source_summary_sha256'] == sha(source_summary)
        assert verification['source_metadata_sha256'] == sha(folder / 'source_metadata_all.json')
        date_check = json.loads((folder / 'date_roles_independent_verification.json').read_text(encoding='utf-8'))
        assert date_check['records'] == 10402 and date_check['date_or_original_name_crosses_roles'] is False
        assert date_check['manifest_sha256'] == sha(folder / 'date_roles_v1/manifest.json')
        assert date_check['image_bytes_or_final_independence_certified'] is False
        geometry = json.loads((folder / 'full_XML_JSON_geometry_comparison.json').read_text(encoding='utf-8'))
        assert geometry['one_to_one_matched_labels'] == 13165 and geometry['image_count_conflicts'] == []
        assert geometry['automatic_training_approval_or_label_repair'] is False
        full_source_rechecked = True
        date_counts = date_check['counts']
    confirmed_weight_files = None
    stage = PROJECT / 'cows2021_adaptation_20261027/results'
    if (stage / 'author_weight_HEAD_checks.json').exists():
        archive = json.loads((stage / 'archive_index_summary.json').read_text(encoding='utf-8'))
        weights = json.loads((stage / 'archive_weight_members.json').read_text(encoding='utf-8'))
        head = json.loads((stage / 'author_weight_HEAD_checks.json').read_text(encoding='utf-8'))
        assert archive['status'] == 'CENTRAL_DIRECTORY_ONLY_READ_ALL_SELECTED_MEMBERS_FOUND'
        assert archive['selected_images'] == 8380 and archive['member_payload_or_image_pixels_read'] is False
        assert all(r['start'] >= archive['directory_start'] and r['end'] < archive['archive_bytes']
                   for r in archive['range_requests'])
        assert head['weight_payload_downloaded_or_loaded'] is False
        assert weights['weight_payload_downloaded_or_loaded'] is False
        assert weights['weights_count'] == len(weights['members']) == len(head['checks']) == 2
        for member, observed in zip(weights['members'], head['checks']):
            assert observed['HTTP'] == 200 and observed['size_matches_archive_member'] is True
            assert observed['bytes'] == member['uncompressed_size']
            assert observed['url'] == 'https://data.bris.ac.uk/datasets/' + member['name']
            assert observed['weight_payload_read'] is False
        confirmed_weight_files = 2
    cows_study = None
    if (stage / 'independent_verification.json').exists():
        audit = json.loads((stage / 'independent_verification.json').read_text(encoding='utf-8'))
        assert audit['status'] == 'DATA_TRAINING_FREEZE_AND_SIX_EVENT_REPLAYS_INDEPENDENTLY_VERIFIED'
        assert audit['seeds'] == [26, 27, 28] and audit['epochs_each'] == 10
        assert audit['delivery_manifest_files'] == 249 and len(audit['checks']) == 6
        train = json.loads((stage / 'training/summary.json').read_text(encoding='utf-8'))
        assert train['status'] == 'ALL_THREE_COWS2021_SEEDS_10_EPOCHS_COMPLETE_FROZEN_BEFORE_VIDEO'
        assert train['freeze_sha256'] == sha(stage / 'training/all_checkpoints_frozen_before_video.json')
        assert train['protocol_sha256'] == audit['protocol_sha256']
        media = json.loads((stage / 'media_verification.json').read_text(encoding='utf-8'))
        assert media['browser_verified'] is True and len(media['media']) == 6
        assert all(r['strict_full_decode'] == 'PASS' and r['frames'] == 1962 and r['fps'] == 25 for r in media['media'])
        assert media['browser_evidence_sha256'] == sha(stage / 'browser_verification.json')
        assert media['browser_screenshot_sha256'] == sha(stage / 'browser_preview_source9420.png')
        source_checks = [r for r in audit['checks'] if r['scene'] == 'source']
        external_checks = [r for r in audit['checks'] if r['scene'] == 'Toros']
        assert [r['events'] for r in source_checks] == [0, 1, 0]
        assert all(r['TP'] == 0 and r['FP'] == 0 and r['FN'] == 6 for r in external_checks)
        assert audit['source_independent_accuracy_verified'] is False
        cows_study = {'training_seeds': [26, 27, 28], 'epochs_each': 10,
                      'source_predictions': [r['events'] for r in source_checks],
                      'Toros_TP': [r['TP'] for r in external_checks],
                      'independent_event_replays': 6, 'files_verified': 249,
                      'media_strict_decode_and_browser_verified': True,
                      'source_independent_accuracy_verified': False,
                      'adopted_as_final_counting_improvement': False}
    orientation_study = None
    orientation = PROJECT / 'orientation_validation_20261027'
    if (orientation / 'results/independent_verification.json').exists():
        check = json.loads((orientation / 'results/independent_verification.json').read_text(encoding='utf-8'))
        assert check['status'] == 'ALL_ROTATION_GT_TRANSFORMS_AND_24_METRIC_CONDITIONS_INDEPENDENTLY_VERIFIED'
        assert check['input_images'] == 1571 and check['labelled_objects_per_condition'] == 1864
        assert len(check['metric_conditions']) == 24 and check['new_training_updates'] == 0
        assert check['maximum_independent_GT_transform_difference'] == 0
        assert check['source_Toros_or_candidate_final_evaluated'] is False
        assert check['source_video_count_failure_cause_proven'] is False
        figure = json.loads((orientation / 'results/figure_record_v2.json').read_text(encoding='utf-8'))
        source = orientation / 'delivery/results/control/summary.json'
        assert figure['source_summary_sha256'] == sha(source)
        summary = json.loads(source.read_text(encoding='utf-8'))
        assert summary['maximum_letterbox_pixel_rotation_difference'] == 0
        assert summary['new_training_updates'] == 0
        for row in figure['files']:
            p = orientation / 'figures_v2' / row['name']
            assert p.stat().st_size == row['bytes'] and sha(p) == row['sha256']
        orientation_study = {'validation_images': 1571, 'objects': 1864,
                             'frozen_seeds': [26, 27, 28], 'metric_conditions': 24,
                             'paired_recall_drop_percentage_points': [
                                 -100 * r['paired_recall_difference_90_minus_original']
                                 for r in check['paired_date_cluster_comparisons']],
                             'source_video_failure_cause_proven': False,
                             'new_training_updates': 0}
    video_study = None
    video = PROJECT / 'orientation_video_20261027'
    if (video / 'results/independent_verification.json').exists():
        check = json.loads((video / 'results/independent_verification.json').read_text(encoding='utf-8'))
        assert check['status'] == 'INVERSE_COORDINATES_ORIGINAL_REGRESSIONS_AND_12_EVENT_REPLAYS_INDEPENDENTLY_VERIFIED'
        assert check['delivery_files_verified'] == 177 and len(check['conditions']) == 12
        assert check['pretracker_inverse_coordinate_rows_verified'] == 12542
        assert check['pretracker_hook_frames_verified'] == 15924
        assert check['all_original_event_and_track_regressions_passed'] == 6
        assert check['overlay_full_decodes'] == 18 and check['training_updates'] == 0
        assert check['protocol_sha256'] == sha(video / 'protocol/video_rotation_v1.json')
        assert check['new_independent_source_count_accuracy_verified'] is False
        assert check['final_test_or_Z2_joint_execution_verified'] is False
        summary_file = video / 'delivery/results/inference/summary.json'
        summary = json.loads(summary_file.read_text(encoding='utf-8'))
        assert summary['new_training_updates'] == 0 and len(summary['conditions']) == 6
        coverage = json.loads((video / 'results/output_coverage.json').read_text(encoding='utf-8'))
        assert coverage['source_inference_summary_sha256'] == sha(summary_file)
        assert coverage['coverage_is_output_not_detection_recall_or_event_accuracy'] is True
        assert coverage['source_independent_truth_received'] is False
        source_original = [r for r in coverage['records'] if r['scene'] == 'source' and r['orientation'] == 'original']
        source_rotated = [r for r in coverage['records'] if r['scene'] == 'source' and r['orientation'] == 'clockwise90']
        assert [r['seed'] for r in source_original] == [r['seed'] for r in source_rotated] == [26, 27, 28]
        assert [r['predicted_A_to_B'] for r in source_original] == [0, 1, 0]
        assert [r['predicted_A_to_B'] for r in source_rotated] == [8, 6, 8]
        assert all(r['sampled_frames_in_scored_scope'] == 392 and r['predicted_B_to_A'] == 0
                   for r in source_original + source_rotated)
        assert [r['pretracker_ROI_frames'] for r in source_original] == [91, 138, 108]
        assert [r['pretracker_ROI_frames'] for r in source_rotated] == [364, 348, 358]
        external = [r for r in coverage['records'] if r['scene'] == 'Toros']
        assert len(external) == 6 and all(r['known_diagnostic_TP_FP_FN'] == {'TP': 0, 'FP': 0, 'FN': 6} for r in external)
        assert all(r['pretracker_ROI_box_rows'] == 0 and r['sampled_frames_in_scored_scope'] == 479
                   for r in external if r['orientation'] == 'clockwise90')
        for row in summary['conditions']:
            assert row['Toros_event_metrics']['TP'] == 0 and row['Toros_event_metrics']['FN'] == 6
            assert len(row['scenes']) == 2
            if row['orientation'] == 'clockwise90':
                assert row['scenes'][1]['detector_pretracker_boxes'] == 0
        media = json.loads((video / 'results/media_verification.json').read_text(encoding='utf-8'))
        assert media['browser_verified'] is True and media['source_accuracy_verified'] is False
        assert len(media['media']) == len(media['reused_original_media']) == 6
        assert all(r['strict_full_decode'] == 'PASS' and r['frames'] == 1962 and r['duration_s'] == 78.48 for r in media['media'])
        assert media['browser_evidence_sha256'] == sha(video / 'results/browser_verification.json')
        assert media['browser_screenshot_sha256'] == sha(video / 'results/browser_source9420.png')
        page = PROJECT / 'phase3_diagnosis_20261026/annotation_workbench/video_rotation_preview.html'
        assert media['page_sha256'] == sha(page) == sha(video / 'templates/video_rotation_preview.html')
        assert media['data_sha256'] == sha(page.with_name('video_rotation_preview_data.json'))
        fix = json.loads((video / 'results/browser_jump_race_fix.json').read_text(encoding='utf-8'))
        assert fix['status'] == 'EDIT_PAUSE_VALUE_RETENTION_AND_BOTH_BOUNDARIES_BROWSER_RETEST_PASSED'
        assert fix['new_page_sha256'] == sha(page)
        assert fix['old_page_sha256'] == sha(video / 'results/video_rotation_preview_before_edit_pause.html')
        assert fix['experiment_predictions_or_counter_rules_changed'] is False
        video_study = {'frozen_seeds': [26, 27, 28], 'input_orientations': ['original', 'clockwise90'],
                       'source_predictions_original': [0, 1, 0], 'source_predictions_clockwise90': [8, 6, 8],
                       'source_scoped_sampled_frames': 392,
                       'Toros_all_six_conditions_TP_FP_FN': [0, 0, 6],
                       'independent_event_conditions': 12, 'original_exact_regressions': 6,
                       'inverse_coordinate_rows': 12542, 'pretracker_hook_frames': 15924,
                       'files_verified': 177, 'media_strict_decode_hashes_and_browser_verified': True,
                       'source_independent_accuracy_verified': False,
                       'new_training_updates': 0, 'Z2_execution_verified': False}
    integer_study = None
    integer = PROJECT / 'integer_reference_20261028'
    if (integer / 'results/local_delivery_verification.json').exists():
        local = json.loads((integer / 'results/local_delivery_verification.json').read_text(encoding='utf-8'))
        check_path = integer / 'delivery/results/independent_verification.json'
        check = json.loads(check_path.read_text(encoding='utf-8'))
        summary_path = integer / 'delivery/results/reference/summary.json'
        summary = json.loads(summary_path.read_text(encoding='utf-8'))
        assert local['manifest_files'] == 35 and local['local_metric_conditions'] == 16
        assert local['candidate_disabled_passes'] == summary['candidate_passed_vectors'] == 8
        assert local['candidate_default_passes'] == summary['candidate_default_passed_vectors'] == 6
        assert check['source_summary_sha256'] == sha(summary_path)
        assert check['candidate_sha256'] == summary['candidate_sha256'] == sha(integer / 'delivery/results/reference/integer_accumulator_candidate.onnx')
        assert check['protocol_sha256'] == sha(integer / 'protocol/integer_conv_v1.json')
        assert check['independent_integer_layer_cases'] == check['ORT_full_branch_exact_integer_cases'] == 416
        assert check['accumulator_elements_recomputed'] == 11325248
        assert check['equivalent_INT8_weight_elements'] == 912008
        assert check['original_failure_index3_retained'] is True
        assert check['new_gradient_or_all_seeds_verified'] is False
        assert check['identity_accuracy_or_FPGA_execution_verified'] is False
        assert summary['old_failure_reproduced_exactly'] is True and summary['old_failed_vectors'] == [3]
        assert summary['candidate_is_changed_numerical_contract'] is True
        assert summary['original_QDQ_gate_fixed'] is False
        assert summary['new_training_updates'] == 0 and summary['new_training_gradient_verified'] is False
        assert summary['new_image_reads'] == 0 and summary['identity_accuracy_evaluated'] is False
        assert summary['FPGA_executed'] is False
        failed_default = [r['vector'] for r in summary['candidate_vector_results']
                          if not r['default_optimisation']['original_embedding_tolerance_passed']]
        assert failed_default == [2, 5]
        assert local['candidate_different_from_old_QDQ_vectors'] == [3]
        integer_study = {'training_seed': 26, 'already_used_training_vectors': 8,
                         'old_QDQ_passes': 7, 'old_failure_index': 3,
                         'new_candidate_disabled_passes': 8, 'new_candidate_default_passes': 6,
                         'new_candidate_default_failures': [2, 5],
                         'independent_integer_layer_cases': 416, 'accumulator_elements': 11325248,
                         'INT8_weight_elements_represented_equivalently': 912008,
                         'max_disabled_embedding_error': local['candidate_disabled_maximum_error'],
                         'files_verified': 35, 'original_QDQ_gate_fixed': False,
                         'candidate_is_changed_numerical_contract': True,
                         'all_seeds_gradients_or_FPGA_verified': False, 'new_training_updates': 0}
    optimizer_study = None
    if (integer / 'results/optimizer_local_verification.json').exists():
        local = json.loads((integer / 'results/optimizer_local_verification.json').read_text(encoding='utf-8'))
        base = integer / 'optimizer_delivery/results'
        check = json.loads((base / 'optimizer_independent_verification.json').read_text(encoding='utf-8'))
        probe = json.loads((base / 'optimizer_probe/summary.json').read_text(encoding='utf-8'))
        isolation = json.loads((base / 'optimizer_isolation/summary.json').read_text(encoding='utf-8'))
        assert check['probe_summary_sha256'] == sha(base / 'optimizer_probe/summary.json')
        assert check['isolation_summary_sha256'] == sha(base / 'optimizer_isolation/summary.json')
        assert probe['protocol_sha256'] == sha(integer / 'protocol/optimizer_probe_v1.json')
        assert isolation['protocol_sha256'] == sha(integer / 'protocol/optimizer_isolation_v1.json')
        assert probe['prior_OFF_ALL_outputs_exactly_reproduced'] is True
        assert len(probe['serialized_ALL_replay_vectors']) == 8
        assert all(r['serialized_replay_exact_original_ALL'] for r in probe['serialized_ALL_replay_vectors'])
        assert probe['common_tensors_per_traced_vector'] == 530
        assert all(r['original_embedding_unchanged_after_trace_outputs'] and
                   r['serialized_ALL_embedding_unchanged_after_trace_outputs'] for r in probe['tracing_preservation_checks'])
        assert check['original_typed_common_tensor_rows'] == 1060 and check['metric_conditions'] == 48
        assert check['single_existing_node_changed'] is True and check['all_other_nodes_and_initializers_unchanged'] is True
        assert check['isolated_mismatch_vectors'] == isolation['isolated_mismatch_vectors'] == [2, 5, 7]
        assert check['vector7_local_difference_but_no_final_embedding_difference'] is True
        assert check['both_controlled_paths_exact_OFF_output'] is True
        assert isolation['target_node']['op_type'] == 'QLinearAdd' and isolation['target_node']['domain'] == 'com.microsoft'
        expected = {'OFF': 8, 'BASIC': 8, 'EXTENDED': 6, 'ALL': 6, 'patched': 8, 'ALL_disable_quant_qdq': 8}
        assert check['pass_counts'] == local['pass_counts'] == expected
        assert local['files'] == 43 and local['new_local_model_forward_performed'] is False
        assert check['new_training_updates'] == 0 and check['all_seeds_gradients_or_FPGA_verified'] is False
        optimizer_study = {'training_seed': 26, 'existing_training_inputs': 8,
                           'single_QLinearAdd_restoration_causal_control_passed': True,
                           'same_upstream_inputs_and_other_nodes_initializers_verified': True,
                           'serialized_graph_and_tracing_preservation_verified': True,
                           'condition_pass_counts': expected, 'local_operator_difference_vectors': [2, 5, 7],
                           'final_default_failure_vectors': [2, 5], 'metric_conditions': 48,
                           'files_verified': 43, 'all_seeds_gradients_or_FPGA_verified': False,
                           'new_training_updates': 0}
    trainable_study = None
    trainable = PROJECT / 'integer_trainable_20261028'
    if (trainable / 'results/local_verification.json').exists():
        local = json.loads((trainable / 'results/local_verification.json').read_text(encoding='utf-8'))
        check = json.loads((trainable / 'delivery/results/independent_verification.json').read_text(encoding='utf-8'))
        summary = trainable / 'delivery/results/smoke_v2/summary.json'
        smoke = json.loads(summary.read_text(encoding='utf-8'))
        assert smoke['status'] == 'ALL_THREE_TRAINABLE_INTEGER_SMOKE_GATES_PASS'
        assert check['source_summary_sha256'] == sha(summary)
        assert smoke['protocol_sha256'] == sha(trainable / 'protocol/trainable_integer_smoke_v1.json')
        assert local['files'] == 82 and local['local_forward_metric_conditions'] == 192
        assert local['packing_checks'] == 48 and check['runtime_metric_conditions'] == 144
        assert check['integer_accumulator_layer_cases'] == 2496 and check['accumulator_elements_recomputed'] == 67951488
        assert check['initial_outputs_unchanged_by_trainability_fix'] is True
        assert check['training_image_roles_and_hashes_verified'] is True
        assert smoke['actual_discarded_smoke_updates'] == 6 and smoke['formal_QAT_updates'] == 0
        assert all(r['discarded_smoke_updates'] == 2 and r['changed_parameter_tensors'] == 98 for r in smoke['seeds'])
        assert all(r['finite_gradient_tensors'] == 104 for seed in smoke['seeds'] for r in seed['updates'])
        initialization = json.loads((trainable / 'results/initialization_local_verification.json').read_text(encoding='utf-8'))
        assert initialization['source_sha256'] == sha(trainable / 'results/initialization_probe.json')
        assert initialization['quantized_weight_differences'] == 6 and initialization['layers_with_qparam_differences'] == 49
        trainable_study = {'seeds': [26, 27, 28], 'initial_and_postupdate_model_conditions': 6,
                           'local_forward_metric_conditions': 192, 'independent_integer_layers': 2496,
                           'independent_accumulator_elements': 67951488, 'actual_discarded_smoke_updates': 6,
                           'formal_QAT_updates_in_smoke_stage': 0, 'files_verified': 82,
                           'training_images_read': 216, 'validation_or_holdout_images_read': 0,
                           'CPU_GPU_fold_initialization_difference_retained': True,
                           'new_vs_prior_feature_max_difference': .02865108847618103,
                           'FPGA_execution_verified': False}
    paired_qat_study = None
    study = PROJECT / 'integer_qat_20261028'
    if (study / 'results/local_verification.json').exists():
        local = json.loads((study / 'results/local_verification.json').read_text(encoding='utf-8'))
        check = json.loads((study / 'delivery/results/independent_verification.json').read_text(encoding='utf-8'))
        summary_file = study / 'delivery/results/study/summary.json'
        summary = json.loads(summary_file.read_text(encoding='utf-8'))
        assert summary['status'] == 'TWELVE_CONDITIONS_PAIRED_INTEGER_QAT_DEVELOPMENT_COMPLETE'
        assert summary['protocol_sha256'] == sha(study / 'protocol/paired_integer_qat_v1.json')
        assert check['source_summary_sha256'] == sha(summary_file)
        assert summary['formal_QAT_updates'] == summary['paired_float_updates'] == 360
        assert summary['smoke_updates_carried_into_training'] == 0
        assert summary['freeze_sha256'] == sha(study / 'delivery/results/study/all_models_thresholds_frozen.json')
        assert local['files'] == 145 and len(local['validation_conditions']) == len(summary['conditions']) == 12
        assert all(r['matched_steps'] == 120 and r['all_augmented_input_tensor_hashes_identical'] and
                   r['initial_master_weights_and_biases_exactly_equal'] and r['fixed_qparams_unchanged'] for r in summary['paired_controls'])
        assert check['numeric_metric_conditions'] == 192 and check['actual_runtime_regression_forwards'] == 96
        assert check['training_image_access_count'] == 580 and check['validation_image_access_count'] == 80
        assert summary['old_evaluation_or_future_holdout_images_accessed'] == 0
        assert check['validation_calibration_and_scores_same_reused_queries'] is True
        by_condition = {name: [r for r in local['validation_conditions'] if r['condition'] == name]
                        for name in ['source_folded_fp32', 'initial_integer', 'paired_float_continuation', 'integer_forward_qat']}
        assert [r['C'] for r in by_condition['initial_integer']] == [2, 1, 3]
        assert [r['C'] for r in by_condition['integer_forward_qat']] == [10, 9, 7]
        assert [r['W'] for r in by_condition['integer_forward_qat']] == [1, 0, 1]
        assert [r['closed_top1'] for r in by_condition['integer_forward_qat']] == [24, 25, 16]
        assert [r['C'] for r in by_condition['paired_float_continuation']] == [18, 16, 15]
        assert all(r['unknown_false_accepts'] == 1 for r in by_condition['integer_forward_qat'])
        paired_qat_study = {'seeds': [26, 27, 28], 'epochs_per_branch': 6, 'updates_per_branch_seed': 120,
                            'formal_QAT_updates': 360, 'paired_float_updates': 360,
                            'all_paired_augmented_tensor_hashes_identical': True,
                            'initial_integer_C': [2, 1, 3], 'QAT_C': [10, 9, 7], 'QAT_W': [1, 0, 1],
                            'QAT_closed_top1': [24, 25, 16], 'paired_float_C': [18, 16, 15],
                            'known_query_count': 25, 'unknown_query_count': 30,
                            'same_reused_validation_queries_calibrate_and_score': True,
                            'files_verified': 145, 'independent_export_metric_conditions': 192,
                            'actual_ORT_regression_forwards': 96, 'final_model_adopted': False,
                            'FPGA_execution_verified': False}
    risk_study = None
    risk = PROJECT / 'identity_risk_diagnosis_20261028'
    if (risk / 'results/local_delivery_verification.json').exists():
        summary = json.loads((risk / 'results/summary.json').read_text(encoding='utf-8'))
        check = json.loads((risk / 'results/independent_verification.json').read_text(encoding='utf-8'))
        local = json.loads((risk / 'results/local_delivery_verification.json').read_text(encoding='utf-8'))
        coverage = json.loads((risk / 'results/matched_coverage.json').read_text(encoding='utf-8'))
        protocol = json.loads((risk / 'protocol/frozen_risk_v1.json').read_text(encoding='utf-8'))
        for row in protocol['input_files']:
            path = Path(row['path'])
            assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
        assert summary['protocol_sha256'] == sha(risk / 'protocol/frozen_risk_v1.json')
        assert check['source_summary_sha256'] == sha(risk / 'results/summary.json')
        assert check['query_condition_rows'] == 660 and check['identity_condition_rows'] == 132
        assert check['independent_fsum_dotproducts'] == 16500 and check['counterfactual_operating_points'] == 3
        assert check['new_inference_training_or_adopted_thresholds'] is False
        QAT = [r for r in summary['conditions'] if r['condition'] == 'integer_forward_qat']
        assert [r['U_rank_correct'] for r in QAT] == [14, 16, 9]
        assert [r['U_rank_wrong'] for r in QAT] == [0, 0, 8]
        assert [r['unknown_false_accepts'] for r in coverage['results']] == [12, 7, 26]
        assert [r['W'] for r in coverage['results']] == [1, 0, 6]
        assert coverage['original_thresholds_or_predictions_modified'] is False
        assert local['files'] == 19 and local['manual_visual_QA'] == 'PASS'
        render = json.loads((risk / 'delivery/results/render_record.json').read_text(encoding='utf-8'))
        assert render['score_plot_query_condition_points'] == 330 and render['cases'] == 5 and render['image_panels'] == 12
        for row in render['files']:
            assert sha(risk / 'delivery' / row['path']) == row['sha256']
        risk_study = {'query_condition_rows': 660, 'identity_condition_groups': 132,
                      'independent_dotproducts': 16500, 'QAT_rank_correct_rejects': [14, 16, 9],
                      'QAT_rank_wrong_rejects': [0, 0, 8],
                      'matched_float_coverage_unknown_false_accepts_of30': [12, 7, 26],
                      'matched_float_coverage_known_wrong_accepts': [1, 0, 6],
                      'matched_coverage_is_label_using_diagnostic_not_adopted_threshold': True,
                      'frozen_thresholds_unchanged': True, 'new_inference_or_training': False,
                      'score_plot_points': 330, 'all_QAT_accepted_error_cases_visualized': 5,
                      'render_files_verified': 19, 'manual_visual_QA': 'PASS', 'FPGA_execution_verified': False}
    range_study = None
    ranges = PROJECT / 'activation_range_20261028'
    if (ranges / 'results/local_verification.json').exists():
        local = json.loads((ranges / 'results/local_verification.json').read_text(encoding='utf-8'))
        check = json.loads((ranges / 'delivery/results/independent_verification.json').read_text(encoding='utf-8'))
        summary_path = ranges / 'delivery/results/probe/summary.json'
        summary = json.loads(summary_path.read_text(encoding='utf-8'))
        assert summary['protocol_sha256'] == sha(ranges / 'protocol/activation_range_v1.json')
        assert check['source_summary_sha256'] == sha(summary_path)
        assert summary['source_training_images'] == check['source_training_image_hashes'] == 64
        assert len(summary['conditions']) == check['condition_view_metrics'] == 36
        assert summary['layer_condition_rows'] == 1872
        assert summary['model_condition_image_forwards'] == check['feature_condition_image_rows'] == 2304
        assert check['representative_integer_fixtures'] == 72 and check['fixture_accumulator_elements_recomputed'] == 5682432
        assert check['full_1872_layer_tensor_values_independently_replayed'] is False
        assert summary['actual_optimizer_updates'] == summary['validation_or_test_image_reads'] == 0
        assert summary['model_weights_and_qparams_unchanged'] is True
        assert summary['counterfactuals_are_not_valid_U8S8_models'] is True
        assert len(check['counterfactual_effects']) == 12 and all(r['mean_teacher_cosine_difference'] < 0 for r in check['counterfactual_effects'])
        assert local['files'] == 27 and local['feature_metric_conditions'] == 36
        assert local['maximum_local_MSE_reduction_difference'] <= 1e-15
        assert local['model_export_gate_tolerances_changed'] is False
        range_study = {'source_training_images': 64, 'views': 2, 'condition_view_metrics': 36,
                       'model_condition_image_forwards': 2304, 'layer_statistics_rows': 1872,
                       'representative_integer_fixtures': 72, 'independent_fixture_accumulator_elements': 5682432,
                       'all12_fixed_weight_unclipping_controls_lower_mean_teacher_cosine': True,
                       'controls_not_valid_U8S8_deployment_candidates': True,
                       'teacher_agreement_not_identity_accuracy': True,
                       'model_weights_qparams_and_thresholds_unchanged': True,
                       'new_training_updates': 0, 'validation_or_test_reads': 0,
                       'files_verified': 27, 'FPGA_execution_verified': False}
    intake_study = None
    intake = PROJECT / 'evaluation_intake_20261028'
    if (intake / 'results/preparation_verification.json').exists():
        prep = json.loads((intake / 'results/preparation_verification.json').read_text(encoding='utf-8'))
        catalog = json.loads((intake / 'results/frozen_prediction_catalog.json').read_text(encoding='utf-8'))
        browser = json.loads((intake / 'results/annotation_browser_retest.json').read_text(encoding='utf-8'))
        fix = json.loads((intake / 'results/annotation_jump_fix.json').read_text(encoding='utf-8'))
        audit = json.loads((intake / 'results/required_input_audit.json').read_text(encoding='utf-8'))
        assert prep['catalog_conditions'] == len(catalog['conditions']) == 17
        assert prep['browser_retest_cases'] == len(browser['tests']) == 9 and prep['intake_tests'] == 16
        assert browser['QA_draft_before'] == browser['QA_draft_after']
        assert browser['main_draft_opened_or_modified'] is False
        assert fix['browser_retest'] == 'PASS'
        assert fix['new_sha256'] == sha(PROJECT / 'phase3_diagnosis_20261026/annotation_workbench/index.html')
        assert fix['browser_evidence_sha256'] == sha(intake / 'results/annotation_browser_retest.json')
        assert fix['browser_screenshot_sha256'] == sha(intake / 'results/annotation_jump_fixed.png')
        assert len(audit['recurrence_evidence_from_three_preceding_goal_phase_audits']) == 3
        assert audit['not_a_wait_on_live_compute'] is True
        assert prep['new_reference_received'] is False and prep['FPGA_execution_verified'] is False
        intake_study = {'catalog_conditions': 17, 'browser_regressions': 9, 'intake_tests': 16,
                        'QA_draft_preserved_and_main_draft_not_operated': True,
                        'source_video_hash_reverified': True,
                        'known_QA_not_admitted_as_reference': True,
                        'current_compute_jobs_verified_terminal': True,
                        'independent_reference_JSON_or_board_parameters_received': False,
                        'same_external_input_gap_evidenced_by_three_prior_goal_audits': True,
                        'original_goal_complete': False}
    recovery_study = None
    recovery = PROJECT / 'counting_recovery_20261028'
    if (recovery / 'results/local_verification.json').exists():
        local = json.loads((recovery / 'results/local_verification.json').read_text(encoding='utf-8'))
        check = json.loads((recovery / 'delivery/results/independent_verification.json').read_text(encoding='utf-8'))
        media = json.loads((recovery / 'results/media_verification.json').read_text(encoding='utf-8'))
        browser = json.loads((recovery / 'results/browser_verification.json').read_text(encoding='utf-8'))
        first = recovery / 'delivery/results/replay_v2/summary.json'
        extension = recovery / 'delivery/results/full640_confirmation/summary.json'
        rows = json.loads(first.read_text(encoding='utf-8'))['conditions'] + json.loads(extension.read_text(encoding='utf-8'))['conditions']
        assert local['files'] == 191 and local['coordinate_rows_verified'] == check['coordinate_rows'] == 36669
        assert check['source_summary_sha256'] == sha(first) and check['extension_summary_sha256'] == sha(extension)
        assert check['protocol_sha256'] == sha(recovery / 'protocol/recovery_v2.json')
        assert check['baseline_exact_regressions'] == 1 and len(check['conditions']) == len(rows) == 10
        full = sorted((r for r in rows if r['arm']['name'] == 'full640_5hz'), key=lambda r:r['seed'])
        assert [r['seed'] for r in full] == [26,27,28] and [r['predicted_down'] for r in full] == [11,10,11]
        assert all(r['predicted_up'] == 0 for r in rows) and check['new_training_updates'] == 0
        assert media['browser_verified'] and len(media['media']) == 8 and media['browser_tests'] == 14
        assert browser['all_tests_passed'] and all(r['pass'] for r in browser['tests'])
        assert media['browser_evidence_sha256'] == sha(recovery / 'results/browser_verification.json')
        assert media['browser_screenshot_sha256'] == sha(recovery / 'results/browser_preview.png')
        assert media['independent_source_accuracy_verified'] is False and check['board_execution'] is False
        recovery_study = {'source_scope':[8912,10873], 'frozen_weights':3, 'development_conditions':10,
                          'full640_source_predictions':[11,10,11], 'previous_full320_predictions':[8,6,8],
                          'independent_event_replays':10, 'inverse_coordinate_rows':36669,
                          'files_verified':191, 'new_media':8, 'browser_tests':14,
                          'post_pilot_full640_confirmation_distinguished_from_preplanned_selection':True,
                          'new_training_updates':0,'source_independent_accuracy_verified':False,
                          'FPGA_execution_verified':False, 'whole_goal_complete':False}
    clock_study = None
    clock = PROJECT / 'tracker_clock_20261028'
    if (clock / 'results/final_review.json').exists():
        final = json.loads((clock / 'results/final_review.json').read_text(encoding='utf-8'))
        check = json.loads((clock / 'delivery/results/independent_verification.json').read_text(encoding='utf-8'))
        summary_file = clock / 'delivery/results/summary.json'
        summary = json.loads(summary_file.read_text(encoding='utf-8'))
        local = json.loads((clock / 'results/local_verification.json').read_text(encoding='utf-8'))
        probe = json.loads((clock / 'results/probe_local_verification.json').read_text(encoding='utf-8'))
        images = json.loads((clock / 'results/stability_case_record.json').read_text(encoding='utf-8'))
        assert final['clock_protocol_sha256'] == check['protocol_sha256'] == sha(clock / 'protocol/clock_v1.json')
        assert final['probe_protocol_sha256'] == sha(clock / 'protocol/case_probe_v1.json')
        assert check['summary_sha256'] == sha(summary_file) and len(summary['conditions']) == 7
        assert local['exact_replays'] == final['exact_cache_replays_before_controls'] == 5
        assert local['native_flow_rows'] == check['flow_rows_verified'] == 8705
        assert local['files'] == 46 and probe['files'] == 10 and final['delivery_files_verified'] == 56
        assert probe['counter_states_checked'] == 63 and len(probe['cases']) == 3
        assert all(c['event_times_and_directions_exact_without_ID'] and not c['events_exact_with_ID'] for c in check['comparisons'])
        assert [c['predicted_down'] for c in summary['conditions']] == [11,10,11,10,10,10,10]
        assert all(c['full_replay_exact'] for c in probe['cases'])
        assert images['visual_QA'] == 'PASS' and len(images['raw_frames']) == 9 and len(images['figures']) == 4
        for row in images['raw_frames'] + images['figures']:
            assert sha(clock / 'source_case' / row['file']) == row['sha256']
        assert final['candidate_confirmation_handoff_implemented'] is False
        assert final['independent_source_accuracy_verified'] is False and final['FPGA_execution_verified'] is False
        clock_study = {'five_cached_raw_to_track_replays_exact':True, 'fixed_buffer_controls':2,
                       'seven_event_conditions_verified':True,'native_track_rows':8705,
                       'ID_and_tracks_changed_but_event_times_directions_same':True,
                       'additional_instrumented_full_replays_exact':3,'counter_states_verified':63,
                       'delivery_files_verified':56,'native_frames':9,'visual_contact_sheets':4,
                       'entry_confirmation_and_separate_B_discontinuity_cases_located':True,
                       'candidate_confirmation_handoff_implemented':False,
                       'new_detector_forwards':0,'training_updates':0,
                       'source_independent_accuracy_verified':False,'FPGA_execution_verified':False,
                       'whole_goal_complete':False}
    handoff_study = None
    handoff = PROJECT / 'confirmation_handoff_20261028'
    if (handoff / 'results/final_review.json').exists():
        final = json.loads((handoff / 'results/final_review.json').read_text(encoding='utf-8'))
        check = json.loads((handoff / 'delivery/results/independent_verification.json').read_text(encoding='utf-8'))
        summary_file = handoff / 'delivery/results/replay_v2/summary.json'
        summary = json.loads(summary_file.read_text(encoding='utf-8'))
        media = json.loads((handoff / 'results/media_verification.json').read_text(encoding='utf-8'))
        browser = json.loads((handoff / 'results/browser_verification.json').read_text(encoding='utf-8'))
        assert final['protocol_sha256'] == check['protocol_sha256'] == sha(handoff / 'protocol/handoff_v1.json')
        assert final['module_sha256'] == check['module_sha256'] == sha(handoff / 'tools/confirmation_counter.py')
        assert check['source_summary_sha256'] == sha(summary_file)
        assert final['implementation_completed'] is True and final['behavior_tests'] == 14
        assert [r['baseline_down'] for r in summary['conditions']] == [11,10,11]
        assert [r['handoff_down'] for r in summary['conditions']] == [12,11,11]
        assert [len(r['added_events']) for r in summary['conditions']] == [1,1,0] and all(not r['removed_events'] for r in summary['conditions'])
        assert check['trace_frames'] == 6525 and check['tentative_observations'] == 127 and check['accepted_history'] == 41
        assert sum(r['independent_event_paths'] for r in check['checks']) == final['independent_event_paths'] == 9
        assert final['delivery_files'] == 64 and final['original_interface_failure_preserved']
        assert media['browser_verified'] and len(media['media']) == 6 and media['browser_tests'] == len(browser['tests']) == 13
        assert all(r['pass'] for r in browser['tests'])
        assert media['browser_evidence_sha256'] == sha(handoff / 'results/browser_verification.json')
        assert media['browser_screenshot_sha256'] == sha(handoff / 'results/browser_source9345_viewport.png')
        assert final['physical_duplicate_cow_events_independently_ruled_out'] is False
        assert final['independent_source_accuracy_verified'] is False and final['FPGA_execution_verified'] is False
        handoff_study = {'implementation_completed':True,'baseline_predictions':[11,10,11],
                         'handoff_predictions':[12,11,11],'added_events':[1,1,0],
                         'original_events_preserved':True,'behavior_tests':14,
                         'independent_event_paths':9,'trace_frames':6525,'admitted_history':41,
                         'delivery_files':64,'new_media':6,'browser_tests':13,
                         'windows_component_replay_exact':True,'same_three_sample_stability_rule':True,
                         'physical_duplicate_cow_events_independently_ruled_out':False,
                         'new_detector_forwards':0,'training_updates':0,
                         'source_independent_accuracy_verified':False,'FPGA_execution_verified':False,
                         'whole_goal_complete':False}
    paired_intake_study = None
    paired_intake = PROJECT / 'paired_event_intake_20261028'
    if (paired_intake / 'results/final_review.json').exists():
        final = json.loads((paired_intake / 'results/final_review.json').read_text(encoding='utf-8'))
        catalog = json.loads((paired_intake / 'results/frozen_prediction_catalog_v2.json').read_text(encoding='utf-8'))
        indexed = json.loads((paired_intake / 'results/catalog_verification.json').read_text(encoding='utf-8'))
        probe = json.loads((paired_intake / 'results/exit_probe_local_verification.json').read_text(encoding='utf-8'))
        tests = json.loads((paired_intake / 'results/all_test_results_delivery_final.json').read_text(encoding='utf-8'))
        cli = json.loads((paired_intake / 'results/cli_verification.json').read_text(encoding='utf-8'))
        assert final['catalog_sha256'] == indexed['catalog_sha256'] == sha(paired_intake / 'results/frozen_prediction_catalog_v2.json')
        previous = json.loads(Path(catalog['previous_catalog_path']).read_text(encoding='utf-8'))
        assert catalog['conditions'][:17] == previous['conditions'] and len(catalog['conditions']) == 23
        assert len(catalog['paired_comparisons']) == 3 and indexed['indexed_prediction_events'] == 139
        assert [r['predicted_events'] for r in catalog['conditions'][17:]] == [11,12,10,11,11,11]
        assert sum(r['tests'] for r in tests['suites']) == final['logic_tests'] == 28 and all(r['exit_code'] == 0 for r in tests['suites'])
        assert cli['checks'] == final['actual_CLI_checks'] == 3 and cli['score_output_created'] is False
        assert probe['protocol_sha256'] == final['exit_probe_protocol_sha256'] == sha(paired_intake / 'protocol/exit_probe_v1.json')
        assert final['evaluation_protocol_sha256'] == sha(paired_intake / 'protocol/evaluation_v1.json')
        assert probe['real_cost_entries_verified'] == 50 and probe['maximum_cost_or_IoU_difference'] < 1e-6
        assert probe['files'] == 9 and probe['trace_frames'] == 11 and probe['synthetic_cost_pairs'] == 25
        assert probe['source_full_original_replay_exact'] and probe['original_seed28_predictions'] == 11
        figures = json.loads((paired_intake / 'results/exit_case_figure_record.json').read_text(encoding='utf-8'))
        assert figures['visual_QA'] == 'PASS' and len(figures['source_files']) == 6 and len(figures['figures']) == 2
        for row in figures['source_files'] + figures['figures']:
            assert sha(paired_intake / 'figures' / row['path']) == row['sha256']
        assert final['association_cost_change_implemented'] is False and final['real_source_count_accuracy_calculated'] is False
        assert final['FPGA_execution_verified'] is False and final['current_source_predictions'] == [12,11,11]
        paired_intake_study = {'catalog_conditions':23,'preserved_historical_conditions':17,'current_pairs':3,
                               'logic_tests':28,'actual_CLI_checks':3,'new_reference_received':False,
                               'original_time_matching_rule_retained_with_ambiguity_reporting':True,
                               'directional_and_overall_scoring_pipeline_tested':True,
                               'B_probe_original_full_replay_exact':True,'B_probe_frames':11,
                               'real_association_cost_or_IoU_checks':50,'software_cost_grid_pairs':25,
                               'native_source_frames':6,'visual_contact_sheets':2,
                               'lost_eligibility_and_secondstage_cost_limits_separate':True,
                               'association_cost_change_implemented':False,
                               'current_source_predictions':[12,11,11],
                               'new_detector_forwards':0,'training_updates':0,
                               'source_count_accuracy_verified':False,'FPGA_execution_verified':False,
                               'whole_goal_complete':False}
    secondstage_study = None
    secondstage = PROJECT / 'secondstage_iou_20261028'
    if (secondstage / 'results/final_review.json').exists():
        final = json.loads((secondstage / 'results/final_review.json').read_text(encoding='utf-8'))
        check = json.loads((secondstage / 'results/local_verification.json').read_text(encoding='utf-8'))
        summary_file = secondstage / 'delivery/results/summary.json'
        summary = json.loads(summary_file.read_text(encoding='utf-8'))
        media = json.loads((secondstage / 'results/media_verification.json').read_text(encoding='utf-8'))
        browser = json.loads((secondstage / 'results/browser_verification.json').read_text(encoding='utf-8'))
        catalog = json.loads((secondstage / 'results/catalog_intake_verification.json').read_text(encoding='utf-8'))
        assert check['summary_sha256'] == sha(summary_file)
        assert check['protocol_sha256'] == final['protocol_sha256'] == sha(secondstage / 'protocol/secondstage_v1.json')
        assert check['candidate_module_sha256'] == final['candidate_module_sha256'] == sha(secondstage / 'tools/secondstage_tracker.py')
        assert len(summary['conditions']) == 6 and check['event_paths'] == 12 and check['trace_updates'] == 13050
        assert check['secondstage_nonempty_decisions'] == 1190 and check['secondstage_cost_entries'] == 1490
        assert check['maximum_cost_or_IoU_difference'] < 1e-6 and check['applied_low_stage_matches_all_history'] == 786
        assert all(r['event_times_and_directions_exact_without_ID'] and not r['full_event_records_exact'] for r in check['comparisons'])
        assert [r['predicted_down'] for r in summary['conditions'] if r['variant'] == 'secondstage_iou'] == [12,11,11]
        assert final['delivery_files_verified'] == 96 and final['candidate_behavior_passes'] == 9
        assert media['browser_verified'] and len(media['media']) == 6 and media['browser_tests'] == len(browser['tests']) == 12
        assert all(r['pass'] for r in browser['tests'])
        assert media['browser_evidence_sha256'] == sha(secondstage / 'results/browser_verification.json')
        assert media['browser_screenshot_sha256'] == sha(secondstage / 'results/browser_source9365.png')
        assert catalog['conditions'] == 26 and catalog['pairs'] == 6 and catalog['software_fixture_direction_rows'] == 52
        assert catalog['source_accuracy_computed'] is False and final['adopted_as_demonstrated_counting_improvement'] is False
        secondstage_study = {'single_score_fusion_block_removed':True,'firststage_and_lost_eligibility_unchanged':True,
                            'real_tracker_tests':9,'original_expected_failures':2,'six_replay_conditions':6,
                            'independent_counter_paths':12,'update_traces':13050,'cost_entries':1490,
                            'all_history_low_matches':786,'main_source_predictions':[12,11,11],
                            'event_times_and_directions_unchanged':True,'track_IDs_changed':True,
                            'delivery_files_verified':96,'new_media':6,'browser_tests':12,
                            'catalog_conditions':26,'catalog_pairs':6,
                            'source_count_accuracy_verified':False,'adopted_as_demonstrated_counting_improvement':False,
                            'new_detector_forwards':0,'training_updates':0,'FPGA_execution_verified':False,
                            'whole_goal_complete':False}
    lost_study = None
    lost = PROJECT / 'lost_recovery_20261028'
    if (lost / 'results/final_review.json').exists():
        final = json.loads((lost / 'results/final_review.json').read_text(encoding='utf-8'))
        check = json.loads((lost / 'results/local_verification.json').read_text(encoding='utf-8'))
        summary_file = lost / 'delivery/results/summary.json'
        summary = json.loads(summary_file.read_text(encoding='utf-8'))
        media = json.loads((lost / 'results/media_verification.json').read_text(encoding='utf-8'))
        browser = json.loads((lost / 'results/browser_verification.json').read_text(encoding='utf-8'))
        cases = json.loads((lost / 'results/ROI_recovery_case_states.json').read_text(encoding='utf-8'))
        catalog = json.loads((lost / 'results/catalog_intake_verification.json').read_text(encoding='utf-8'))
        assert check['summary_sha256'] == sha(summary_file)
        assert check['protocol_sha256'] == final['protocol_sha256'] == sha(lost / 'protocol/lost_v1.json')
        assert check['candidate_module_sha256'] == final['candidate_module_sha256'] == sha(lost / 'tools/lost_tracker.py')
        assert check['single_eligibility_expression_AST_change'] and len(summary['conditions']) == 6
        assert check['counter_paths'] == 12 and check['baseline_full_regressions'] == 3 and check['trace_updates'] == 13050
        assert check['cost_entries'] == 3411 and check['maximum_cost_difference'] < 1e-6
        assert check['all_lost_recoveries'] == 259 and check['lost_recoveries_in_scope'] == 33
        assert check['current_scope_actual_low_detection_in_ROI'] == 4
        assert [r['predicted_down'] for r in summary['conditions'] if r['variant'] == 'allow_lost_iou'] == [12,11,11]
        assert all(r['times_and_directions_exact'] and not r['full_event_records_exact'] for r in check['comparisons'])
        assert final['delivery_files_verified'] == 105 and final['candidate_passes'] == 12
        assert len(cases['cases']) == 4 and cases['candidate_component_replays_exact'] == 3
        figures = json.loads((lost / 'results/case_figure_record.json').read_text(encoding='utf-8'))
        assert figures['visual_QA'] == 'PASS' and len(figures['source_images']) == 12
        for row in figures['source_images'] + figures['figures']:
            assert sha(lost / 'case_figures' / row['file']) == row['sha256']
        assert media['browser_verified'] and len(media['media']) == 6 and media['browser_tests'] == len(browser['tests']) == 12
        assert all(t['pass'] for t in browser['tests'])
        assert media['browser_evidence_sha256'] == sha(lost / 'results/browser_verification.json')
        assert media['browser_screenshot_sha256'] == sha(lost / 'results/browser_source9365.png')
        assert catalog['conditions'] == 29 and catalog['pairs'] == 9 and catalog['software_fixture_direction_rows'] == 58
        assert catalog['source_accuracy_computed'] is False and final['adopted_as_demonstrated_counting_improvement'] is False
        lost_study = {'single_eligibility_expression_changed':True,'firststage_IoU_and_counter_unchanged':True,
                      'real_tracker_tests':12,'original_expected_failures':2,'paired_conditions':6,
                      'independent_counter_paths':12,'update_traces':13050,'cost_entries':3411,
                      'Lost_recoveries_all_history':259,'scope_whole_frame_recoveries':33,'scope_ROI_recoveries':4,
                      'all_four_ROI_cases_inspected':True,'main_source_predictions':[12,11,11],
                      'event_times_and_directions_unchanged':True,'track_IDs_changed':True,
                      'delivery_files_verified':105,'new_media':6,'browser_tests':12,
                      'catalog_conditions':29,'catalog_pairs':9,
                      'source_count_accuracy_verified':False,'adopted_as_demonstrated_counting_improvement':False,
                      'new_detector_forwards':0,'training_updates':0,'FPGA_execution_verified':False,
                      'next_priority':'Independent human event reference before more scene-specific optimization',
                      'whole_goal_complete':False}
    external_study = None
    external = PROJECT / 'external_method_regression_20261028'
    if (external / 'results/final_review.json').exists():
        final = json.loads((external / 'results/final_review.json').read_text(encoding='utf-8'))
        check = json.loads((external / 'results/local_verification.json').read_text(encoding='utf-8'))
        summary_file = external / 'delivery/results/summary.json'
        summary = json.loads(summary_file.read_text(encoding='utf-8'))
        cases = json.loads((external / 'results/case_local_verification.json').read_text(encoding='utf-8'))
        overlap = json.loads((external / 'results/overlap_case_review.json').read_text(encoding='utf-8'))
        assert final['protocol_sha256'] == check['protocol_sha256'] == sha(external / 'protocol/regression_v1.json')
        assert final['summary_sha256'] == check['summary_sha256'] == sha(summary_file)
        assert check['reference_rows'] == 1775 and check['reference_IDs'] == 9 and check['reference_events'] == 6
        assert check['tracker_runs'] == 6 and check['counter_paths'] == 12 and check['main_method_conditions'] == 8
        assert check['full_original_baseline_regressions'] == 2 and check['update_traces'] == 2874
        main = [r for r in summary['scores'] if r['main_method']]
        assert [r['metrics']['TP'] for r in main] == [6,6,6,6,2,2,2,3]
        assert all(r['metrics']['FP'] == 0 and r['metrics']['wrong_direction_matches'] == 0 for r in summary['scores'])
        assert overlap['frame'] == 120 and abs(overlap['predicted_box_pair_IoU'] - .8575113387044181) < 1e-12
        assert overlap['ID1_emitted_event_frames'] == [125] and overlap['ID8_emitted_event_frames'] == []
        assert cases['manual_visual_QA'] == 'PASS' and cases['images_full_decoded'] == 15
        assert cases['native_contact_images_viewed'] == 5 and cases['main_overlay_panels_viewed'] == 6
        for row in cases['figures']:
            assert sha(external / 'figures' / row['file']) == row['sha256']
        assert final['files_verified'] == 87 and final['old_pilot_adopted_as_final_model'] is False
        assert final['new_independent_test'] is False and final['Cows2021_three_weights_crossdomain_test_claimed'] is False
        external_study = {'already_used_external_reference_regression':True,'publisher_trajectory_rows':1775,
                          'derived_reference_events':6,'old_detector_caches':2,'tracker_runs':6,
                          'counter_paths_scored':12,'main_method_conditions':8,'independent_exhaustive_scores':12,
                          'official_main_TP':[6,6,6,6],'five_epoch_main_TP':[2,2,2,3],
                          'all_event_FP_and_wrong_direction_zero':True,'new_match_time_error_s':.5,
                          'overlapping_two_ID_case_retained':True,'overlapping_box_IoU':.8575113387044181,
                          'event_FP_zero_not_no_duplicate_track':True,'files_verified':87,
                          'image_files_decoded':15,'main_overlay_panels_viewed':6,
                          'old_pilot_final_adopted':False,'new_independent_test':False,
                          'Cows2021_three_weight_crossdomain_claim':False,'new_detector_forwards':0,
                          'training_updates':0,'FPGA_execution_verified':False,'whole_goal_complete':False}
    duplicate_study = None
    duplicate = PROJECT / 'duplicate_track_audit_20261028'
    if (duplicate / 'results/final_review.json').exists():
        final = json.loads((duplicate / 'results/final_review.json').read_text(encoding='utf-8'))
        audit = json.loads((duplicate / 'results/audit.json').read_text(encoding='utf-8'))
        check = json.loads((duplicate / 'results/independent_verification.json').read_text(encoding='utf-8'))
        render = json.loads((duplicate / 'results/render_v2_local_verification.json').read_text(encoding='utf-8'))
        assert final['protocol_sha256'] == check['protocol_sha256'] == audit['protocol_sha256'] == sha(duplicate / 'protocol/duplicate_v1.json')
        assert final['audit_sha256'] == check['audit_sha256'] == sha(duplicate / 'results/audit.json')
        assert check['condition_frames'] == 2874 and check['conditions'] == 6 and check['all_IoU_matrix_entries_recomputed'] == 88101
        assert check['maximum_pair_IoU_difference'] == 0 and check['high_overlap_pair_frames'] == 75 and check['episode_count'] == 48
        assert [r['frames_with_high_overlap_ID_pairs'] for r in audit['conditions']] == [1,2,2,22,22,23]
        assert [r['high_overlap_pair_frames'] for r in audit['conditions']] == [2,3,3,22,22,23]
        assert [r['GT_primary_supported_pair_frames'] for r in audit['conditions']] == [1,1,1,13,13,13]
        assert [r['GT_sensitivity_supported_pair_frames'] for r in audit['conditions']] == [1,1,1,22,22,23]
        assert [r['direct_raw_duplicate_pair_frames'] for r in audit['conditions']] == [0,0,0,9,9,10]
        known = audit['known_case_frame120']
        assert known['frame'] == 120 and known['track_IDs'] == [1,8] and known['direct_raw_duplicate_pair']
        assert abs(known['raw_link']['raw_pair_IoU'] - .8955011970160278) < 1e-12
        assert render['manual_visual_QA'] == 'PASS' and render['raster_full_decodes'] == 13 and render['files'] == 19
        assert render['representative_panels_visually_inspected'] == 6 and render['special_panels_visually_inspected'] == 2 and render['native_frames_visually_inspected'] == 4
        for row in render['visual_evidence_files']:
            assert sha(duplicate / 'render_v2_delivery/results/figures_v2' / row['file']) == row['sha256']
        assert final['physical_duplicate_rate_established'] is False and final['ID_merging_or_new_thresholds_implemented'] is False
        assert final['source_predictions_and_scores_changed'] is False and final['FPGA_execution_verified'] is False
        duplicate_study = {'six_frozen_output_audit_complete':True,'condition_frames':2874,
                           'candidate_pair_frames':75,'contiguous_episodes':48,'independent_matrix_elements':88101,
                           'candidate_frames_official':[1,2,2],'candidate_frames_five_epoch':[22,22,23],
                           'known_case_pair_already_in_raw_detections':True,'different_cows_high_overlap_counterexample_retained':True,
                           'physical_identity_not_inferred_from_IoU_alone':True,
                           'event_and_track_redundancy_metrics_separate':True,'original_scores_preserved':True,
                           'final_render_files_verified':19,'raster_full_decodes':13,
                           'native_frames_viewed':4,'representative_panels_viewed':6,'special_panels_viewed':2,
                           'physical_duplicate_rate_established':False,'ID_merge_or_threshold_change':False,
                           'new_independent_reference':False,'new_detector_forwards':0,'training_updates':0,
                           'FPGA_execution_verified':False,'whole_goal_complete':False}
    mootrack_study = None
    mootrack = PROJECT / 'mootrack_alignment_20261028'
    if (mootrack / 'results/final_review.json').exists():
        final = json.loads((mootrack / 'results/final_review.json').read_text(encoding='utf-8'))
        visual = json.loads((mootrack / 'evidence/visual_review.json').read_text(encoding='utf-8'))
        assert final['status'] == 'BOUNDED_NATIVE_SAMPLES_GT_SCALE_HYPOTHESIS_AND_ADMISSION_LIMITS_REVIEWED'
        assert final['range_bytes_checked'] == 44740482 and final['range_requests_checked'] == 7
        assert final['video_samples_reconstructed_and_decode_count_checked'] == 126 and final['native_frames_visually_inspected'] == 5
        assert final['GT_anchor_frames_visually_inspected'] == 4 and final['GT_anchor_boxes'] == 24
        assert final['GT_rows_independently_rechecked'] == 350272 and final['scale_hypothesis'] == 2.0
        assert final['author_text_files'] == 30 and final['Git_tree_objects_reconstructed_to_commit_tree'] == 183
        assert final['catalog_conditions_preserved'] == 29 and final['current_predicted_down'] == [12,11,11]
        assert visual['native_display_indices0_inspected'] == [0,8991,26973,53919,53945]
        for row in final['source_records']:
            assert sha(Path(row['path'])) == row['sha256']
        for row in final['images']:
            assert sha(Path(row['path'])) == row['sha256']
        assert final['whole_video_GT_alignment_certified'] is False and final['tail_truncation_proven'] is False
        assert final['new_independent_counting_reference_certified'] is False and final['FPGA_execution_verified'] is False
        assert final['whole_goal_complete'] is False
        mootrack_study = {'bounded_pixel_and_sample_table_audit_complete':True,'range_bytes':44740482,
                          'native_frames_visually_inspected':5,'GOP_sample_decode_checks':126,
                          'GT_spatial_scale_candidate':2.0,'annotated_visual_anchors':4,'published_GT_rows_checked':350272,
                          'author_text_blobs':30,'Git_tree_objects_reconstructed':183,
                          'source_predictions_preserved':[12,11,11],'source_catalog_conditions':29,
                          'new_independent_counting_reference_certified':False,'whole_video_GT_alignment_certified':False,
                          'tail_truncation_proven':False,'new_detector_forwards':0,'training_updates':0,
                          'FPGA_execution_verified':False,'whole_goal_complete':False}
    confirmed_total_study = None
    human_total = PROJECT / 'human_count_confirmation_20261028'
    if (human_total / 'results/final_review.json').exists():
        final = json.loads((human_total / 'results/final_review.json').read_text(encoding='utf-8'))
        reference = json.loads((human_total / 'evidence/user_confirmation.json').read_text(encoding='utf-8'))
        candidate = json.loads((human_total / 'results/frozen_development_candidate.json').read_text(encoding='utf-8'))
        assert final['status'] == 'HUMAN_TOTAL_12_ACCEPTED_DEVELOPMENT_CANDIDATE_AND_CAMERA_PIVOT_REVIEWED'
        assert final['reference_sha256'] == sha(human_total / 'evidence/user_confirmation.json')
        assert final['candidate_sha256'] == sha(human_total / 'results/frozen_development_candidate.json')
        assert final['comparison_sha256'] == sha(human_total / 'results/total_count_comparison.json')
        assert final['human_confirmed_total'] == reference['human_confirmed_total'] == 12
        assert final['human_total_reference_accepted'] is True and final['current_clip_total_goal_achieved'] is True
        assert final['actual_main_prediction_events_recounted'] == [12,11,11] and final['absolute_total_errors'] == [0,1,1]
        assert candidate['condition_id'] == 'confirmation_handoff_20261028/seed26'
        assert sha(Path(candidate['checkpoint_path'])) == candidate['checkpoint_sha256']
        assert final['per_event_F1_claimed'] is False and final['source_events_promoted_to_reference'] is False
        assert final['ordinary_overhead_video_priority'] is True and final['source_clip_remains_development_data'] is True
        assert final['FPGA_execution_verified'] is False and final['whole_goal_complete'] is False
        confirmed_total_study = {'human_total_reference_accepted':True,'human_confirmed_down':12,
                                 'development_clip_count_milestone_achieved':True,'main_predictions':[12,11,11],
                                 'absolute_total_errors':[0,1,1],'fixed_usable_candidate':'confirmation_handoff_20261028/seed26',
                                 'ordinary_directly_overhead_video_priority':True,'fisheye_branch_archived_after_user_steering':True,
                                 'historical_total_unconfirmed_records_superseded_for_current_state':True,
                                 'per_event_F1_claimed':False,'new_unseen_test_claimed':False,'new_training_updates':0,
                                 'FPGA_execution_verified':False,'whole_goal_complete':False}
    overhead_study = None
    overhead = PROJECT / 'overhead_session_validation_20261028'
    if (overhead / 'results/final_review.json').exists():
        final = json.loads((overhead / 'results/final_review.json').read_text(encoding='utf-8'))
        assert final['status'] == 'FOUR_ORDINARY_OVERHEAD_SESSIONS_EIGHT_FROZEN_CONDITIONS_AND_LIMITS_REVIEWED'
        assert final['source_directory_entries'] == 301 and final['eligible_sessions'] == 213 and final['selected_sessions'] == 4
        assert final['source_frames'] == 637 and final['source_video_bytes'] == 162888404
        assert final['model_conditions'] == final['independent_counter_paths'] == 8
        assert final['model_forward_calls'] == final['counter_ticks_recomputed'] == 216
        assert final['native_ROI_coordinates_recomputed'] == 83 and final['full_video_decode_files'] == 16
        assert final['full_video_decode_frames'] == 2548 and final['all_raster_files_decoded'] == 52
        assert final['official_raw_presence_frames'] == [7,6,0,5] and final['accepted_raw_presence_frames'] == [23,17,27,18]
        assert final['official_predicted_A_to_B'] == [0,0,0,0] and final['accepted_predicted_A_to_B'] == [0,0,1,0]
        assert final['current_source_human_confirmed_12_milestone_preserved'] is True and final['current_source_29_conditions_unchanged'] is True
        assert final['new_event_GT_available'] is False and final['new_count_accuracy_or_recall_F1_claimed'] is False
        assert final['reserved_final_date_opened'] is False and final['browser_playback_verified'] is False
        for path,digest in final['evidence_hashes'].items():
            assert sha(overhead / path) == digest
        for row in final['media'] + final['images']:
            assert sha(Path(row['path'])) == row['sha256']
        assert all(j['state']=='COMPLETED' and j['exit']=='0:0' for j in final['Slurm_jobs'])
        overhead_study = {'ordinary_overhead_sessions':4,'source_frames':637,'frozen_model_conditions':8,
                          'model_forwards':216,'counter_paths_independently_recomputed':8,
                          'ROI_coordinates_recomputed':83,'full_decode_media':16,'full_decode_frames':2548,
                          'native_and_prediction_visual_anchors':44,'accepted_source12_milestone_preserved':True,
                          'raw_output_presence_is_not_recall':True,'accepted_predicted_A_to_B':[0,0,1,0],
                          'new_event_GT_available':False,'new_accuracy_or_F1_claimed':False,
                          'reserved_final_date_opened':False,'browser_playback_verified':False,
                          'training_updates':0,'FPGA_execution_verified':False,'whole_goal_complete':False}
    long_overhead_study = None
    long_overhead = PROJECT / 'overhead_long_session_20261028'
    if (long_overhead / 'results/final_review.json').exists():
        final = json.loads((long_overhead / 'results/final_review.json').read_text(encoding='utf-8'))
        assert final['status'] == 'ORDINARY_LONG_VIDEO_NATIVE_ADMISSION_BACKGROUND_AND_POSITIVE_CANDIDATE_REVIEWED'
        assert final['first_source_frames_counted'] == final['packet_clock_entries_checked'] == 15756
        assert final['source_has_strict_decode_failure'] is True and final['strict_ffmpeg_exit_code'] == 183
        assert final['conservative_quarantine_frames0'] == [15705,15755] and final['first_source_full_zero_event_GT_established'] is False
        assert final['first_source_overview_images_viewed'] == 128 and final['review_video_frames_fully_decoded'] == 3152
        assert final['other_source_files_probed'] == 6 and final['native_probe_attempts'] == 18
        assert final['native_probe_images_viewed'] == 11 and final['failed_probes_retained'] == 7
        assert final['probe_HTTP_bytes_including_preserved_guard_attempt'] == 88080396 and final['all_raster_files_full_decoded'] == 174
        assert final['positive_candidate'] == '2023-08-17T13-25-38.mp4' and final['positive_candidate_source_bytes'] == 260358184
        assert final['positive_source_complete_byte_download_verified'] is True and final['positive_probe_ranges_match_complete_source_bytes'] is True
        assert final['positive_source_whole_decode_or_event_GT_verified'] is False and final['model_or_training_calls'] == 0
        assert final['current_human_confirmed_12_milestone_preserved'] is True and final['current_29_condition_catalog_unchanged'] is True
        for path,digest in final['evidence_hashes'].items():assert sha(long_overhead/path) == digest
        for row in final['images']:assert sha(Path(row['path'])) == row['sha256']
        assert sha(long_overhead/'input/2023-08-17T13-25-38.mp4') == final['positive_candidate_source_sha256']
        long_overhead_study = {'ordinary_overhead_long_source_frames':15756,'background_candidate_overview_samples':128,
                               'zero_event_truth_not_inferred_from_sampling':True,'strict_source_decode_failure_recorded':True,
                               'conservative_terminal_quarantine':[15705,15755],'remaining_files_probed':6,'native_probe_attempts':18,
                               'successful_native_probes_viewed':11,'positive_source':'2023-08-17T13-25-38.mp4',
                               'positive_source_full_bytes_obtained':260358184,'positive_source_whole_decode_and_GT_pending':True,
                               'current_confirmed12_preserved':True,'new_model_or_training_calls':0,
                               'new_accuracy_or_F1_claimed':False,'FPGA_execution_verified':False,'whole_goal_complete':False}
    positive_reference_study = None
    positive = PROJECT / 'overhead_positive_reference_20261028'
    if (positive / 'results/final_review_v3.json').exists():
        final = json.loads((positive / 'results/final_review_v3.json').read_text(encoding='utf-8'))
        draft = json.loads((positive / 'reference/assistant_event_draft_v1.json').read_text(encoding='utf-8'))
        assert final['status'] == 'NEW_LONG_SOURCE_ADMISSION_AND_FROZEN_ASSISTANT_EVENT_DRAFT_REVIEWED_NOT_SCORING_GT'
        assert final['source_frames_counted'] == final['source_packet_clocks_checked'] == 14107
        assert final['strict_decoder_failure_retained'] == 183 and final['conservative_source_tail_quarantine'] == [14056,14106]
        assert final['overview_anchor_panels_viewed'] == 114 and final['focused_1Hz_panels_viewed'] == 125
        assert final['final_A_B_witness_panels_viewed'] == 72 and final['raster_files_full_decoded'] == 807
        assert final['preview_videos_full_decoded'] == 4 and final['preview_video_frames_full_decoded'] == 3447
        assert final['draft_sha256'] == sha(positive / 'reference/assistant_event_draft_v1.json')
        assert final['local_reference_candidates'] == draft['provisional_downward_candidates'] == 12
        assert final['group_window_candidates'] == 11 and final['late_window_candidates'] == 1 and final['noncow_person_controls'] == 2
        assert final['new_reference_authority'] == 'assistant_provisional_native_visual_review'
        assert final['independent_human_confirmation_received'] is False and final['exact_event_timestamps_finalized'] is False
        assert final['eligible_for_final_scoring'] is False and draft['eligible_for_final_scoring'] is False
        assert final['exact_visual_snapshot_sha256_bound_to_draft'] == draft['visual_review_sha256']
        assert final['original_frozen_draft_rewritten'] is False
        assert final['guide_Markdown_table_lineendings_verified'] is True
        assert final['new_model_forward_calls'] == final['new_training_updates'] == 0
        assert final['current_different_clip_user_confirmed12_preserved'] is True and final['current29_condition_catalog_unchanged'] is True
        assert final['real_cow_bidirectional_coverage_established'] is False and final['FPGA_execution_verified'] is False
        for path,digest in final['evidence_hashes'].items():assert sha(positive/path) == digest
        for row in final['images'] + final['media']:assert sha(Path(row['path'])) == row['sha256']
        positive_reference_study = {'new_ordinary_long_source_frames':14107,'strict_terminal_source_error_retained':True,
                                    'native_overview_panels_viewed':114,'focused_one_Hz_panels_viewed':125,
                                    'provisional_local_candidates':12,'group_candidates':11,'late_candidates':1,'noncow_controls':2,
                                    'reference_authority':'assistant_provisional_native_visual_review',
                                    'independent_human_acceptance_pending':True,'exact_event_times_pending':True,'eligible_for_final_scoring':False,
                                    'frozen_draft_hash_and_exact_visual_snapshot_preserved':True,
                                    'current_other_clip_human_confirmed12_preserved':True,'media_full_decode_frames':3447,
                                    'image_files_full_decoded':807,'new_model_forwards':0,'training_updates':0,
                                    'real_cow_bidirectional_coverage_established':False,'FPGA_execution_verified':False,'whole_goal_complete':False}
    timing_study = None
    timing_root = PROJECT / 'event_timing_refinement_20261029'
    if (timing_root / 'results/final_review.json').exists():
        final = json.loads((timing_root / 'results/final_review.json').read_text(encoding='utf-8'))
        assert final['status'] == 'TWELVE_CONDITIONAL_EVENT_TIMING_SETS_AND_NATIVE_PIXEL_LIMITS_REVIEWED'
        assert final['native_ruler_pages_visually_reviewed'] == 23 and final['native_ruler_panels_visually_reviewed'] == 172
        assert final['manual_working_range_rows'] == 68 and final['region_labels'] == {'N':12,'U':20,'B':36}
        assert final['binary_scenarios_independently_checked'] == 40 and final['conditional_timing_values'] == 32
        assert final['conditional_width_histogram_seconds'] == {'0.4':8,'0.2':4} and final['single_exact_grid_times'] == 0
        assert final['old_review_target_exceeded_by'] == ['R03']
        assert final['eligible_for_final_scoring'] is False and final['independent_human_acceptance_received'] is False
        assert final['manual_ranges_are_calibrated_measurements'] is False
        assert final['new_model_forwards'] == final['new_training_updates'] == final['new_Slurm_jobs'] == 0
        assert final['new_different_clip_user_confirmed12_preserved'] is True and final['current_29_condition_catalog_unchanged'] is True
        for path,digest in final['evidence_hashes'].items():assert sha(timing_root/path) == digest
        for row in final['source_records'] + final['rasters']:assert sha(Path(row['path'])) == row['sha256']
        timing_study = {'native_ruler_panels_viewed':172,'manual_working_centre_ranges':68,'boundary_uncertain_samples':20,
                        'local_binary_scenarios_verified':40,'per_event_candidate_times_total':32,'widths_seconds':{'0.2':4,'0.4':8},
                        'old_review_target_exceeded_by':['R03'],'unique_exact_grid_times':0,
                        'annotation_authority':'assistant_provisional_native_visual_review','eligible_for_final_scoring':False,
                        'independent_human_acceptance_pending':True,'manual_ranges_not_calibrated_error_bounds':True,
                        'current_other_clip_confirmed12_preserved':True,'new_model_forwards':0,'training_updates':0,
                        'FPGA_execution_verified':False,'whole_goal_complete':False}
    long_replay_study = None
    replay_root = PROJECT / 'long_video_fixed_replay_20261029'
    if (replay_root / 'results/final_review.json').exists():
        final = json.loads((replay_root / 'results/final_review.json').read_text(encoding='utf-8'))
        assert final['status'] == 'FOUR_FROZEN_MODELS_NATIVE_LONG_VIDEO_REPLAY_AND_CASE_DIAGNOSIS_REVIEWED'
        assert final['job_id'] == '130345' and final['job_state'] == 'COMPLETED' and final['job_exit_code'] == '0:0'
        assert final['new_model_forwards'] == 8100 and final['independent_counter_paths'] == 8
        assert list(final['handoff_down_predictions'].values()) == [0,11,12,12]
        assert list(final['confirmed_only_down_predictions'].values()) == [0,11,11,12]
        assert final['movie_frames_fully_decoded'] == 12500 and final['actual_panels_viewed'] == 44
        assert final['new_reference_final_scoring_eligible'] is False and final['formal_accuracy_or_F1_computed'] is False
        assert final['new_different_clip_user_confirmed12_preserved'] is True and final['current_29_condition_catalog_unchanged'] is True
        for relative,digest in final['evidence_hashes'].items():assert sha(replay_root/relative) == digest
        for relative,digest in final['source_and_retained_artifact_hashes'].items():assert sha(PROJECT/relative) == digest
        for row in final['documents']:
            document = Path(row['path'])
            # Live project entry points grow after a phase; their current links
            # are checked above. The phase's own published documents stay bound.
            if document.is_relative_to(replay_root): assert sha(document) == row['sha256']
            else: assert document.exists()
        for row in final['rasters']:assert sha(Path(row['path'])) == row['sha256']
        long_replay_study = {'frozen_models':4,'counter_paths':8,'native_observation_ticks':8100,
                             'raw_boxes_inverse_checked':4808,'native_ROI_centers_checked':731,
                             'handoff_down_predictions':final['handoff_down_predictions'],
                             'confirmed_only_down_predictions':final['confirmed_only_down_predictions'],
                             'movies_fully_decoded':12,'movie_frames':12500,'actual_sheets_viewed':11,'actual_panels_viewed':44,
                             'seed26_fragment_case_IDs':[19,23],'seed27_handoff_added_frame0':2720,
                             'new_reference_final_scoring_eligible':False,'formal_accuracy_or_F1_computed':False,
                             'current_other_clip_confirmed12_preserved':True,'new_training_updates':0,
                             'FPGA_execution_verified':False,'whole_goal_complete':False}
    gap_study = None
    gap_root = PROJECT / 'long_video_track_gap_20261029'
    if (gap_root / 'results/final_review.json').exists():
        final = json.loads((gap_root / 'results/final_review.json').read_text(encoding='utf-8'))
        assert final['status'] == 'NATIVE_TRACK_GAP_ASSOCIATION_DIAGNOSIS_AND_ONE_FACTOR_COST_CONTROL_REVIEWED'
        assert final['jobs_completed'] == ['130347','130348','130349'] and final['job_exit_codes'] == ['0:0']*3
        assert final['full_history_replays'] == 4 and final['tracker_updates_each_full_replay'] == 2025
        assert final['independent_cost_entries'] == 51 and final['partial_assignments_enumerated'] == 26
        assert final['new_long_seed26_predictions_before_after'] == [11,12]
        assert final['controlled_short_signal'] == 'GREEN' and final['controlled_event_frame0'] == 2675
        assert final['candidate_adopted'] is False and final['new_reference_final_scoring_eligible'] is False
        assert final['original_confirmed12_candidate_preserved'] is True and final['reference_drafts_preserved'] is True
        for relative,digest in final['evidence_hashes'].items(): assert sha(gap_root/relative) == digest
        assert sha(replay_root/'results/final_review.json') == final['retained_prior_review_sha256']
        for row in final['documents']:
            document = Path(row['path'])
            if document.is_relative_to(gap_root): assert sha(document) == row['sha256']
            else: assert document.exists()
        for row in final['rasters']: assert sha(Path(row['path'])) == row['sha256']
        gap_study = {'full_history_replays':4,'tracker_updates_each':2025,'red_signal_repeats':2,'controlled_short_signal':'GREEN',
                     'independent_cost_entries':51,'partial_assignments_enumerated':26,'controlled_counter_paths':4,
                     'native_ROI_centers':600,'new_long_seed26_predictions':[11,12],'controlled_event_frame0':2675,
                     'other_event_timing_change_frame0':[3845,3840],'source_images_hash_checked':625,
                     'paired_videos_fully_decoded':3,'paired_video_frames':625,'actual_sheets_viewed':6,'actual_panels_viewed':12,
                     'candidate_adopted':False,'old_clip_and_other_seed_regression_pending':True,
                     'current_other_clip_confirmed12_preserved':True,'new_detector_forwards':0,'new_training_updates':0,
                     'formal_scores_computed':False,'FPGA_execution_verified':False,'whole_goal_complete':False}
    firststage_regression_study = None
    regression_root = PROJECT / 'firststage_iou_regression_20261029'
    if (regression_root / 'results/final_review.json').exists():
        final = json.loads((regression_root / 'results/final_review.json').read_text(encoding='utf-8'))
        assert final['status'] == 'FIRSTSTAGE_IOU_NINE_SOURCE_REGRESSION_AND_GLOBAL_NONADOPTION_REVIEWED'
        assert final['jobs_completed'] == ['130351','130352'] and final['job_exit_codes'] == ['0:0','0:0']
        assert final['fixed_sources'] == final['exact_baseline_gate_conditions'] == 9
        assert final['full_tracker_runs'] == 18 and final['counter_paths'] == 36 and final['tracker_update_ticks'] == 31166
        assert final['native_ROI_centers_verified'] == 9027 and final['ROI_pair_IoUs_verified'] == 6367
        assert final['reference_scored_paths'] == 8 and final['exploratory_reference_case_IoUs'] == 175
        assert final['toros_official_TP_FP_FN_before_after'] == [[6,0,0],[5,0,1]]
        assert final['toros_pilot_TP_FP_FN_before_after'] == [[2,0,4],[4,0,2]]
        assert final['movie_frames_fully_decoded'] == 8444 and final['case_panels_actually_viewed'] == 66
        assert final['candidate_global_replacement_adopted'] is False and final['current_confirmed12_candidate_preserved'] is True
        assert final['new_long_reference_final_scoring_eligible'] is False and final['posthoc_scene_or_seed_specific_switching_added'] is False
        for relative,digest in final['evidence_hashes'].items(): assert sha(regression_root/relative) == digest
        for relative,digest in final['retained_artifact_hashes'].items(): assert sha(PROJECT/relative) == digest
        for row in final['documents']:
            document = Path(row['path'])
            if document.is_relative_to(regression_root): assert sha(document) == row['sha256']
            else: assert document.exists()
        for row in final['rasters']: assert sha(Path(row['path'])) == row['sha256']
        firststage_regression_study = {'fixed_sources':9,'exact_baseline_gate_conditions':9,'tracker_conditions':18,
            'counter_paths':36,'tracker_update_ticks':31166,'native_ROI_centers':9027,'box_pair_IoUs':6367,
            'overlap_candidate_pair_ticks':69,'Toros_reference_scored_paths':8,'Toros_case_IoUs':175,
            'new_long_handoff_predictions_before_after':[[0,11,12,12],[0,12,12,12]],
            'original_handoff_predictions_before_after':[[12,11,11],[12,11,11]],
            'Toros_official_TP_FP_FN_before_after':[[6,0,0],[5,0,1]],'Toros_pilot_TP_FP_FN_before_after':[[2,0,4],[4,0,2]],
            'movies_fully_decoded':9,'movie_frames':8444,'actual_sheets_viewed':32,'actual_panels_viewed':66,
            'candidate_global_replacement_adopted':False,'current_confirmed12_preserved':True,
            'new_independent_test':False,'new_long_reference_scores_computed':False,'new_detector_forwards':0,'new_training_updates':0,
            'FPGA_execution_verified':False,'whole_goal_complete':False}
    capture12_study = None
    capture12_root = PROJECT / 'confirmed12_capture_identity_20261029'
    if (capture12_root / 'results/final_review_v3.json').exists():
        final = json.loads((capture12_root / 'results/final_review_v3.json').read_text(encoding='utf-8'))
        assert final['status'] == 'CONFIRMED12_NATIVE_CAPTURE_REAL_IDENTITY_QUERIES_AND_UNVERIFIED_CANDIDATES_REVIEWED'
        assert final['jobs_completed'] == ['130360','130361'] and final['job_exit_codes'] == ['0:0','0:0']
        assert final['source_confirmed_count_preserved'] == final['photos'] == final['tasks_completed'] == 12
        assert final['real_first_queries'] == final['real_repeated_queries'] == 60 and final['interface_self_query_controls'] == 5
        assert final['independent_image_dotproducts'] == 1800 and final['independent_identity_scores'] == 360
        assert final['source_photo_JPEG_reencoding_checks'] == 12 and final['source_quality_pixel_checks'] == 36
        assert final['all_conditions_rejected_events'] == 10 and final['unverified_candidate_events'] == 2
        assert final['candidate_public_anonymous_IDs'] == ['020','009'] and final['source_identity_accuracy'] is None
        assert final['verified_source_identities'] == 0 and final['worker_finished_after_frontend_EOF'] == 0
        assert final['actual_contact_sheets_viewed'] == 5 and final['actual_image_panels_viewed'] == 30
        assert final['snapshot_behavior_tests'] == 8 and final['worker_delta_is_audit_only_verified'] is True
        assert final['current_count_model_and_thresholds_unchanged'] is True and final['new_detector_forwards'] == 0
        for relative,digest in final['evidence_hashes'].items(): assert sha(capture12_root/relative) == digest
        for relative,digest in final['retained_artifact_hashes'].items(): assert sha(PROJECT/relative) == digest
        for row in final['documents']:
            document=Path(row['path'])
            if document.is_relative_to(capture12_root): assert sha(document) == row['sha256']
            else: assert document.exists()
        for row in final['rasters']: assert sha(Path(row['path'])) == row['sha256']
        capture12_study = {'human_total12_count_version_preserved':True,'native_photos':12,'completed_background_jobs':12,
            'cached_observation_ticks':2175,'actual_source_frames_decoded':10874,'real_first_queries':60,'real_fresh_process_repeated_queries':60,
            'interface_gallery_self_query_controls':5,'independent_image_cosines':1800,'independent_identity_scores':360,
            'source_native_JPEG_checks':12,'source_quality_pixel_checks':36,'snapshot_consider_inputs':282,
            'all_conditions_rejected_events':10,'unverified_candidate_events':2,'candidate_public_anonymous_IDs':['020','009'],
            'verified_source_identities':0,'source_identity_accuracy':None,'jobs_finished_after_frontend_EOF':0,
            'retained_snapshot_peak_bytes':12508422,'snapshot_behavior_tests':8,'raster_files_verified':77,
            'actual_sheets_viewed':5,'actual_image_panels_viewed':30,'new_detector_forwards':0,'new_training_updates':0,
            'RF_hardware_connected':False,'FPGA_execution_verified':False,'whole_goal_complete':False}
    rf_stream12_study = None
    rf_stream12_root = PROJECT / 'confirmed12_rf_stream_20261029'
    if (rf_stream12_root / 'results/final_review.json').exists():
        final = json.loads((rf_stream12_root / 'results/final_review.json').read_text(encoding='utf-8'))
        assert final['status'] == 'CAUSAL_RF_STREAM_144_LEDGERS_515_REAL_QUERIES_AND_PRESSURE_CONTROLS_REVIEWED'
        assert final['jobs_completed'] == ['130362','130363'] and final['job_exit_codes'] == ['0:0','0:0']
        assert final['reused_source_events'] == 12 and final['functional_cases'] == 10 and final['real_pressure_controls'] == 2
        assert final['event_ledgers'] == 144 and final['actual_query_configuration_forwards'] == 515
        assert final['causal_RF_contexts'] == 120 and final['independent_read_window_relations'] == 16898
        assert final['independent_image_dotproducts'] == 15450 and final['independent_identity_scores'] == 3090
        assert final['single_code_RF_candidates_and_shared'] == [5,7]
        assert final['late_unique_reads'] == 12 and final['late_event_links'] == 13
        assert final['deliberate_wrong_single_mock_RF_candidates'] == 5
        assert final['burst_actual_query_jobs_capacity_rejects'] == [4,8] and final['expired_waiting_capacity_rejects'] == [4,8]
        assert final['expired_task_query_forwards'] == 0 and final['unit_checks'] == 14 and final['plots_actually_viewed'] == 2
        assert final['current_confirmed12_count_version_and_photos_preserved'] is True and final['source_cow_identity_accuracy'] is None
        for relative,digest in final['evidence_hashes'].items(): assert sha(rf_stream12_root/relative) == digest
        for relative,digest in final['retained_artifact_hashes'].items(): assert sha(PROJECT/relative) == digest
        for row in final['documents']:
            document=Path(row['path'])
            if document.is_relative_to(rf_stream12_root): assert sha(document) == row['sha256']
            else: assert document.exists()
        for row in final['plot_files']: assert sha(Path(row['path'])) == row['sha256']
        rf_stream12_study = {'reused_source_events':12,'functional_cases':10,'real_pressure_controls':2,'event_ledgers':144,
            'real_query_configuration_forwards':515,'completed_query_jobs':103,'causal_RF_contexts':120,'read_window_relations':16898,
            'independent_image_cosines':15450,'independent_identity_scores':3090,'single_code_unique_and_shared':[5,7],
            'late_unique_reads':12,'late_event_links':13,'deliberate_wrong_single_mock_candidates':5,
            'burst_completed_and_capacity_rejects':[4,8],'expired_waiting_and_capacity_rejects':[4,8],'expired_task_query_forwards':0,
            'unit_checks':14,'plot_files':4,'actual_figures_viewed':2,'actual_panels_viewed':3,
            'confirmed12_version_and_source_photos_preserved':True,'RF_hardware_connected':False,'source_cow_identity_accuracy':None,
            'new_detector_forwards':0,'new_training_updates':0,'FPGA_execution_verified':False,'whole_goal_complete':False}
    identity_provenance_study = None
    identity_provenance_root = PROJECT / 'identity_source_provenance_20261029'
    if (identity_provenance_root / 'results/final_review.json').exists():
        final=json.loads((identity_provenance_root / 'results/final_review.json').read_text(encoding='utf-8'))
        assert final['status'] == 'OFFICIAL_SOURCE_MAPPING_AUDIT_AND_E010_ID009_SAME_PASSAGE_EVALUATION_EXCLUSION_REVIEWED'
        assert final['completed_jobs'] == ['130396','130399','130415'] and final['job_exit_codes'] == ['0:0']*3
        assert final['official_ZIP_entries_verified'] == 103156 and final['published_file_catalog_records'] == 101467
        assert final['published_timestamp_CSV_members'] == 0 and final['author_source_text_blobs_verified'] == 102
        assert final['gallery_image_metadata_and_release_checks'] == 30
        assert final['coarse_template_frame_comparisons'] == 13050 and final['refined_template_frame_comparisons'] == 300
        assert final['independent_transform_candidates_checked'] == 182 and final['independent_inlier_point_pairs_checked'] == 3426
        assert [r['source_frame0'] for r in final['strong_core_gallery_source_pairs']] == [9610,9685,9760]
        assert all(r['NCC'] > .99 and r['best_native_track_ID'] == 102 for r in final['strong_core_gallery_source_pairs'])
        assert final['source_trace_associated_event'] == 'E010_f9790_tid102' and final['affected_query_source_frame0'] == 9745
        assert final['independent_identity_evaluation_admitted'] is False and final['source_identity_truth_promoted'] is False
        assert final['current_confirmed12_milestone_preserved'] is True and final['actual_image_panels_viewed'] == 95
        assert final['first_endpoint_weak_match_preserved'] is True and final['last_endpoint_geometry_rejection_preserved'] is True
        for relative,digest in final['evidence_hashes'].items(): assert sha(identity_provenance_root/relative) == digest
        for relative,digest in final['retained_artifact_hashes'].items(): assert sha(PROJECT/relative) == digest
        for row in final['documents']:
            document=Path(row['path'])
            if document.is_relative_to(identity_provenance_root): assert sha(document) == row['sha256']
            else: assert document.exists()
        for row in final['rasters']: assert sha(Path(row['path'])) == row['sha256']
        identity_provenance_study={'official_ZIP_entries':103156,'official_images':101329,'official_videos':137,
            'published_file_records':101467,'timestamp_CSV_members':0,'author_source_text_blobs':102,'gallery_release_checks':30,
            'coarse_comparisons':13050,'local_refinement_comparisons':300,'independent_transform_candidates':182,'photometric_pairs':7,
            'core_ID009_source_frames':[9610,9685,9760],'linked_source_event':'E010_f9790_tid102','query_source_frame0':9745,
            'current_same_passage_gallery_query_pair_admitted_for_independent_identity_evaluation':False,
            'source_identity_truth_promoted':False,'other25_gallery_absence_or_identity_error_inferred':False,
            'endpoint_weak_and_boundary_rejections_preserved':True,'source_rasters_verified':66,'current_sheets_viewed':8,'actual_image_panels_viewed':95,
            'confirmed12_count_milestone_preserved':True,'new_identity_model_forwards':0,'new_training_updates':0,
            'FPGA_execution_verified':False,'whole_goal_complete':False}
    crossdate_gallery_study = None
    crossdate_gallery_root = PROJECT / 'crossdate_gallery_20261029'
    if (crossdate_gallery_root / 'results/final_review.json').exists():
        final=json.loads((crossdate_gallery_root / 'results/final_review.json').read_text(encoding='utf-8'))
        assert final['status']=='FIXED5_ENCODERS_TWO_DATE_GALLERIES_720_DECISIONS_AND_ALL_FALSE_ACCEPT_CASES_REVIEWED'
        assert final['new_gallery_images']==30 and final['paired_model_gallery_conditions']==10
        assert final['labelled_queries']==60 and final['actual_event_query_images']==12
        assert final['actual_successful_run_image_forwards']==660 and final['combined_model_attempt_image_forwards']==1278
        assert final['retrieval_decisions']==720 and final['scalar_dot_products_verified']==21600 and final['identity_scores_verified']==4320
        assert final['old_CPU_gallery_and60_actual_query_feature_maxdelta']==0 and final['old_GPU_all300_predictions_acceptances_exact'] is True
        assert final['prior_CPU_actual_query_tensor_hashes_exact'] is True and final['numerical_gate_failure_and_revision_preserved'] is True
        assert final['new_gallery_C26_C_W_U_unknownFAR']==[27,0,3,5]
        assert final['new_unknown_false_accept_case_model_query_pairs']==8 and final['new_unknown_false_accept_distinct_IDs']==3
        assert len(final['new_real_accepted_candidates'])==1 and final['new_real_accepted_candidates'][0]['predicted_id']=='009'
        assert final['event_identity_accuracy_admitted'] is False and final['new_gallery_later_than_original_source_disclosed'] is True
        assert final['current_confirmed12_count_milestone_preserved'] is True and final['FPGA_execution_verified'] is False
        assert final['actually_viewed_figures']==4 and final['actually_viewed_image_panels']==54 and final['SVG_bar_segments_verified']==40
        assert final['new_training_updates']==0 and final['new_independent_test'] is False and final['whole_goal_complete'] is False
        for relative,digest in final['evidence_hashes'].items(): assert sha(crossdate_gallery_root/relative)==digest
        for relative,digest in final['retained_artifact_hashes'].items(): assert sha(PROJECT/relative)==digest
        for row in final['documents']:
            document=Path(row['path'])
            if document.is_relative_to(crossdate_gallery_root): assert sha(document)==row['sha256']
            else: assert document.exists()
        for row in final['rasters']: assert sha(Path(row['path']))==row['sha256']
        crossdate_gallery_study={k:final[k] for k in ['new_gallery_images','paired_model_gallery_conditions','labelled_queries',
            'actual_event_query_images','actual_successful_run_image_forwards','combined_model_attempt_image_forwards',
            'retrieval_decisions','scalar_dot_products_verified','identity_scores_verified','new_gallery_C26_C_W_U_unknownFAR',
            'new_unknown_false_accept_case_model_query_pairs','new_unknown_false_accept_distinct_IDs',
            'event_identity_accuracy_admitted','new_gallery_later_than_original_source_disclosed',
            'current_confirmed12_count_milestone_preserved','actually_viewed_figures','actually_viewed_image_panels',
            'new_training_updates','new_independent_test','FPGA_execution_verified','whole_goal_complete']}
    crop_domain_study = None
    crop_domain_root = PROJECT / 'crop_domain_20261029'
    if (crop_domain_root / 'results/final_review.json').exists():
        final=json.loads((crop_domain_root / 'results/final_review.json').read_text(encoding='utf-8'))
        assert final['status']=='VALIDATION_FROZEN_CROP_THRESHOLD_40_CONDITIONS_5080_DECISIONS_AND_NONADOPTION_REVIEWED'
        assert final['new_validation_gallery_images']==25 and final['source_inputs_fully_decoded']==182
        assert final['validation_model_rule_conditions']==20 and final['evaluation_model_rule_threshold_conditions']==40
        assert final['model_image_forwards']==3640 and final['validation_before_gate_image_forwards']==1600
        assert final['all_threshold_decisions_verified']==5080 and final['scalar_dot_products_verified']==70700
        assert final['identity_max_scores_verified']==14140 and final['unique_crop_pixel_transforms_verified']==728
        assert final['previous_P0_tensor_hashes_exact']==510 and final['previous_P0_candidates_acceptances_and_features_exact'] is True
        assert final['all20_thresholds_and5_choices_verified'] is True and final['selected_rules']==['P0_original']*4+['P1_border08_both']
        assert final['selected_evaluation_C_W_U_F']==[[19,0,11,3],[14,0,16,2],[26,0,4,3],[19,0,11,1],[19,0,11,0]]
        assert final['all_five_encoders_and_three_seeds_retained'] is True and final['P3_control_never_selected'] is True
        assert final['all_error_model_query_threshold_pairs_preserved']==82 and final['selected_error_pairs_reviewed']==9
        assert len(final['selected_actual_unverified_candidates'])==1 and final['selected_actual_unverified_candidates'][0]['predicted_id']=='009'
        assert final['event_identity_accuracy_admitted'] is False and final['source_identity_truth_promoted'] is False
        assert final['global_crop_or_threshold_replacement_adopted'] is False and final['current_confirmed12_count_milestone_preserved'] is True
        assert final['SVG_bar_segments_verified']==40 and final['SVG_grid_annotation_and_quad_pairs_verified']==80
        assert final['actually_viewed_figures']==6 and final['actually_viewed_image_panels']==72 and final['local_rasters_fully_decoded']==56
        assert final['new_training_updates']==0 and final['new_detector_forwards']==0 and final['new_independent_test'] is False
        assert final['FPGA_execution_verified'] is False and final['whole_goal_complete'] is False
        for relative,digest in final['evidence_hashes'].items(): assert sha(crop_domain_root/relative)==digest
        for relative,digest in final['retained_artifact_hashes'].items(): assert sha(PROJECT/relative)==digest
        for row in final['documents']:
            document=Path(row['path'])
            if document.is_relative_to(crop_domain_root): assert sha(document)==row['sha256']
            else: assert document.exists()
        for row in final['rasters']: assert sha(Path(row['path']))==row['sha256']
        crop_domain_study={k:final[k] for k in ['new_validation_gallery_images','source_inputs_fully_decoded',
            'validation_model_rule_conditions','evaluation_model_rule_threshold_conditions','model_image_forwards',
            'all_threshold_decisions_verified','scalar_dot_products_verified','identity_max_scores_verified',
            'unique_crop_pixel_transforms_verified','previous_P0_tensor_hashes_exact','selected_rules','selected_evaluation_C_W_U_F',
            'all_error_model_query_threshold_pairs_preserved','selected_error_pairs_reviewed','all_actual_candidate_config_event_pairs',
            'event_identity_accuracy_admitted','global_crop_or_threshold_replacement_adopted','current_confirmed12_count_milestone_preserved',
            'actually_viewed_figures','actually_viewed_image_panels','new_training_updates','new_detector_forwards',
            'new_independent_test','FPGA_execution_verified','whole_goal_complete']}
    torso_pair_study = None
    torso_pair_root = PROJECT / 'detector_torso_pairs_20261029'
    if (torso_pair_root / 'results/final_review.json').exists():
        final=json.loads((torso_pair_root / 'results/final_review.json').read_text(encoding='utf-8'))
        assert final['status']=='ACTUAL_DETECTOR_TORSO_PAIRS_INPUT_SCALE_CONTROL_AND_TRAINING_PRIORITY_REVIEWED'
        assert final['source_images']==8380 and final['unique_reference_objects']==10752
        assert final['main_actual_detector_forwards']==13093 and final['adaptive_control_actual_detector_forwards']==288
        assert final['total_actual_detector_forwards']==13381 and final['validation_four_model_matches']==[1141,592,505,226]
        assert final['training_matched_targets']==2920 and final['training_unmatched_references_preserved']==5968
        assert final['all_condition_reference_rows_verified']==16344 and final['all_condition_crop_targets_verified']==5384
        assert final['assignment_candidate_IoUs_verified']==16625 and final['multiple_optimal_assignment_images']==0
        assert final['first_last_baseline_repeats_verified']==64 and final['prior320_sample_correspondences_verified']==48
        assert final['fixed8_CW_table_640rect_320rect_640square_320square']==[[6,3,6,5],[4,11,4,11],[2,10,2,10],[2,7,4,8]]
        assert final['cached_replays_not_new_model_forwards']==9426 and final['ideal_AABB_exterior_above025']==512
        assert final['all_four_models_and_all_three_seeds_retained'] is True and final['global_imgsz320_replacement_adopted'] is False
        assert final['localizer_training_started'] is False and final['planned_new_training_candidate_runs']==9 and final['new_training_updates']==0
        assert final['animal_identity_labels_generated'] is False and final['actual_event_identity_accuracy_admitted'] is False
        assert final['original_human12_count_milestone_preserved'] is True and final['candidate_final_pixels_accessed'] is False
        assert final['actually_viewed_figures']==12 and final['actually_viewed_image_panels']==82 and final['all_local_rasters_decoded']==31
        assert final['SVG_bar_segments_verified']==12 and final['SVG_CDF_values_verified']==4973 and final['SVG_CDF_vertices_verified']==9935
        assert final['FPGA_execution_verified'] is False and final['whole_goal_complete'] is False
        for relative,digest in final['evidence_hashes'].items(): assert sha(torso_pair_root/relative)==digest
        for relative,digest in final['retained_artifact_hashes'].items(): assert sha(PROJECT/relative)==digest
        for row in final['documents']:
            document=Path(row['path'])
            if document.is_relative_to(torso_pair_root): assert sha(document)==row['sha256']
            else: assert document.exists()
        for row in final['rasters']: assert sha(Path(row['path']))==row['sha256']
        torso_pair_study={k:final[k] for k in ['source_images','unique_reference_objects','main_actual_detector_forwards',
            'adaptive_control_actual_detector_forwards','total_actual_detector_forwards','validation_four_model_matches',
            'training_matched_targets','training_unmatched_references_preserved','all_condition_reference_rows_verified',
            'all_condition_crop_targets_verified','first_last_baseline_repeats_verified','prior320_sample_correspondences_verified',
            'ideal_AABB_exterior_above025','global_imgsz320_replacement_adopted','planned_new_training_candidate_runs',
            'animal_identity_labels_generated','actual_event_identity_accuracy_admitted','original_human12_count_milestone_preserved',
            'actually_viewed_figures','actually_viewed_image_panels','new_training_updates','FPGA_execution_verified','whole_goal_complete']}
    lane_crop_study = None
    lane_crop_root = PROJECT / 'lowres_roi_20261029'
    if (lane_crop_root/'results/final_review.json').exists():
        final=json.loads((lane_crop_root/'results/final_review.json').read_text(encoding='utf-8'))
        assert final['status']=='FIXED_LANE_CROP12_CONDITIONS31848_FORWARDS72_PATHS_AND73_VISUAL_PANELS_REVIEWED'
        assert final['input_sizes']==[192,256,320] and final['model_resolution_conditions']==12
        assert final['actual_source_image_forwards']==final['actual_predictor_hook_image_count']==31848
        assert final['full_input_cache_regression_traces']==36 and final['full_input_counter_regression_paths']==72
        assert final['new_tracker_updates']==32808 and final['independent_counter_paths']==72
        assert final['native_inverse_boxes']==9173 and final['maximum_native_inverse_error']==0
        assert final['native_ROI_centers_verified']==8027 and final['formal_event_conditions']==48
        assert final['paired_full_vs_crop_conditions']==72 and final['independent_source_crops']==8
        assert final['actual_NN_input_arrays']==24 and final['model_input_anchor_hashes']==96 and final['maximum_input_float32_delta']<=1.2e-7
        assert final['original_crop_down_counts_4models_by3sizes']==[[0,0,0],[7,8,10],[4,6,10],[8,11,11]]
        assert final['Toros_official_crop_TP_FP_FN_3sizes_by5Hz30Hz']==[[[4,0,2],[5,0,1]],[[3,0,3],[5,0,1]],[[3,0,3],[4,0,2]]]
        assert final['all_models_sizes_sampling_counters_and_negative_results_retained'] is True
        assert final['global_crop_adopted'] is False and final['human_confirmed12_version_preserved'] is True
        assert final['new_training_updates']==0 and final['identity_encoder_forwards']==0 and final['new_independent_test'] is False
        assert final['PYNQ_actions_in_this_offline_experiment']==0 and final['PYNQ5FPS_proven'] is False and final['whole_goal_complete'] is False
        assert final['SVG_bar_count']==72 and final['video_strict_decode_frames']==1962 and final['video_actual_anchor_frames']==4
        assert final['figures_actually_viewed']==13 and final['image_panels_actually_viewed']==73 and final['NN_input_display_panels_pixel_exact']==24
        for relative,digest in final['evidence_hashes'].items(): assert sha(lane_crop_root/relative)==digest
        for relative,digest in final['retained_historical_evidence'].items(): assert sha(PROJECT/relative)==digest
        for row in final['documents']:
            document=Path(row['path'])
            if document.is_relative_to(lane_crop_root): assert sha(document)==row['sha256']
            else: assert document.exists()
        visual=json.loads((lane_crop_root/'evidence/visual_review.json').read_text())
        for row in visual['figures']: assert sha(Path(row['path']))==row['sha256']
        lane_crop_study={k:final[k] for k in ['input_sizes','model_resolution_conditions','actual_source_image_forwards',
            'actual_predictor_hook_image_count','new_tracker_updates','independent_counter_paths','native_inverse_boxes',
            'formal_event_conditions','paired_full_vs_crop_conditions','independent_source_crops','actual_NN_input_arrays',
            'original_crop_down_counts_4models_by3sizes','Toros_official_crop_TP_FP_FN_3sizes_by5Hz30Hz',
            'global_crop_adopted','human_confirmed12_version_preserved','new_training_updates','PYNQ5FPS_proven',
            'video_strict_decode_frames','figures_actually_viewed','image_panels_actually_viewed','whole_goal_complete']}
    lowres_board_study = None
    lowres_root = PROJECT / 'lowres_baseline_20261029'
    board_lowres_root = PROJECT / 'pynq_lowres_20261029'
    if (lowres_root/'results/final_review.json').exists():
        final=json.loads((lowres_root/'results/final_review.json').read_text(encoding='utf-8'))
        assert final['status']=='LOWRES12_CONDITIONS_50700_FORWARDS_72_COUNTER_PATHS_REVIEWED_WITH_UNRESOLVED_BOARD_BENCHMARK'
        assert final['input_sizes']==[192,256,320] and final['target_frontend_Hz']==5 and final['model_resolution_conditions']==12
        assert final['actual_source_detector_image_forwards']==50700 and final['completed_source_records_reused']==44952
        assert final['resume_source_forwards_directly_hooked']==5748 and final['prior_failed_job_in_memory_hook_counter_not_invented'] is True
        assert final['all_counter_updates']==32808 and final['independent_counter_paths']==72
        assert final['validation_candidate_IoUs']==20801 and final['native_inverse_boxes']==43119 and final['publisher6_metric_conditions']==48
        assert final['original_down_counts_4models_by3sizes']==[[0,0,0],[0,7,10],[1,7,8],[2,7,10]]
        assert final['Toros_official_TP_FP_FN_3sizes_by5Hz30Hz']==[[[1,0,5],[4,0,2]],[[4,0,2],[6,0,0]],[[4,0,2],[6,0,0]]]
        assert final['new_training_updates']==0 and final['new_lowres_training_conditions_submitted']==0 and final['human_confirmed12_version_preserved'] is True
        assert final['board_inventory_live_confirmed'] is True and final['PYNQ_version']=='3.1.1'
        assert final['own_board_benchmark_PID']==8082 and final['own_board_benchmark_terminal_state']=='NOT_OBSERVED'
        assert final['own_board_benchmark_restart_count']==0 and final['current_PL_after_benchmark']=='UNKNOWN_NOT_READ_BACK'
        assert final['current_live_PYNQ_5FPS_proven'] is False and final['foreground_background_joint_PYNQ_5FPS_proven'] is False
        assert final['current_image_panels_actually_viewed']==52 and final['three_movies_strict_decoded_frames']==5886
        assert final['actual_video_frame_alignment_checks']==12 and final['current_SVG_bar_segments_verified']==48
        assert final['new_final_test'] is False and final['whole_goal_complete'] is False
        for relative,digest in final['evidence_hashes'].items(): assert sha(lowres_root/relative)==digest
        for relative,digest in final['board_evidence_hashes'].items(): assert sha(board_lowres_root/relative)==digest
        for relative,digest in final['retained_artifact_hashes'].items(): assert sha(PROJECT/relative)==digest
        for row in final['board_source_file_records']: assert sha(Path(row['path']))==row['sha256']
        for row in final['documents']:
            document=Path(row['path'])
            if document.is_relative_to(lowres_root) or document.is_relative_to(board_lowres_root): assert sha(document)==row['sha256']
            else: assert document.exists()
        for row in final['rasters']: assert sha(Path(row['path']))==row['sha256']
        fresh=json.loads((board_lowres_root/'evidence/final_connectivity_recheck.json').read_text(encoding='utf-8'))
        assert fresh['benchmark_PID8082_terminal_still_not_observed'] is True and fresh['no_restart_or_programming_performed'] is True
        lowres_board_study={k:final[k] for k in ['input_sizes','target_frontend_Hz','model_resolution_conditions',
            'actual_source_detector_image_forwards','all_counter_updates','independent_counter_paths','publisher6_metric_conditions',
            'original_down_counts_4models_by3sizes','Toros_official_TP_FP_FN_3sizes_by5Hz30Hz','new_training_updates',
            'new_lowres_training_conditions_submitted','human_confirmed12_version_preserved','PYNQ_version','own_board_benchmark_PID',
            'own_board_benchmark_terminal_state','current_live_PYNQ_5FPS_proven','foreground_background_joint_PYNQ_5FPS_proven',
            'current_image_panels_actually_viewed','three_movies_strict_decoded_frames','whole_goal_complete']}
        lowres_board_study['final_connectivity_recheck_sha256']=sha(board_lowres_root/'evidence/final_connectivity_recheck.json')
    recovered_board_study = None
    recovered_board_root = PROJECT / 'pynq_board_validation_20261029'
    if (recovered_board_root/'results/final_review.json').exists():
        final=json.loads((recovered_board_root/'results/final_review.json').read_text(encoding='utf-8'))
        assert final['status']=='REAL_PYNQ_3SIZE_PROFILES_AND_TWO_PERIODIC_INPUT_CONTROLS_REVIEWED_WITH424_ACTUAL_FORWARDS'
        assert final['actual_PYNQ_FPGA_and_ARM_network_execution_verified'] is True and final['hardware_performance_phase_complete'] is True
        assert final['PYNQ_version']=='3.1.1' and final['actual_IP']=='192.168.2.99' and final['input_sizes']==[192,256,320]
        assert final['engines']==['O8resident','O8resident','O6legacy'] and final['three_sizes_same_engine_control'] is False
        assert [round(v,2) for v in final['formal_latency_means_ms']]==[158.79,261.82,1056.39]
        assert final['total_actual_hardware_image_forwards']==424 and final['raw_arrays_verified']==406
        assert final['formal_samples']==96 and final['probe_samples']==1 and final['warmup_records']==18
        assert final['fixed_E010_raw_repeats_exact']==60 and final['prior_interrupted192_raw_repeats_exact']==12
        assert final['CPU_input_timing_operations']==324 and final['independent_native_photo_decodes']==12
        assert final['input_letterbox_conditions']==36 and final['input_arrays_verified']==108
        assert final['resize_before_rotation_different_conditions']==12 and final['resize_before_rotation_maximum_uint8_delta']==1
        assert final['jpeg_periodic_processed_3sizes']==[60,45,17] and final['jpeg_periodic_skipped_3sizes']==[40,55,83]
        assert final['framebank_periodic_processed_3sizes']==[98,69,20] and final['framebank_periodic_skipped_3sizes']==[2,31,80]
        assert final['framebank_deadline_misses_3sizes']==[16,69,20] and final['framebank_observed_FPS_3sizes'][0]==4.9
        assert final['same_pixel_raw_comparison_rows']==182 and final['same_pixel_unique_model_query_conditions']==31
        assert final['all7_own_board_processes_terminal_and_absent'] is True and final['recovered_board_services_currently_accessible'] is True
        assert final['final_known_O8_bit_sha256']=='5da7a73bf52fd5153e25de5c28a40e2080c29e960d767008e0e804ec527bbfd8'
        assert final['old_PID8082_result_admitted_for_performance'] is False and final['old_interrupted39_files_preserved'] is True
        assert final['old_service_loss_root_cause_proven'] is False and final['board_model_is_existing_COCO_quantized_assets'] is True
        assert final['current_cow_finetuned_weights_deployed'] is False and final['cow_present_photos_each_fullinput_size']==[0,0,0]
        assert final['current12_cow_count_accuracy_admitted'] is False and final['foreground_tracking_active'] is False
        assert final['camera_hardware_active'] is False and final['background_identity_active'] is False
        assert final['complete_pipeline_stable5FPS_proven'] is False and final['foreground_background_joint5FPS_proven'] is False
        assert final['new_training_updates']==0 and final['new_independent_accuracy_test'] is False and final['whole_goal_complete'] is False
        for relative,digest in final['evidence_hashes'].items(): assert sha(recovered_board_root/relative)==digest
        for relative,digest in final['retained_artifact_hashes'].items(): assert sha(PROJECT/relative)==digest
        for row in final['documents']:
            document=Path(row['path'])
            if document.is_relative_to(recovered_board_root): assert sha(document)==row['sha256']
            else: assert document.exists()
        recovered_board_study={k:final[k] for k in ['actual_PYNQ_FPGA_and_ARM_network_execution_verified','input_sizes',
            'formal_latency_means_ms','formal_latency_P95_ms','engines','three_sizes_same_engine_control',
            'total_actual_hardware_image_forwards','raw_arrays_verified','CPU_input_timing_operations',
            'jpeg_periodic_processed_3sizes','framebank_periodic_processed_3sizes','framebank_deadline_misses_3sizes',
            'framebank_observed_FPS_3sizes','same_pixel_raw_comparison_rows','all7_own_board_processes_terminal_and_absent',
            'board_model_is_existing_COCO_quantized_assets','current_cow_finetuned_weights_deployed','current12_cow_count_accuracy_admitted',
            'foreground_tracking_active','background_identity_active','complete_pipeline_stable5FPS_proven','foreground_background_joint5FPS_proven',
            'original_human12_milestone_preserved','new_training_updates','whole_goal_complete']}
    cow_O8_compile_study = None
    cow_O8_root = PROJECT / 'pynq_cow_compile_20261029'
    if (cow_O8_root/'results/final_review.json').exists():
        final=json.loads((cow_O8_root/'results/final_review.json').read_text(encoding='utf-8'))
        assert final['status']=='COW1_CLASS192_O8_NATIVE_COMPILE_AND8_REAL_BOARD_VECTORS_REVIEWED'
        assert final['implementation_qualification_phase_complete'] is True and final['user_confirmed_O8_engine'] is True
        assert final['class_count']==1 and final['input_size']==192 and final['train_only_PTQ_calibration_images']==128
        assert final['static_graph_nodes']==383 and final['static_tensors']==2132 and final['graph_bytes']==14605169
        assert final['PL_integer_convolutions']==94 and final['ARM_integer_depthwise']==8 and final['resident_pairs']==25
        assert final['exact_structure_rewrite_count']==3 and final['original_and_normalized_ONNX_training_vectors_exact']==8
        assert final['CPU_reference_and_native_training_vectors_exact']==8 and final['actual_PYNQ_FPGA_ARM_training_vectors_exact']==8
        assert final['actual_board_model_forwards_with2warmups']==10 and final['strict_raw_byte_arrays_exact']==8
        assert final['class_LUT_scalar_code_checks']==768 and final['maximum_scalar_sigmoid_delta']<2e-7
        assert final['board_maximum_box_error']==final['board_maximum_score_error']==0
        assert final['new_firmware_programmed'] is False and final['original_O8_runtime_and_firmware_hashes_preserved'] is True
        assert final['board_process_terminal_and_absent'] is True and final['old_seed26_qualifier_not_new15_models'] is True
        assert final['new15_lowres_models_deployed'] is False and final['real_source_video_count_accuracy_admitted'] is False
        assert final['camera_active'] is False and final['background_identity_active'] is False
        assert final['foreground_background_joint5FPS_proven'] is False and final['new_training_updates_in_this_compile_phase']==0
        assert final['original_human12_milestone_preserved'] is True and final['whole_goal_complete'] is False
        for relative,digest in final['evidence_hashes'].items(): assert sha(cow_O8_root/relative)==digest
        for relative,digest in final['retained_artifact_hashes'].items(): assert sha(PROJECT/relative)==digest
        for row in final['documents']:
            doc=Path(row['path'])
            if doc.is_relative_to(cow_O8_root): assert sha(doc)==row['sha256']
            else: assert doc.exists()
        cow_O8_compile_study={k:final[k] for k in ['class_count','input_size','train_only_PTQ_calibration_images',
            'static_graph_nodes','static_tensors','PL_integer_convolutions','ARM_integer_depthwise','resident_pairs',
            'exact_structure_rewrite_count','actual_PYNQ_FPGA_ARM_training_vectors_exact','actual_board_model_forwards_with2warmups',
            'strict_raw_byte_arrays_exact','board_maximum_box_error','board_maximum_score_error','new_firmware_programmed',
            'original_O8_runtime_and_firmware_hashes_preserved','board_process_terminal_and_absent','old_seed26_qualifier_not_new15_models',
            'new15_lowres_models_deployed','real_source_video_count_accuracy_admitted','foreground_background_joint5FPS_proven',
            'original_human12_milestone_preserved','whole_goal_complete']}
    lowres_factorial_study = None
    lowres_factorial_root = PROJECT / 'detector_factorial_20261029'
    if (lowres_factorial_root/'results/final_review.json').exists():
        final=json.loads((lowres_factorial_root/'results/final_review.json').read_text(encoding='utf-8'))
        assert final['status']=='ALL15_LOWRES_TRAINED_WEIGHTS63375_FORWARDS90_COUNTER_PATHS_REVIEWED_WITH_NONADOPTION'
        assert final['training_and_offline_evaluation_phase_complete'] is True and final['new_conditions']==15 and final['historical320_plain_controls']==3
        assert final['new_total_epochs']==150 and final['formal_optimizer_updates']==18375 and final['observed_training_batches']==31950
        assert final['training_image_presentations']==1021350 and final['discarded_smoke_updates']==12
        assert final['all15_fixed_last_epoch_weights_frozen_before_video'] is True and final['no_training_repeated_after_completed_weights'] is True
        assert final['original_training_array_postprocess_states_preserved']=='ALL15_FAILED1:0_AT_LF_ONLY_SCHEDULE_HASH_ASSERT'
        assert final['gradient_arrays_recovered'] is False and final['rotation_schedules_reconstructed_not_observed'] is True
        assert final['actual_new_detector_image_forwards']==final['predictor_hook_image_count']==63375
        assert final['validation_matching_cases']==23565 and final['candidate_validation_IoUs']==43792 and final['native_inverse_boxes']==61225
        assert final['maximum_native_inverse_error']==0 and final['ROI_centers_verified']==10137 and final['new_tracker_updates']==41010
        assert final['independent_counter_paths']==90 and final['publisher6_event_score_conditions']==60 and final['cached_control_regression_counter_paths']==36
        assert final['new_original_down_counts_groups_by_seeds']==[[6,4,5],[6,5,5],[8,9,8],[7,8,8],[7,8,7]]
        assert final['new_validation_matches_groups_by_seeds']==[[1754,1596,1773],[1819,1810,1851],[1697,1730,1800],[1835,1851,1845],[1843,1845,1846]]
        assert final['all_seeds_and_negative_results_retained'] is True and final['new_model_adopted_globally'] is False
        assert final['new15_weights_actual_PYNQ_video_count_verified'] is False and final['foreground_background_joint5FPS_proven'] is False
        assert final['original_human12_milestone_preserved'] is True and final['new_independent_test'] is False and final['whole_goal_complete'] is False
        for relative,digest in final['evidence_hashes'].items(): assert sha(lowres_factorial_root/relative)==digest
        for relative,digest in final['retained_artifact_hashes'].items(): assert sha(PROJECT/relative)==digest
        for row in final['documents']:
            doc=Path(row['path'])
            if doc.is_relative_to(lowres_factorial_root): assert sha(doc)==row['sha256']
            else: assert doc.exists()
        lowres_factorial_study={k:final[k] for k in ['new_conditions','historical320_plain_controls','new_total_epochs',
            'formal_optimizer_updates','training_image_presentations','all15_fixed_last_epoch_weights_frozen_before_video',
            'gradient_arrays_recovered','rotation_schedules_reconstructed_not_observed','actual_new_detector_image_forwards',
            'validation_matching_cases','native_inverse_boxes','independent_counter_paths','publisher6_event_score_conditions',
            'new_original_down_counts_groups_by_seeds','new_validation_matches_groups_by_seeds','new_model_adopted_globally',
            'new15_weights_actual_PYNQ_video_count_verified','foreground_background_joint5FPS_proven','original_human12_milestone_preserved','whole_goal_complete']}
    lowres_event_audit_study = None
    lowres_event_root = PROJECT / 'lowres_event_audit_20261029'
    if (lowres_event_root/'results/final_review.json').exists():
        final=json.loads((lowres_event_root/'results/final_review.json').read_text(encoding='utf-8'))
        assert final['status']=='39_CACHED_CONDITIONS78_DIAGNOSTIC_CASES234_ORACLE_PATHS_AND36_NATIVE_PIXEL_PANELS_REVIEWED'
        assert final['full_input_cached_conditions']==27 and final['fixed_crop_cached_conditions']==12 and final['diagnostic_cases']==78
        assert final['fixed_IoU_levels']==[.5,.3] and final['reference_tracks']==12 and final['reference_box_samples']==581
        assert final['unique_raw640_prior_admissions']==12 and final['reference_self_events_and_exact_frames_verified']==12
        assert final['case_reference_rows']==45318 and final['independent_assignment_problems']==55848 and final['independent_counter_oracle_paths']==234
        assert final['primary_case']=='S192_rot90_seed26' and final['primary_actual_down_count']==6
        assert final['primary_presence_raw_center_post_center_oracle_counts']==[6,6,5]
        assert final['primary_unmapped_reference_tracks']==[93,94,96,103,98,102]
        assert final['primary6_fail_presence_oracle_at_both_IoU_levels'] is True
        assert final['primary_entry_region_insufficient_cases']==5 and final['primary_exit_region_insufficient_cases']==1
        assert final['actual_above_some_oracle_full_input_conditions']==13 and final['oracles_are_not_monotonic_upper_bounds'] is True
        assert final['reference_is_independent_GT'] is False and final['actual_animal_identity_labels_created'] is False and final['formal_reference_F1_admitted'] is False
        assert final['new_network_forwards']==final['new_training_updates']==final['PYNQ_actions']==0 and final['global_runtime_pipeline_changed'] is False
        assert final['source_frame_scope']==[8912,10873] and final['actual_PTS_native_frame_pixel_checks']==18
        assert final['figures_actually_viewed']==6 and final['image_panels_actually_viewed']==36
        assert final['next_fixed_crop_conditions']==15 and final['next_fixed_crop_detector_forwards_planned']==39810 and final['next_crop_job_submitted'] is False
        assert sha(PROJECT/'factorial_lane_crop_20261029/protocol/crop_v1.json')==final['next_crop_protocol_sha256']
        assert final['original_human12_milestone_preserved'] is True and final['foreground_background_joint5FPS_proven'] is False and final['whole_goal_complete'] is False
        for relative,digest in final['evidence_hashes'].items(): assert sha(lowres_event_root/relative)==digest
        for relative,digest in final['retained_artifact_hashes'].items(): assert sha(PROJECT/relative)==digest
        for row in final['documents']:
            doc=Path(row['path'])
            if doc.is_relative_to(lowres_event_root): assert sha(doc)==row['sha256']
            else: assert doc.exists()
        visual=json.loads((lowres_event_root/'results/visual_review.json').read_text())
        for row in visual['pages']: assert sha(Path(row['path']))==row['sha256']
        lowres_event_audit_study={k:final[k] for k in ['full_input_cached_conditions','fixed_crop_cached_conditions',
            'diagnostic_cases','reference_box_samples','independent_assignment_problems','independent_counter_oracle_paths',
            'primary_actual_down_count','primary_presence_raw_center_post_center_oracle_counts','primary_unmapped_reference_tracks',
            'primary_entry_region_insufficient_cases','primary_exit_region_insufficient_cases','oracles_are_not_monotonic_upper_bounds',
            'reference_is_independent_GT','new_network_forwards','new_training_updates','PYNQ_actions','actual_PTS_native_frame_pixel_checks',
            'figures_actually_viewed','image_panels_actually_viewed','next_fixed_crop_conditions','next_fixed_crop_detector_forwards_planned',
            'next_crop_job_submitted','original_human12_milestone_preserved','foreground_background_joint5FPS_proven','whole_goal_complete']}
    new_lane_crop_study = None
    new_lane_root = PROJECT / 'factorial_lane_crop_20261029'
    if (new_lane_root/'results/final_review.json').exists():
        final=json.loads((new_lane_root/'results/final_review.json').read_text(encoding='utf-8'))
        assert final['status']=='15_NEW_MODELS39810_CROP_FORWARDS90_COUNTER_PATHS_AND54_VISUAL_PANELS_REVIEWED'
        assert final['fixed_crop_phase_complete'] is True and final['condition_count']==15
        assert final['real_new_detector_forwards']==39810 and final['counter_observation_ticks']==41010 and final['counter_paths']==90
        assert final['raw_boxes_inverse_verified']==16286 and final['actual_NN_anchor_hashes']==120 and final['unique_actual_NN_arrays']==24
        assert final['primary_case']=='S192_rot90_seed26' and final['primary_original_down_count']==10 and final['human_confirmed_total']==12
        assert final['original_event_level_GT'] is False and final['new_independent_test'] is False
        assert final['publisher_formal_scoring_conditions']==60 and final['strict_decoded_video_frames']==3924 and final['movies']==2
        assert final['SVG_bars']==36 and final['figures_actually_viewed']==9 and final['panels_actually_viewed']==54
        assert final['inference_job']=='130559' and final['failed_media_job']=='130563' and final['completed_media_job']=='130564'
        assert final['new_training_updates']==final['board_actions']==0 and final['global_pipeline_replaced'] is False
        assert final['model_selected_using_new_crop_count'] is False and final['original_human12_milestone_preserved'] is True
        assert final['foreground_background_joint5FPS_proven'] is False and final['whole_goal_complete'] is False
        for relative,digest in final['evidence_hashes'].items():assert sha(new_lane_root/relative)==digest
        for relative,digest in final['retained_artifact_hashes'].items():assert sha(PROJECT/relative)==digest
        for row in final['documents']:assert sha(Path(row['path']))==row['sha256']
        visual=json.loads((new_lane_root/'results/visual_review.json').read_text(encoding='utf-8'))
        for row in visual['files']:assert row['actually_viewed'] is True and sha(Path(row['path']))==row['sha256']
        new_lane_crop_study={k:final[k] for k in ['condition_count','real_new_detector_forwards','counter_paths',
            'paired_original_groups','primary_case','primary_original_down_count','human_confirmed_total','original_event_level_GT',
            'publisher_formal_scoring_conditions','strict_decoded_video_frames','figures_actually_viewed','panels_actually_viewed',
            'new_training_updates','board_actions','original_human12_milestone_preserved','foreground_background_joint5FPS_proven','whole_goal_complete']}
    rot192_vector_qualification = None
    rot192_root = PROJECT / 'pynq_rot192_compile_20261029'
    if (rot192_root/'results/strict_raw_bytes_verification.json').exists():
        checked=json.loads((rot192_root/'results/independent_implementation_verification.json').read_text())
        strict=json.loads((rot192_root/'results/strict_raw_bytes_verification.json').read_text())
        assert checked['model_checkpoint_sha256']=='7b01cead4841f17d561f2a6bd768f9b229f1b3bd142818d8302135d3c69ffd45'
        assert checked['size']==192 and checked['class_count']==1 and checked['dense_PL_convolutions']==94 and checked['integer_ARM_depthwise']==8
        assert checked['actual_FPGA_ARM_reference_vectors_checked']==8 and checked['actual_model_forwards_with2warmups']==10
        assert checked['board_maximum_box_error']==checked['board_maximum_score_error']==0 and checked['actual_board_raw_arrays_byte_exact'] is True
        assert checked['one_preselected_new_model_actual_board_vectors_verified'] is True and checked['all15_new_models_board_verified'] is False
        assert len(strict['arrays'])==8 and all(row['CPU_reference_native_and_board_bytes_exact'] for row in strict['arrays'])
        assert checked['real_source_video_count_or_identity_accuracy_admitted'] is False and checked['foreground_background_joint5FPS_proven'] is False
        rot192_vector_qualification={k:checked[k] for k in ['model_checkpoint_sha256','size','class_count',
            'actual_FPGA_ARM_reference_vectors_checked','actual_model_forwards_with2warmups','actual_board_raw_arrays_byte_exact',
            'mean_training_vector_tensor_to_raw_ms','one_preselected_new_model_actual_board_vectors_verified',
            'real_source_video_count_or_identity_accuracy_admitted','foreground_background_joint5FPS_proven','whole_goal_complete']}
    actual_rot192_video_study = None
    actual_rot192_root = PROJECT/'pynq_rot192_eval_20261029'
    if (actual_rot192_root/'results/final_review.json').exists():
        final=json.loads((actual_rot192_root/'results/final_review.json').read_text(encoding='utf-8'))
        assert final['status']=='FIXED_ROT192_QUALITY2654_REAL_O8_VIDEO_FORWARDS6_ARM_COUNTER_PATHS_AND16_VISUAL_PANELS_REVIEWED'
        assert final['real_quality_ORT_forwards']==8450 and final['native_integer_video_anchor_forwards']==8
        assert final['actual_O8_video_forwards']==final['actual_O8_raw_archive_arrays']==final['all_input_PNG_tensors_verified']==2654
        assert final['actual_ARM_counter_paths']==6 and final['actual_ARM_counter_observation_ticks']==2734 and final['server_counter_paths']==12
        assert final['FP32_QDQ_actual_O8_original_counts']==[10,11,11] and final['actual_O8_Toros_handoff_TP_FP_FN_both_sampling_rates']==[1,0,5]
        assert final['prior_human_total12_preserved'] is True and final['original_human_event_level_GT'] is False
        assert final['actual8_video_anchor_raw_bytes_exact'] is True and final['QDQ_ORT_raw_equals_actual_O8_raw'] is False
        assert abs(final['mean_PNG_to_counter_ms']-178.2404283862095)<1e-8 and final['processing_over200ms_frames']==118
        assert final['figures_actually_viewed']==5 and final['panels_actually_viewed']==16 and final['strict_decoded_movie_frames']==1962
        assert final['actual_board_process_terminal_and_absent'] is True and final['original_O8_firmware_reprogrammed'] is False
        assert final['periodic_deadline_scheduler_tested'] is False and final['simultaneous_identity_tested'] is False
        assert final['whole_goal_complete'] is False and final['foreground_background_joint5FPS_proven'] is False
        for relative,digest in final['evidence_hashes'].items():assert sha(actual_rot192_root/relative)==digest
        for relative,digest in final['retained_artifact_hashes'].items():assert sha(PROJECT/relative)==digest
        for row in final['documents']:assert sha(Path(row['path']))==row['sha256']
        visual=json.loads((actual_rot192_root/'results/visual_review.json').read_text(encoding='utf-8'))
        for row in visual['files']:assert row['actually_viewed'] and sha(Path(row['path']))==row['sha256']
        actual_rot192_video_study={k:final[k] for k in ['actual_O8_video_forwards','actual_ARM_counter_paths','actual_ARM_counter_observation_ticks',
          'FP32_QDQ_actual_O8_original_counts','actual_O8_Toros_handoff_TP_FP_FN_both_sampling_rates','actual8_video_anchor_raw_bytes_exact',
          'mean_PNG_to_counter_ms','P95_PNG_to_counter_ms','processing_over200ms_frames','periodic_deadline_scheduler_tested',
          'livecamera_tested','simultaneous_identity_tested','figures_actually_viewed','panels_actually_viewed',
          'foreground_background_joint5FPS_proven','whole_goal_complete']}
    numpy_tracker_port_study = None
    tracker_port_root=PROJECT/'pynq_frontend_port_20261029'
    if (tracker_port_root/'independent_verification.json').exists():
        port=json.loads((tracker_port_root/'independent_verification.json').read_text())
        assert port['status']=='FROZEN_TRACKER_CORE_AST_AND90_SERVER_PLUS90_REAL_ARM_TRACES_REVIEWED'
        assert port['upstream_class_definitions_AST_exact']==6 and port['upstream_top_level_functions_AST_exact']==10
        assert port['server_traces_exact']==port['actual_board_traces']==90 and port['server_and_board_counter_paths_each']==180
        assert port['server_and_board_observation_ticks_each']==82020 and port['actual_board_post_tracker_rows']==40893
        assert port['maximum_board_vs_reference_box_pixels']==.0001220703125
        assert port['all_board_track_IDs_and_counter_events_runtime_checked_exact'] is True
        assert port['model_forwards']==port['PL_actions']==0 and port['global_dependency_changes'] is False
        for relative,digest in port['evidence_hashes'].items():assert sha(tracker_port_root/relative)==digest
        numpy_tracker_port_study={k:port[k] for k in ['server_traces_exact','actual_board_traces','server_and_board_counter_paths_each',
            'server_and_board_observation_ticks_each','maximum_board_vs_reference_box_pixels',
            'all_board_track_IDs_and_counter_events_runtime_checked_exact','task_specific_compilation_and_regression_proven',
            'general_LAP_numpy_compatibility_certified','global_dependency_changes','model_forwards','PL_actions','whole_goal_complete']}
    same_board_study_expectations = {
      'pynq_identity_ncnn_20261029': (
        'FIXED_BODY_ENCODER132_ACTUAL_ARM_VECTORS132_PHOTO_INPUTS_AND144_RETRIEVAL_DECISIONS_REVIEWED',
        {'actual_ARM_formal_vectors':132,'all_runtime_photo_input_tensors_exact':132,'retrieval_decisions_exact':144,
         'prior_failed_formal_vectors':4,'global_Pillow_or_numpy_changed':False,'new_permanent_identity_accuracy_proven':False}),
      'pynq_periodic_joint_20261030': (
        'SAME_PYNQ_ACTUAL_PERIODIC_DETECTION_AND11_REAL_BACKGROUND_IDENTITY_JOBS_REVIEWED',
        {'actual_O8_timed_forwards':781,'actual_same_board_background_jobs':11,'case_processed_frames':[392,389],
         'case_skipped_slots':[0,3],'case_deadline_misses':[23,128],'case_source_counts':[11,11],
         'all11_runtime_photo_and_tensor_reconstructed':True,'approx5FPS_mean_throughput_observed':True,
         'all200ms_deadlines_met':False,'highres_and_RFID_inputs_are_replay_and_simulation':True}),
      'pynq_idle_control_20261030': (
        'ACTUAL_IDLE_GATED_PYNQ783_FRAMES392_STOP_WINDOWS_AND11_BACKGROUND_JOBS_REVIEWED',
        {'actual_O8_timed_forwards':783,'actual_stop_resume_pairs':392,'actual_same_board_identity_jobs':11,
         'case_processed_frames':[391,392],'case_skipped_slots':[1,0],'case_late_frames':[17,28],
         'case_source_down_counts':[11,11],'all200ms_deadlines_met':False,'new_permanent_identity_accuracy_proven':False}),
      'pynq_capture_encoding_20261030': (
        'PNG_PIXEL_EXACT22_WRITE_BENCHMARK_AND_THREE1170_O8_FRAME22_IDENTITY_JOB_CONTROLS_REVIEWED',
        {'lossless_photo_pair_checks':11,'actual_board_PNG_writes':22,'actual_O8_timed_forwards':1170,
         'actual_background_identity_jobs':22,'case_processed_frames':[390,392,388],'case_skips':[2,0,4],
         'case_deadline_misses':[20,67,25],'case_source_counts':[11,11,11],
         'same_frame_same_box_prior_input_and_feature_exact_pairs':17,'all22_runtime_photos_and_tensors_reconstructed':True,
         'zero_deadline_misses_proven':False,'actual_camera_or_RFID_hardware':False}),
      'rot192_event_diagnosis_20261030': (
        'THREE_FIXED192_IMPLEMENTATIONS6_CASES18_ORACLE_PATHS_AND45_HEAD_ARRAYS_REVIEWED',
        {'source_counts':[10,11,11],'remaining_O8_development_reference_tracks':[94],
         'reference_is_independent_GT':False,'reference_rows':3486,'association_problems':4296,
         'oracle_paths':18,'unfiltered_head_arrays':45,'threshold_or_counter_changed':False,'new_model_forwards':0}),
      'pynq_o8_sizes_20261030': (
        'SAME_O8_S256_AND_S320_ACTUAL_BOARD_VECTORS_AND_ORDERED_FLOAT_REFERENCE_REVIEWED',
        {'actual_new_board_qualification_vectors':16,'actual_new_board_warmups':4,'same_O8_firmware_as192':True,
         'all16_actual_raw_bytes_exact_to_native_and_qualified_reference':True,'ordered_reference_vectors_exact':24,
         'original_numpy_reference_vectors_exact':23,'original320_full_raw_failure_preserved':True,
         'reference_nonconv_float_order_explicitly_revised':True,'native_engine_weights_calibration_or_firmware_changed':False,
         'both_actual_board_processes_terminal_and_absent':True})}
    actual_same_board_studies = {}
    for relative,(status,expectations) in same_board_study_expectations.items():
        study_root=PROJECT/relative
        final=json.loads((study_root/'results/final_review.json').read_text(encoding='utf-8'))
        assert final['status']==status and final['whole_goal_complete'] is False and final['new_training_updates']==0
        for key,value in expectations.items():assert final[key]==value,(relative,key,final[key],value)
        for evidence,digest in final['evidence_hashes'].items():assert sha(study_root/evidence)==digest,(relative,evidence)
        for row in final['documents']:assert sha(Path(row['path']))==row['sha256']
        visual_file=study_root/'results/visual_review.json'
        if visual_file.exists():
            visual=json.loads(visual_file.read_text(encoding='utf-8'))
            if 'files' in visual:
                for row in visual['files']:assert row['actually_viewed'] and sha(Path(row['path']))==row['sha256']
            elif 'file' in visual:assert sha(Path(visual['file']))==visual['sha256']
        actual_same_board_studies[relative]={'status':status,**{key:final[key] for key in expectations},'whole_goal_complete':False}
    photometric_root=PROJECT/'photometric_input_20261030'
    photometric_final=json.loads((photometric_root/'results/final_review.json').read_text(encoding='utf-8'))
    assert photometric_final['status']=='THREE_FIXED_INPUT_CONDITIONS25350_ORT_FORWARDS36_EVENT_PATHS_AND34_PANELS_REVIEWED'
    photometric_expectations={'actual_successful_study_forwards':25350,'failed_v1_completed_arrays_preserved':7492,
        'baseline_raw_arrays_byte_exact':8450,'baseline_video_input_hashes_exact':2654,'all_input_hashes_rebuilt_from_source':12675,
        'validation_matching_problems':9426,'raw_video_rows':15924,'counter_observation_ticks':16404,'counter_paths':36,'publisher_matching_paths':24,
        'original_FP32_QDQ_counts_by_none_gamma_CLAHE':[10,11,8,10,8,8],
        'validation_TP_by_none_gamma_CLAHE':[1819,1814,1830,1823,1824,1810],
        'Toros5Hz_TP_by_none_gamma_CLAHE':[1,1,1,1,0,0],'Toros30Hz_TP_by_none_gamma_CLAHE':[1,1,1,2,0,0],
        'head_arrays_in_remaining_case_diagnosis':90,'development_reference_is_independent_GT':False,
        'actual_SVG_bars_checked':30,'input_panels_checked':30,'figures_actually_viewed':3,'panels_actually_viewed':34,
        'new_training_updates':0,'actual_board_actions':0,'new_independent_test':False,'new_identity_accuracy_proven':False,
        'photometric_candidates_adopted_for_deployment':False,'whole_goal_complete':False,'all_own_launched_jobs_terminal':True}
    for key,value in photometric_expectations.items():assert photometric_final[key]==value,(key,photometric_final[key],value)
    for relative,digest in photometric_final['evidence_hashes'].items():assert sha(photometric_root/relative)==digest,relative
    for row in photometric_final['documents']:assert sha(Path(row['path']))==row['sha256']
    visual=json.loads((photometric_root/'results/visual_review.json').read_text(encoding='utf-8'))
    for row in visual['files']:assert row['actually_viewed'] and sha(Path(row['path']))==row['sha256']
    coverage_and_pair_expectations={
        'training_coverage_20261030':('TRAIN_ONLY6809_NATIVE_IMAGES8888_REGIONS213_ACTUAL_LOADER_BATCHES_AND28_PANELS_REVIEWED',
            {'native_train_images':6809,'native_body_regions':8888,'native_Y_le80':5899,'native_low_background_contrast_le15':3707,
             'real_loader_delivered_batches':213,'real_loader_delivered_images':6809,'real_augmented_AABB_rows':20292,
             'augmented_shortside_lt24':5466,'augmented_shortside_lt16':1949,'actual_RGB_controls':96,
             'source_XML_near_duplicate_flags':1,'labels_removed_or_modified':0,'independent_occlusion_or_coat_color_GT_created':False,
             'SVG_histogram_bars_checked':108,'figures_actually_viewed':3,'panels_actually_viewed':28,
             'loader_replayed_after_failure':False,'unpersisted_runtime_metadata_fabricated':False,
             'validation_holdout_or_video_pixels_in_coverage_audit':0,'new_model_forwards_in_coverage_audit':0,'new_training_updates':0,
             'actual_board_actions':0,'whole_goal_complete':False}),
        'mosaic_pair_20261030':('SIX_PAIRED_TRAININGS25350_REPLAYS36_EVENT_PATHS_AND12_VISUAL_PANELS_REVIEWED',
            {'formal_training_runs':6,'formal_training_updates':7350,'discarded_smoke_updates':4,'persisted_training_batch_rows':12780,
             'persisted_gradient_gate_rows':7350,'training_image_presentations':408540,'raw_full_gradient_arrays_saved':False,
             'paired_rotation_and_optimizer_schedules_exact':3,'all3_mosaic100_state_dicts_reproduced':True,'reproduced_parameter_and_buffer_tensors':2124,
             'post_training_source_label_files_unchanged':8380,'actual_evaluation_source_image_forwards':25350,'actual_inference_hook_image_calls':25350,
             'old_baseline_traces_exact':9,'validation_matching_problems':9426,'counter_paths':36,'publisher_temporal_matching_paths':24,
             'NN_anchor_hashes_checked':48,'original_counts_by_condition_order':[10,10,10,10,10,11],
             'Toros5Hz_TP_by_condition_order':[1,3,1,3,0,0],'Toros30Hz_TP_by_condition_order':[1,4,3,4,1,1],
             'validation_TP_by_condition_order':[1819,1838,1810,1813,1851,1831],
             'primary_retained_for_quantization':'mosaic050_seed26',
             'primary_checkpoint_sha256':'628db893fa8be090df206b32c35d8b81839eab2f497925ccbd0c6d855ad9d3eb',
             'new_candidate_quantized_or_executed_on_board':False,'prior_deployed_candidate_replaced':False,
             'first_failed_evaluation_new_source_forwards':0,'strict_regression_metadata_repair_only':True,
             'all6_training_main_jobs_completed':True,'all_training_stderr_clean':False,'pin_memory_exception_headers_after_complete_record':2,
             'pin_memory_exception_root_cause_confirmed':False,'all_launched_phase_jobs_terminal':True,
             'strict_decoded_video_frames':1962,'figures_actually_viewed':5,'panels_actually_viewed':12,
             'new_independent_test':False,'actual_board_actions':0,'whole_goal_complete':False})}
    coverage_and_pair_studies={}
    for phase,(status,expectations) in coverage_and_pair_expectations.items():
        directory=PROJECT/phase;final=json.loads((directory/'results/final_review.json').read_text(encoding='utf-8'))
        assert final['status']==status
        for key,value in expectations.items():assert final[key]==value,(phase,key,final[key],value)
        for relative,digest in final['evidence_hashes'].items():assert sha(directory/relative)==digest,(phase,relative)
        for row in final['documents']:assert sha(Path(row['path']))==row['sha256']
        visual=json.loads((directory/'results/visual_review.json').read_text(encoding='utf-8'))
        for row in visual['files']:assert row['actually_viewed'] and sha(Path(row['path']))==row['sha256']
        coverage_and_pair_studies[phase]={'status':status,**expectations}
    new_mosaic_board_expectations={
        'pynq_mosaic192_compile_20261030':('FIXED_MOSAIC050192_PTQ_COMPILE_AND8_REAL_O8_TRAIN_VECTORS_REVIEWED',
            {'checkpoint_sha256':'628db893fa8be090df206b32c35d8b81839eab2f497925ccbd0c6d855ad9d3eb',
             'actual_train_calibration_images':128,'all_calibration_tensor_hashes_exact_to_old':True,'compiler_workspace_original_files_unchanged':60,
             'primary_ordered_native_legacy_vectors_byte_exact':8,'actual_board_formal_vectors':8,'actual_board_warmups':2,
             'actual_board_raw_arrays_byte_exact':8,'mean_training_vector_tensor_to_raw_ms':140.31615075,
             'class_LUT_codes_scalar_checked':768,'static_tensor_entries_parsed':2132,'static_program_nodes_parsed':383,
             'board_worker_terminal_and_absent':True,'new_bitstream_programming':False,'new_training_updates':0,
             'new_model_full_video_or_joint5FPS_proven':False,'whole_goal_complete':False}),
        'pynq_mosaic192_eval_20261030':('MOSAIC050192_QUALITY2654_REAL_O8_VIDEO_FORWARDS6_ARM_COUNTER_PATHS_AND16_PANELS_REVIEWED',
            {'checkpoint_sha256':'628db893fa8be090df206b32c35d8b81839eab2f497925ccbd0c6d855ad9d3eb',
             'real_ORT_quality_forwards':8450,'native_integer_video_anchor_forwards':8,'actual_O8_video_forwards':2654,'actual_O8_warmups':2,
             'validation_FP32_QDQ_matched_references':[1838,1839],'FP32_QDQ_actual_O8_original_counts':[10,10,10],
             'actual_O8_Toros5Hz_TP_FP_FN':[3,0,3],'actual_O8_Toros30Hz_TP_FP_FN':[4,0,2],
             'actual8_video_anchor_raw_bytes_exact':True,'QDQ_ORT_equals_actual_O8_raw':False,'QDQ_different_raw_frame_rows':2654,
             'actual_ARM_counter_observation_ticks':2734,'actual_ARM_counter_paths':6,'mean_PNG_to_counter_ms':179.79121297626224,
             'P95_PNG_to_counter_ms':220.96877844999997,'processing_over200ms_frames':193,'strict_decoded_video_frames':1962,
             'SVG_bars_checked':19,'figures_actually_viewed':5,'panels_actually_viewed':16,'all_input_PNG_tensors_verified':2654,
             'actual_board_process_terminal_and_absent':True,'SSH_launch_timeout_not_restarted':True,'new_training_updates':0,'new_independent_test':False,
             'real_camera_or_RFID':False,'simultaneous_identity_in_this_record':False,'new_model_joint5FPS_proven_in_this_record':False,
             'prior_deployed_candidate_replaced':False,'whole_goal_complete':False}),
        'pynq_mosaic192_joint_20261030':('NEW_MOSAIC192_SIX_REAL_PERIODIC_RUNS_ALL_RAW_PHOTOS_AND_RETRIEVALS_REVIEWED',
            {'checkpoint_sha256':'628db893fa8be090df206b32c35d8b81839eab2f497925ccbd0c6d855ad9d3eb',
             'actual_O8_qualification_forwards':8,'actual_O8_warmups':12,'counter_paths':12,'identity_warmups':4,
             'all_actual_O8_raws_exact_to_same_model_full_video':True,'all_runtime_photos_inputs_features_and_reject_decisions_reconstructed':True,
             'new_model_input_quantization_256_codes_rechecked':True,'input_quantization_recheck_after_launch_disclosed':True,
             'both_real_networks_run_on_same_PYNQ':True,'same_source_repeats_are_independent_farm_sessions':False,
             'real_camera_or_RFID_hardware':False,'new_permanent_identity_accuracy_proven':False,
             'parent_and_four_identity_workers_terminal_absent':True,'known_O8_and_SSH_Jupyter_read_after_experiment':True,
             'prior_deployed_candidate_replaced':False,'new_training_updates':0,'new_independent_test':False,'whole_goal_complete':False})}
    new_mosaic_board_studies={}
    for phase,(status,expectations) in new_mosaic_board_expectations.items():
        directory=PROJECT/phase;final=json.loads((directory/'results/final_review.json').read_text(encoding='utf-8'))
        assert final['status']==status
        for key,value in expectations.items():assert final[key]==value,(phase,key,final[key],value)
        for relative,digest in final['evidence_hashes'].items():assert sha(directory/relative)==digest,(phase,relative)
        for row in final['documents']:assert sha(Path(row['path']))==row['sha256']
        visual_file=directory/'results/visual_review.json'
        if visual_file.exists():
            visual=json.loads(visual_file.read_text(encoding='utf-8'))
            for row in visual['files']:assert row['actually_viewed'] and sha(Path(row['path']))==row['sha256']
        if phase.endswith('joint_20261030'):
            raw=json.loads((directory/'results/independent_verification.json').read_text(encoding='utf-8'))
            assert len(raw['cases'])==6 and final['actual_O8_timed_forwards']==sum(r['processed_frames'] for r in raw['cases'])
            assert final['actual_background_identity_jobs']==sum(r['actual_background_jobs'] for r in raw['cases'])
            assert final['case_processed_frames']==[r['processed_frames'] for r in raw['cases']]
            assert final['case_skips']==[r['skipped_slots'] for r in raw['cases']]
            assert final['case_deadline_misses']==[r['deadline_misses'] for r in raw['cases']]
            assert final['case_source_down_counts']==[r['source_down_count'] for r in raw['cases']]
            assert final['case_throughput_FPS']==[r['processed_per_second_over_offered_duration'] for r in raw['cases']]
            assert all(r['source_down_count']==10 for r in raw['cases'])
            assert final['actual_photo_panels_viewed']==final['actual_background_identity_jobs']
            expectations={**expectations,**{key:final[key] for key in ['actual_O8_timed_forwards','actual_background_identity_jobs','case_processed_frames','case_skips','case_deadline_misses','case_throughput_FPS','case_source_down_counts']}}
        new_mosaic_board_studies[phase]={'status':status,**expectations}
    confirmation_expectations={
        'mosaic_event_diagnosis_20261030':('TWO_REAL_O8_MODELS4_CASES2324_REFERENCE_ROWS12_PATHS_AND9_NATIVE_INPUT_PANELS_REVIEWED',
            {'actual_counter_replay_counts':[11,10],'human_total12_still_not_met':True,'analysis_cases':4,'reference_rows':2324,
             'association_problems':2864,'reference_conditioned_counter_paths':12,'reference_is_independent_GT':False,
             'old_unmatched_development_tracks':[94],'new_unmatched_development_tracks':[94,103],
             'reference103_new_raw_entry_longest':3,'reference103_new_post_plus_legal_prior_entry_longest':2,
             'native_source_frames_checked':3,'actual_192_input_pairs_byte_equal':3,'panels_actually_viewed':9,
             'new_model_forwards':0,'new_training_updates':0,'actual_board_actions':0,'global_counter_or_tracker_changed':False,'whole_goal_complete':False}),
        'unconfirmed_iou_20261030':('111_CACHE_UNCONFIRMED_IOU_CONTROL444_PATHS_AND_SINGLE_FRAME_CAUSAL_DIAGNOSIS_REVIEWED',
            {'cache_conditions':111,'tracker_conditions':222,'counter_paths':444,'recorded_counter_observation_ticks':217078,
             'scope_metric_rows':476,'formal_existing_publisher_score_rows':272,'native_score_appendix_rows':8,
             'paired_scope_rows':238,'changed_scope_rows':38,'baseline_traces_reused_no_rerun':91,'all111_baselines_before_control':True,
             'original_hardware_Toros_sampler_order_reproduced':True,'ID_relabeling_or_event_gate_relaxation':False,
             'new_O8_cache_original_counts':[10,11],'old_O8_cache_original_counts':[11,11],'native_confirmed12_counts':[12,12],
             'new_O8_5Hz_TP_before_after':[3,3],'new_O8_30Hz_TP_before_after':[4,3],'new_FP32_5Hz_TP_before_after':[3,2],
             'single_frame_diagnostic_before_after':[10,11],'all_pre9550_states_exact_in_single_frame_diagnostic':True,
             'single_frame_special_case_is_deployment_rule':False,'frame9550_actual_pure_IoU_cost':0.21052730083465576,
             'frame9550_actual_fused_cost':0.7721717953681946,'reference_is_independent_GT':False,'new_model_forwards':0,
             'new_training_updates':0,'actual_board_actions':0,'production_tracker_or_counter_files_changed':False,
             'control_adopted_for_deployment':False,'new_independent_test':False,'all_own_launched_jobs_terminal':True,'whole_goal_complete':False})}
    confirmation_studies={}
    for phase,(status,expectations) in confirmation_expectations.items():
        directory=PROJECT/phase;final=json.loads((directory/'results/final_review.json').read_text(encoding='utf-8'))
        assert final['status']==status
        for key,value in expectations.items():assert final[key]==value,(phase,key,final[key],value)
        for relative,digest in final['evidence_hashes'].items():assert sha(directory/relative)==digest,(phase,relative)
        for row in final['documents']:assert sha(Path(row['path']))==row['sha256']
        if phase.startswith('mosaic_event'):
            visual=json.loads((directory/'results/visual_review.json').read_text(encoding='utf-8'))
            assert visual['actually_viewed'] and sha(Path(visual['actual_image_file']))==visual['actual_image_sha256']
        confirmation_studies[phase]={'status':status,**expectations}
    directory=PROJECT/'causal_photo_20261030'
    causal_photo=json.loads((directory/'results/final_review.json').read_text(encoding='utf-8'))
    assert causal_photo['status']=='FROZEN_CAUSAL_PHOTO_SIX_REAL_RUNS2309_O8_RAW39_ARM_PHOTOS69_TORCH_REFERENCES_AND_NONADOPTION_REVIEWED'
    causal_expectations={'actual_O8_timed_forwards':2309,'actual_O8_qualification_forwards':8,'actual_O8_warmups':12,
        'actual_identity_ARM_query_forwards':39,'actual_identity_ARM_warmups':4,
        'case_processed_frames':[392,391,379,376,381,390],'case_source_down_counts':[10,10,10,10,9,9],
        'case_skips':[0,1,13,16,11,2],'case_deadline_misses':[24,20,253,281,24,41],
        'counter_paths':12,'counter_observation_ticks_with_history':13007,'pause_windows_verified':1527,
        'all_actual_raws_byte_exact_to_prior_full_same_model_O8':True,'readonly_photo_pairs':10,'readonly_candidate_observations':60,
        'readonly_panels_viewed':20,'actual_ARM_panels_viewed':39,'actual_selection_candidate_observations':230,
        'fresh_Torch_query_forwards':39,'fresh_Torch_gallery_forwards':30,'fresh_Torch_retrieval_conditions':78,
        'source_and_Torch_input_tensors_exact':True,'all_actual_photos_features_scores_and_reject_decisions_verified':True,
        'exact_event_key_pairs':7,'unmatched_condition_records_retained':25,'accepted_predictions_in_each_background':[1,1,1,1],
        'all4_accepts_same_f9790_pixels_not4_animals':True,'causal_ring_policies_adopted':False,'production_tracker_or_counter_changed':False,
        'posthoc_counter_deletion_probe_counts':[10,9,10,9,9],'counter_probe_is_full_tracker_rerun':False,'single_frame_special_case_deployed':False,
        'steady6_JPEG_payload_peak_bytes':4418520,'transient7_JPEG_payload_peak_bytes':5149692,'JPEG_payload_claimed_total_memory':False,
        'inherited_model_and_quant_metadata_clarified_without_mutating_run':True,'asynchronous_queue_copy_scope_disclosed':True,
        'parent_four_workers_collector_terminal_absent':True,'server_job130642_completed0_0':True,'known_O8_and_services_retained':True,
        'new_training_updates':0,'new_independent_test':False,'real_camera_or_RFID':False,'permanent_identity_accuracy_proven':False,'whole_goal_complete':False}
    for key,value in causal_expectations.items():assert causal_photo[key]==value,(key,causal_photo[key],value)
    for mapping in ['evidence_hashes','code_hashes']:
        for relative,digest in causal_photo[mapping].items():assert sha(directory/relative)==digest
    for row in causal_photo['documents']:assert sha(Path(row['path']))==row['sha256']
    for name in ['actual_visual_review.json','readonly_visual_review.json']:
        visual=json.loads((directory/'results'/name).read_text(encoding='utf-8'));assert visual['actually_viewed']
        for row in visual['files']:assert sha(Path(row['file']))==row['sha256']
    directory=PROJECT/'input_cost_20261030'
    input_cost=json.loads((directory/'results/final_review.json').read_text(encoding='utf-8'))
    assert input_cost['status']=='INPUT_COST256_READS138_REAL_O8_FORWARDS_FILE_RESIDENCY_DEVICE_STATS_AND_NONADOPTION_REVIEWED'
    input_cost_expectations={'source_images':16,'read_cases':256,'groups':8,'conditions_per_group':32,
        'actual_O8_measured_forwards':128,'actual_O8_qualification_forwards':8,'actual_O8_warmups':2,
        'failed_v1_read_cases':0,'failed_v1_all_model_forwards':0,'process_IO_counter_absent_preserved':True,
        'file_mincore_and_device_stats_verified':True,'cold_cases_with_nonresident_pages_and_positive_device_read_delta':128,
        'hot_cases_all_pages_resident_and_zero_device_read_delta':128,'all16_raws_byte_exact_to_prior_actual_same_model':True,
        'all128_raw_hashes_verified':True,'whole_device_bytes_claimed_process_bytes':False,'full_periodic_target_still_RED':True,
        'microbenchmark_is_full_pipeline_performance':False,'new_periodic_counter_or_identity_run':False,'new_policy_adopted':False,
        'immutable_copy_and_pickle_scope_disclosed':True,'global_cache_or_swap_changed':False,'parent_processes_terminal_absent':True,
        'original_O8_and_services_retained':True,'new_training_updates':0,'new_independent_test':False,'whole_goal_complete':False}
    for key,value in input_cost_expectations.items():assert input_cost[key]==value,(key,input_cost[key],value)
    for relative,digest in input_cost['evidence_hashes'].items():assert sha(directory/relative)==digest
    for row in input_cost['documents']:assert sha(Path(row['path']))==row['sha256']
    directory=PROJECT/'async_highres_20261030'
    async_highres=json.loads((directory/'results/final_review.json').read_text(encoding='utf-8'))
    assert async_highres['status']=='ASYNC_HIGHRES4_REAL_RUNS1465_RAW784_RELEASED_SOURCE_READS40_ARM70_TORCH_AND_NONADOPTION_REVIEWED'
    async_expectations={'actual_O8_timed_forwards':1465,'actual_O8_qualification_forwards':8,'actual_O8_warmups':8,
        'actual_ARM_identity_queries':40,'actual_ARM_identity_warmups':4,'case_processed_frames':[354,378,385,348],
        'case_skips':[38,14,7,44],'case_deadline_misses':[353,170,363,347],'case_source_down_counts':[10,10,10,10],
        'counter_observation_ticks_with_history':8597,'counter_paths':8,'worker_pause_windows':1465,'all_complete_O8_raw_byte_equal_to_prior_same_model':True,
        'released_producer_source_records':784,'foreground_received_packets':1465,'actual_positive_model_IO_overlap_cases':580,
        'all_timed_producer_reads_after_release':True,'preflight_integrity_reads_kernel_cache_scope_disclosed':True,
        'producer_behavior_tests_both_Windows_and_board_pass':True,'bounded_buffer_payload_not_total_system_memory':True,
        'actual_photos_and_all40_panels_verified_viewed':True,'accepted_predictions_per_background':[0,1,1,0],
        'both_accepts_same_f9790_pixels_not2_verified_cows':True,'literal_event_key_pairs':6,'unmatched_condition_records_retained':28,
        'fresh_Torch_query_forwards':40,'fresh_Torch_gallery_forwards':30,'fresh_Torch_retrieval_conditions':80,'all_Torch_input_tensors_byte_exact':True,
        'CRLF_first_submission_rejected_before_compute':True,'only_submission_line_endings_repaired':True,'reference_job130643_completed0_0':True,
        'board_parent_four_workers_reader_threads_collector_terminal_absent':True,'original_O8_and_services_retained':True,
        'prototype_kept_as_research_candidate':True,'global_default_changed':False,'stable5FPS_or_identity_accuracy_proven':False,
        'real_camera_or_RFID':False,'new_training_updates':0,'new_independent_test':False,'whole_goal_complete':False}
    for key,value in async_expectations.items():assert async_highres[key]==value,(key,async_highres[key],value)
    for mapping in ['evidence_hashes','code_hashes']:
        for relative,digest in async_highres[mapping].items():assert sha(directory/relative)==digest
    for row in async_highres['documents']:assert sha(Path(row['path']))==row['sha256']
    visual=json.loads((directory/'results/visual_review.json').read_text(encoding='utf-8'));assert visual['actually_viewed'] and visual['panels']==40
    for row in visual['files']:assert row['actually_viewed'] and sha(Path(row['file']))==row['sha256']
    directory=PROJECT/'backend_service_20261030'
    backend=json.loads((directory/'results/final_review.json').read_text(encoding='utf-8'))
    assert backend['status']=='BACKEND_SERVICE4_REAL_RUNS1466_RAW39_PHOTOS69_TORCH_SERIAL_RECOVERY_REVIEWED_FULL_ARCHIVE_LOCAL_PENDING'
    backend_expectations={'actual_O8_timed_forwards':1466,'actual_O8_qualification_forwards':8,'actual_O8_warmups':8,
        'actual_ARM_identity_queries':39,'actual_ARM_identity_warmups':4,'fresh_Torch_query_forwards':39,'fresh_Torch_gallery_forwards':30,
        'fresh_Torch_retrieval_conditions':78,'reference_job130717_completed0_0':True,'case_processed_frames':[378,362,335,391],
        'case_skips':[14,30,57,1],'case_deadline_misses':[191,177,304,187],'case_source_down_counts':[10,9,10,10],
        'counter_observation_ticks':8598,'counter_paths':8,'released_source_records':1568,'CPU_boundary_windows':1466,
        'CPU_positive_tick_windows':[0,48,46,0],'CPU_tick_sums':[0,857,975,0],'original_files_hash_verified_on_board':178,
        'complete_O8_raws_verified_on_board_and_hash_bound_locally':1466,'photo_pixels_and_input_tensors_verified':39,'actual_raw_features_hash_bound':39,
        'reconstructed_PNG_byte_identical':30,'remaining9_PNGs_pixels_equal_encoding_diff':True,'all39_photo_panels_viewed':True,
        'accepted_predictions_per_run':[1,1,0,1],'all3_accepts_same_f9790_not3_verified_cows':True,'literal_event_key_pairs':4,
        'unmatched_condition_records_retained':31,'same_preexisting_normalization_and_score_gates_used':True,'extra_byte_normalization_failure_preserved':True,
        'new_global_default_adopted':False,'stable5FPS_count12_or_identity_accuracy_proven':False,'full_original_archive_locally_downloaded':False,
        'full_original_archive_preserved_on_board':True,'raw_arrays_locally_downloaded':False,'UART_metadata_and_numeric_archives_hash_verified':True,
        'recovery_added_model_forwards':0,'recovery_reset_or_network_changes':False,'experiment_workers_collector_and_audit_PIDs_absent':True,
        'local_SSH_and_Jupyter_services_active':True,'ethernet_carrier':0,'external_SSH_and_Jupyter_access_recovered':False,
        'loaded_O8_checked_at_original_root_collection':True,'loaded_O8_rechecked_after_network_loss':False,'current_on_disk_bitfile_SHA_unchanged':True,
        'shared_accelerator_lock_available':True,'new_training_updates':0,'new_independent_test':False,'real_camera_or_RFID':False,'whole_goal_complete':False}
    for key,value in backend_expectations.items():assert backend[key]==value,(key,backend[key],value)
    for mapping in ['evidence_hashes','code_hashes']:
        for relative,digest in backend[mapping].items():assert sha(directory/relative)==digest
    for row in backend['documents']:assert sha(Path(row['path']))==row['sha256']
    visual=json.loads((directory/'results/visual_review.json').read_text(encoding='utf-8'));assert visual['actually_viewed'] and visual['panels']==39
    for row in visual['files']:assert row['actually_viewed'] and sha(Path(row['file']))==row['sha256']
    # The older backend final above is its historical pre-download snapshot.
    # Bind the later full-original recovery separately, without rewriting that record.
    followup=json.loads((directory/'results/full_archive_followup_review_v2.json').read_text(encoding='utf-8'))
    assert followup['status']=='FULL_ORIGINAL_ARCHIVE178_FILES1466_RAW39_PHOTOS_VECTORS_AND_CURRENT_LOADED_O8_FOLLOWUP_REVIEWED'
    full_archive_expectations={'full_original_archive_locally_downloaded':True,'manifest_files':178,
        'actual_raw_arrays_locally_checked':1466,'original_PNGs_and_NPZs_checked':39,
        'prior_recovery_matches_full_original':True,'earlier_frozen_reports_preserved':True,
        'loaded_O8_rechecked_after_network_loss':True,'ethernet_carrier':0,'external_board_network_recovered':False,
        'all_checked_task_PIDs_absent':True,'original_experimental_counts':[10,9,10,10],'global_default_changed':False,
        'new_model_forwards':0,'new_training_updates':0,'new_experiment_rerun':False,
        'index_output_collision_disclosed_without_changing_numeric_gate':True,'whole_goal_complete':False}
    for key,value in full_archive_expectations.items():assert followup[key]==value,(key,followup[key],value)
    for relative,digest in followup['evidence_hashes'].items():assert sha(directory/relative)==digest
    for row in followup['documents']:assert sha(Path(row['path']))==row['sha256']
    directory=PROJECT/'external_sources_20261030'
    source_intake=json.loads((directory/'results/final_review.json').read_text(encoding='utf-8'))
    assert source_intake['status']=='THREE_PUBLIC_SOURCE_INTAKES22_COLO_JSON504_TOP_IMAGES_AND8_TRAIN_PIXEL_QA_REVIEWED'
    source_intake_expectations={'COLO_annotation_JSONs':22,'unique_top_images':504,'publisher_top_test_images':50,
        'publisher_top_test_original_boxes':451,'zero_width_test_boxes':1,'positive_area_small_outside_test_boxes':15,
        'train_QA_images_actually_viewed':8,'train_QA_panels':16,'test50_pixels_requested':False,
        'new_model_forwards':0,'new_training_updates':0,'new_independent_passage_or_identity_GT_obtained':False,
        'AutoCattlogger_sample_videos_obtained':False,'CattleEyeView_data_obtained':False,
        'forms_submitted_or_messages_sent':False,'global_proxy_or_node_configuration_changed':False,
        'quantitative_model_evaluation_not_yet_admitted':True,'whole_goal_complete':False}
    for key,value in source_intake_expectations.items():assert source_intake[key]==value,(key,source_intake[key],value)
    for relative,digest in source_intake['evidence_hashes'].items():assert sha(directory/relative)==digest
    for row in source_intake['documents']:assert sha(Path(row['path']))==row['sha256']
    directory=PROJECT/'colo_eval_20261030'
    colo=json.loads((directory/'results/final_review.json').read_text(encoding='utf-8'))
    assert colo['status']=='COLO50_TEST_IMAGES9_FIXED_CONDITIONS450_CPU_FORWARDS72_COCO_RERUNS_AND66_PANELS_REVIEWED'
    colo_expectations={'Slurm_job130734_completed0_0':True,'test_images':50,'original_GT_boxes':451,'valid_GT_boxes':450,
        'quarantined_zero_area_annotation_ID':127,'fixed_model_size_conditions':9,'actual_source_image_forwards':450,
        'actual_network_calls':45,'warmup_forwards':0,'all_raw_frozen_before_scoring':True,
        'independent_fixed_image_rows_checked':900,'locally_rerun_COCO_metric_groups':72,'maximum_COCO_array_difference':0,
        'clipped_unclipped_12stats_sensitivity_max':0,'actual_visual_panels_viewed':66,
        'main_fixed_TP_FP_FN':[[7,2,443],[31,9,419],[63,10,387],[92,21,358],[116,38,334],[136,45,314],[86,5,364],[102,12,348],[137,31,313]],
        'new_training_updates':0,'new_board_forwards':0,'default_model_or_tracker_changed':False,
        'new_passage_or_permanent_identity_GT':False,'new_fixed_external_detection_evaluation':True,
        'existing_final_Cows_holdout_opened':False,'test_images_now_opened_but_not_used_for_training_or_method_selection':True,
        'download_partial_recovery_and_CRLF_source_gate_failures_preserved':True,'numeric_gate_not_relaxed':True,
        'server_runtime_not_claimed_PYNQ_FPS':True,'whole_goal_complete':False}
    for key,value in colo_expectations.items():assert colo[key]==value,(key,colo[key],value)
    for relative,digest in colo['evidence_hashes'].items():assert sha(directory/relative)==digest
    for row in colo['documents']:assert sha(Path(row['path']))==row['sha256']
    directory=PROJECT/'colo_error_diagnosis_20261030'
    diagnosis=json.loads((directory/'results/final_review.json').read_text(encoding='utf-8'))
    assert diagnosis['status']=='NINE_RETAINED_OUTPUT_ERROR_PARTITIONS4050_GT173_FP5400_CERTIFIED_MATCHINGS_AND13_NATIVE_CASES_REVIEWED'
    diagnosis_expectations={'conditions':9,'GT_condition_rows':4050,'FP_condition_rows':173,
        'independently_certified_maximum_matching_graphs':5400,'all9_fixed_conf0_20_matching_upper_bounds_equal_existing_TP':True,
        'new192_FN_partition_low001_to020_below001_no_geometry':[104,196,64],
        'new192_interior_TP_denominator':[28,186],'new192_border_TP_denominator':[58,264],
        'old_new192_common_lost_gained_GT_counts':[71,21,15],'actual_panels_viewed':13,'score_band_witnesses_independently_raw_checked':7,
        'object_scope_contract_written_no_automatic_relabeling':True,'all450_original_positive_GT_kept':True,
        'GT_oracle_reported_as_deployable_improvement':False,'new_model_forwards':0,'new_training_updates':0,'new_board_forwards':0,
        'new_independent_test_or_passage_identity_GT':False,'default_model_tracker_or_threshold_changed':False,'whole_goal_complete':False}
    for key,value in diagnosis_expectations.items():assert diagnosis[key]==value,(key,diagnosis[key],value)
    for relative,digest in diagnosis['evidence_hashes'].items():assert sha(directory/relative)==digest
    for row in diagnosis['documents']:assert sha(Path(row['path']))==row['sha256']
    directory=PROJECT/'cpu_partition_combined_20261030'
    affinity=json.loads((directory/'results/final_review.json').read_text(encoding='utf-8'))
    assert affinity['status']=='EIGHT_REAL_FIXED_JOB_O8_ARM_RUNS2963_RAW80_ORIGINAL_PHOTOS_COMPLETE_ARCHIVE_AND_NONADOPTION_REVIEWED'
    affinity_expectations={'actual_timed_O8_forwards':2963,'actual_O8_qualification_forwards':16,'actual_O8_warmups':16,
        'actual_ARM_identity_queries':80,'actual_ARM_identity_warmups':8,'new_Torch_reference_forwards':0,'all_new_actual_model_forwards':3083,
        'case_processed_frames':[356,357,353,357,391,383,374,392],'case_source_down_counts':[9,10,9,8,10,10,8,10],
        'case_deadline_misses':[356,357,353,357,58,67,64,68],'fixed_identity_jobs_per_case':10,'counter_observation_ticks':17227,'counter_paths':16,
        'all80_photo_pixels_inputs_and_four_vector_arrays_verified':True,'unique_photos_actually_viewed':10,'all80_occurrences_hash_bound':True,
        'same_fixed_job_pair_comparisons':40,'accepted_predictions':8,'all8_accepts_same_f9790_not8_verified_cows':True,
        'foreground_affinity_main_thread_and_publisher_scope_only_disclosed':True,'background_all_observed_threads_mask_checked':True,
        'posthoc_followup_and_cross_stage_drift_disclosed':True,'PNG_NPZ_evidence_IO_and_progress_overhead_scope_disclosed':True,
        'every_frame_highres_ring_not_in_this_control':True,'fixed_jobs_not_current_event_triggers':True,
        'small_input_receiver_readiness_framing_failure_preserved_and_same_receiver_continued':True,
        'additional_launch_quote_compile_failure_zero_model_forwards_preserved':True,
        'generic_collection_staging_status_contains_literal6_but_actual_member_count2_independently_checked':True,
        'full_original_archive_received_and337_files_verified':True,'UART195_blocks_and_full_SHA_verified':True,
        'UART_settings_restored_no_baud_or_reset':True,'all_experiment_workers_collectors_terminal_absent':True,
        'current_loaded_O8_rechecked':True,'shared_lock_available':True,'board_local_services_active':True,'ethernet_carrier':0,
        'external_board_network_recovered':False,'new_global_default_adopted':False,'fixed_background_CPU1_or_foreground_main_CPU0_adopted':False,
        'new_training_updates':0,'new_independent_test_or_identity_GT':False,'live_camera_or_RFID':False,
        'stable5FPS_and_count12_proven':False,'permanent_identity_accuracy_proven':False,'whole_goal_complete':False}
    for key,value in affinity_expectations.items():assert affinity[key]==value,(key,affinity[key],value)
    for relative,digest in affinity['evidence_hashes'].items():assert sha(PROJECT/relative)==digest
    for row in affinity['documents']+affinity['source_bindings']:assert sha(Path(row['path']))==row['sha256']
    directory=PROJECT/'cows2021_identity_intake_20261030'
    identity_intake=json.loads((directory/'results/final_review.json').read_text(encoding='utf-8'))
    assert identity_intake['status']=='COWS2021_IDENTITY8670_TEST181_NONEMPTY_IDS301_TRAIN_VIDEO435_TRACKLET_METADATA_AND_SCOPE_REVIEWED'
    identity_intake_expectations={'test_JPEG_members':8670,'nonempty_test_IDs':181,'live_test_ID_directories':182,
        'empty_publisher_ID179_JPEG_count':0,'README13784_vs_paper8670_test_scope_resolved':True,'Test_filename_formats':2,
        'train_JPEGs':23350,'train_video_directories':301,'train_tracklet_directories':435,
        'train_directory_numbers_claimed_permanent_identity':False,'exact_crop_detection_source_links':7931,
        'timestamp_only_candidate_links':16,'unresolved_crop_original_links':723,
        'cross_OpenCows_exact_filename_or_size_CRC_candidates':0,'physical_cross_dataset_ID_disjointness_proven':False,
        'new_image_pixels_read':0,'new_model_forwards':0,'new_training_updates':0,'reserved_date_pixels_opened':False,
        'current12_events_permanent_identity_GT_obtained':False,'next_cropped_identity_source_is_independent_full_pipeline_test':False,
        'whole_goal_complete':False}
    for key,value in identity_intake_expectations.items():assert identity_intake[key]==value,(key,identity_intake[key],value)
    for relative,digest in identity_intake['evidence_hashes'].items():assert sha(directory/relative)==digest
    for row in identity_intake['documents']:assert sha(Path(row['path']))==row['sha256']
    directory=PROJECT/'cows2021_identity_eval_20261030'
    identity_eval=json.loads((directory/'results/final_review.json').read_text(encoding='utf-8'))
    assert identity_eval['status']=='COWS2021_120_ID540_CROPS1080_CPU_FORWARDS_CROSS_DATE_OPEN_SET_AND_HIGH_ERROR_RESULTS_REVIEWED'
    identity_eval_expectations={'Slurm130743_completed0_0':True,'unique_crops':540,'publisher_IDs':120,
        'calibration_registered_unknown_IDs':[20,20],'evaluation_registered_unknown_IDs':[40,40],
        'calibration_model_image_forwards':360,'evaluation_model_image_forwards':720,'all_new_model_image_forwards':1080,
        'network_calls':90,'warmup_forwards':0,'all540_input_tensors_match_original_training_preprocess':True,
        'original750_identity_input_exact_pixel_overlap':0,'gallery_query_cross_ID_exact_pixel_duplicates':0,
        'both_thresholds_frozen_before_any_evaluation_forward':True,'calibration20_vs_evaluation40_gallery_IDs_scope_disclosed':True,
        'all4_conditions_C_W_U_unknown_FA':[[26,6,88,9],[37,11,72,20],[30,21,69,21],[30,21,69,20]],
        'known_query_denominator_each':120,'unknown_query_denominator_each':120,
        'all4_known_Top1_correct':[69,69,65,65],'all4_known_Top5_correct':[106,106,100,100],
        'identity_score_cells_independently_recomputed':24000,'evaluation_decisions_independently_recomputed':960,
        'bootstrap2000_by_publisher_ID_reproduced':True,'preselected_source_panels_viewed':12,'posthoc_retrieval_panels_viewed':11,
        'full_original35_manifest_files_received_verified':True,'single_TLS_EOF_only_same_image499_retried_original539_reused':True,
        'partial_transfer_extract_guard_stopped_before_any_extraction':True,'author_identity_crop_evaluation_now_exists':True,
        'current12_passage_permanent_ID_mapping_obtained':False,'independent_full_detector_count_ID_test':False,
        'physical_cross_dataset_identity_disjointness_claimed':False,'reserved2020_03_05_to2020_03_11_pixels_opened':False,
        'new_training_updates':0,'new_board_forwards':0,'new_deployment_threshold_or_model_adopted':False,'live_camera_or_RFID':False,
        'reliable_automatic_identity_recovery_proven':False,'whole_goal_complete':False}
    for key,value in identity_eval_expectations.items():assert identity_eval[key]==value,(key,identity_eval[key],value)
    for relative,digest in identity_eval['evidence_hashes'].items():assert sha(directory/relative)==digest
    for row in identity_eval['documents']:assert sha(Path(row['path']))==row['sha256']
    directory=PROJECT/'cows2021_identity_gallery_control_20261030'
    gallery_control=json.loads((directory/'results/final_review.json').read_text(encoding='utf-8'))
    assert gallery_control['status']=='POSTHOC20_VS40_ID_GALLERIES16_FIXED_CONTROLS2880_DECISIONS_AND_SCOPE_REVIEWED'
    gallery_control_expectations={'conditions':16,'query_decisions':2880,'independently_recomputed_ID_score_cells':86400,
        'score_monotonicity_pairs':720,'current_encoder_calibrated_FA_by_fold20_then40':[12,20,16,20],
        'unknown_queries_per_condition':120,'same_query_and_threshold_within_gallery_expansion':True,'both_folds_preserved':True,
        'posthoc_control_and_repeated_unknown_queries_disclosed':True,'new_model_forwards':0,'new_training_updates':0,
        'new_threshold_search':False,'new_independent_test':False,'new_deployment_policy_adopted':False,'whole_goal_complete':False}
    for key,value in gallery_control_expectations.items():assert gallery_control[key]==value,(key,gallery_control[key],value)
    for relative,digest in gallery_control['evidence_hashes'].items():assert sha(directory/relative)==digest
    for row in gallery_control['documents']:assert sha(Path(row['path']))==row['sha256']
    new_identity_chain = {}
    for phase, expectations in {
        'identity_domain_adapt_20261030': {
            'formal_optimizer_updates':1800,'formal_training_image_forwards':57600,
            'discarded_smoke_updates':2,'smoke_image_forwards':64,'evaluation_model_image_forwards':3780,
            'all_new_model_image_forwards':61444,'new_Cows_training_IDs':16,'new_Cows_training_images':457,
            'primary_C_domain_seed26_Top1_folds':[54,51],'primary_full40_Top1':99,
            'primary_full40_C_W_U_FA':[10,1,109,5],'future20_ID_pixels_opened':False,
            'reservedMar05toMar11_pixels_opened':False,'new_deployment_model_or_threshold_adopted':False,
            'reliable_automatic_ID_recovery_proven':False,'whole_goal_complete':False},
        'identity_rejection_scores_20261030': {
            'fixed_models':7,'score_methods':3,'calibrated_thresholds':21,'development_conditions':84,
            'independent_decisions':13860,'independent_ID_score_cells':360360,
            'primary_seed26_method_by_calibration':'absolute_cosine','primary_calibration_C_absolute_margin_ratio':[10,7,9],
            'primary_not_changed_by_development_outcomes':True,'new_model_forwards':0,
            'future20_ID_pixels_opened':False,'new_deployment_method_or_threshold_adopted':False,'whole_goal_complete':False},
        'identity_domain_ncnn_20261030': {
            'input_image_pairs':630,'measured_model_image_forwards':1260,'Python_trace_forward_calls':1,
            'converter_internal_probe_count_unknown_additional':True,'development_decisions':1260,
            'development_decision_changes':0,'calibration_decisions':240,'calibration_endpoint_accept_changes':1,
            'thresholds_recalibrated':False,'full_tensor_anchors':10,'manifest_files_verified':32,'whole_goal_complete':False},
        'identity_domain_arm_20261030': {
            'actual_ARM_measured_forwards':97,'actual_ARM_warmups':2,'new_PL_forwards':0,
            'independently_recomputed_source_and_tensor_hashes':97,'full_input_anchors':9,
            'independently_recomputed_decisions':120,'independent_full_Cows_accuracy':False,
            'concurrent_detector_5FPS_test':False,'default_encoder_or_O8_changed':False,'whole_goal_complete':False}
    }.items():
        directory=PROJECT/phase
        final=json.loads((directory/'results/final_review.json').read_text(encoding='utf-8'))
        for key,value in expectations.items():assert final[key]==value,(phase,key,final[key],value)
        for relative,digest in final.get('evidence_hashes',{}).items():assert sha(directory/relative)==digest
        for row in final.get('evidence',[]):assert sha(directory/row['file'])==row['sha256']
        for row in final.get('documents',[]):assert sha(Path(row['path']))==row['sha256']
        new_identity_chain[phase]=expectations
    pair_directory=PROJECT/'identity_joint_pair_20261030'
    identity_pair=json.loads((pair_directory/'results/final_review.json').read_text(encoding='utf-8'))
    pair_expectations={'actual_timed_O8_forwards':1564,'actual_O8_qualification_forwards':8,'actual_O8_warmups':8,
                       'actual_ARM_total_forwards':85,'all_new_actual_board_forwards':1665,
                       'photo_input_feature_score_jobs_verified':40,'same_photo_new_old_pairs':20,
                       'case_models':['old','new','new','old'],'new_training_updates':0,
                       'new_independent_test':False,'default_model_or_policy_changed':False,
                       'future20_ID_pixels_opened':False,'tracker_replay_all4_full_associations_pass':True,
                       'whole_goal_complete':False}
    for key,value in pair_expectations.items():assert identity_pair[key]==value,(key,identity_pair[key],value)
    for relative,digest in identity_pair['evidence_hashes'].items():assert sha(pair_directory/relative)==digest
    directory=PROJECT/'identity_final20_20261030'
    future_protocol=json.loads((directory/'results/pre_pixel_review.json').read_text(encoding='utf-8'))
    assert future_protocol['identity_final20_evaluation_executed']is False and future_protocol['final_ID_image_files_requested']==0
    assert future_protocol['independent_identity_score_cells_checked']==3600 and future_protocol['entire_project_unseen_pixels_claimed']is False
    for relative,digest in future_protocol['evidence_hashes'].items():assert sha(directory/relative)==digest
    final20=json.loads((directory/'results/final_review.json').read_text(encoding='utf-8'))
    final20_expectations={'registered_IDs':10,'unknown_IDs':10,'images':90,'actual_model_image_forwards':180,
        'actual_network_calls':16,'warmups':0,'new_training_updates':0,'new_board_forwards':0,
        'identity_score_cells':1200,'decisions':480,'per_ID_interval_sets':8,'paired_ID_contrasts':20,
        'primary_Top1_C_W_U_FA':[[22,10,2,18,3],[30,3,0,27,0]],'new_primary_accepted_query_images':3,
        'new_primary_accepted_publisher_IDs':2,'old_unknown_FA_query_images':3,'old_unknown_FA_publisher_IDs':1,
        'first_final_ID_pixels_requested_only_after_code_model_and_threshold_freeze':True,
        'calibration_primary_fold_not_changed_by_test':True,'heldout_IDs_now_seen_and_reuse_limits_disclosed':True,
        'full_project_or_crossfarm_unseen_pixel_claimed':False,'automatic_reliable_identity_recovery_proven':False,
        'default_model_or_threshold_changed':False,'board_identity_final90_evaluated':False,
        'source_visuals_viewed':8,'explanation_cases_viewed':23,'all_new_server_jobs_terminal':True,
        'reservedMar05toMar11_pixels_opened':False,'whole_goal_complete':False}
    for key,value in final20_expectations.items():assert final20[key]==value,(key,final20[key],value)
    for relative,digest in final20['evidence_hashes'].items():assert sha(directory/relative)==digest
    directory=PROJECT/'identity_final20_arm_20261030'
    final20_arm=json.loads((directory/'results/final_review.json').read_text(encoding='utf-8'))
    final20_arm_expectations={'actual_ARM_measured_forwards':180,'actual_ARM_warmup_forwards':4,'actual_ARM_network_calls':184,
        'source_JPEG_and_tensor_hashes_verified':90,'input_anchors_verified':6,'actual_raw_features_verified':180,
        'ID_score_cells_recomputed':1200,'retrieval_queries':120,'fixed_decisions':480,
        'numeric_failed_images':0,'Top1_changes':0,'Top5_order_changes':0,'decision_changes':0,
        'primary_Top1_C_W_U_FA':[[22,10,2,18,3],[30,3,0,27,0]],
        'same90_CPU_evaluation_not_new_independent_test':True,'thresholds_not_changed_for_hardware':True,
        'new_training_updates':0,'new_CPU_reference_forwards':0,'new_PL_forwards':0,
        'default_O8_encoder_tracker_or_reject_threshold_changed':False,'new_heldout_date_pixels_opened':False,
        'all_own_experiment_and_collection_PIDs_confirmed_absent':True,'concurrent_detector_or_full5FPS_test':False,'whole_goal_complete':False}
    for key,value in final20_arm_expectations.items():assert final20_arm[key]==value,(key,final20_arm[key],value)
    for relative,digest in final20_arm['evidence_hashes'].items():assert sha(directory/relative)==digest
    directory=PROJECT/'identity_trigger_pair_20261030'
    trigger_partial=json.loads((directory/'results/interruption_review_v1.json').read_text(encoding='utf-8'))
    trigger_partial_expectations={'observed_case_counts':[10,10,8],'observed_complete_case_summaries':3,
        'fourth_run_processed_lower_bound':350,'timed_O8_calls_observed_lower_bound':1451,
        'raw_outputs_or_photos_received':False,'fourth_case_terminal_received':False,
        'full_numeric_counter_or_identity_verification_complete':False,'source_original_experiment_restarted':False,
        'user_confirmed_power_or_connection_change':True,'recovery_code_AST_checked':True,
        'recovery_code_executed_on_board':False,'original_model_or_PL_reprogrammed_for_access_recovery':False,
        'new_model_forwards_by_review':0,'whole_goal_complete':False}
    for key,value in trigger_partial_expectations.items():assert trigger_partial[key]==value,(key,trigger_partial[key],value)
    for relative,digest in trigger_partial['evidence_hashes'].items():assert sha(directory/relative)==digest
    # The interruption record is a historical hash-bound observation; the
    # subsequently recovered complete original stage is checked below.
    assert trigger_partial['raw_outputs_or_photos_received']is False
    paper_review=json.loads((PROJECT/'paper_readiness_20261030/results/manuscript_review_v1.json').read_text(encoding='utf-8'))
    assert paper_review['numeric_table_rows_verified']==8 and not paper_review['ready_for_submission']
    assert paper_review['new_model_forwards']==0 and not paper_review['actual_trigger_originals_obtained']
    for row in paper_review['documents']+paper_review['method_sources_bound']+paper_review['result_sources_bound_and_hash_verified']+paper_review['tools']:
        assert sha(Path(row['file']))==row['sha256']
    directory=PROJECT/'independent_source_recheck_20261030'
    source_recheck=json.loads((directory/'results/final_review_v1.json').read_text(encoding='utf-8'))
    source_recheck_expected={'official_archive_entries':68350,'JPEG_entries':68334,'canonical_L_files':12172,
        'canonical_L_IDs':103,'L_dates':134,'metadata_conflict_groups':40,'byte_verified_conflict_groups':2,
        'CRC_only_remaining_groups':38,'actually_viewed_frozen_QA_images':8,'QA_only_IDs':['11','65','100'],
        'HTTP_response_records':31,'saved_response_bytes_including_failed_bodies':14561616,
        'strict_archive_range_responses':28,'source_archive_full_MD5_verified':False,'complete_archive_downloaded':False,
        'new_counting_GT_or_current12_identity_GT':False,'new_identity_scores':0,'new_training_updates':0,
        'new_model_forwards':0,'new_board_experiments':0,'board_results_recovered':False,
        'publisher_labels_changed':False,'Cows_reserved_date_pixels_opened':False,'BECA_entire_GT_certified':False,
        'network_configuration_changed':False,'whole_goal_complete':False}
    for key,value in source_recheck_expected.items():assert source_recheck[key]==value,(key,source_recheck[key],value)
    for relative,digest in source_recheck['evidence_hashes'].items():assert sha(directory/relative)==digest
    for row in source_recheck['documents']:assert sha(Path(row['path']))==row['sha256']
    directory=PROJECT/'beca_fixed_transfer_20261030'
    beca_transfer=json.loads((directory/'results/final_review.json').read_text(encoding='utf-8'))
    beca_transfer_expected={'source_images':90,'publisher_registered_IDs':10,'publisher_unknown_IDs':10,
        'model_image_forwards':180,'network_calls':16,'Slurm_job_id':'130909','Slurm_state':'COMPLETED','Slurm_exit':'0:0',
        'main_counts':[[14,13,15,2,26],[15,13,11,6,26]],'workpoints':8,'ID_score_cells':1200,
        'gallery_image_pair_cells':3600,'fixed_decisions':480,'stratified_ID_paired_contrasts':24,
        'actually_viewed_images':90,'actually_viewed_pages':10,'filename_camera_date_discrepancy_examples':2,
        'real_capture_dates_independently_verified':False,'selected_IDs_now_seen':True,
        'source_labels_independently_certified':False,'excluded_conflict_IDs':15,'excluded_seen_QA_IDs':3,
        'new_training_updates':0,'new_NCNN_reference_forwards':0,'new_board_forwards':0,
        'default_model_or_threshold_changed':False,'new_current12_identity_or_counting_GT':False,
        'actual_trigger_board_results_recovered':False,'Cows_reserved_date_pixels_opened':False,
        'ready_for_automatic_identity_deployment':False,'whole_goal_complete':False}
    for key,value in beca_transfer_expected.items():assert beca_transfer[key]==value,(key,beca_transfer[key],value)
    for relative,digest in beca_transfer['evidence_hashes'].items():assert sha(directory/relative)==digest
    for row in beca_transfer['documents']:assert sha(Path(row['path']))==row['sha256']
    directory=PROJECT/'beca_score_diagnosis_20261031'
    score_diag=json.loads((directory/'results/final_review.json').read_text(encoding='utf-8'))
    assert score_diag['threshold_states']==122 and score_diag['zero_W_FA_max_C']==[1,3]
    assert score_diag['new_model_forwards']==0 and not score_diag['deployment_threshold_selected']
    for relative,digest in score_diag['evidence_hashes'].items():assert sha(directory/relative)==digest
    for row in score_diag['documents']:assert sha(Path(row['path']))==row['sha256']
    paper_v2=json.loads((PROJECT/'paper_readiness_20261030/results/manuscript_review_v2.json').read_text(encoding='utf-8'))
    assert paper_v2['claims']==15 and not paper_v2['ready_for_submission'] and paper_v2['numeric_table_rows_verified']==10
    for row in paper_v2['documents']+paper_v2['source_files']+paper_v2['tools']:assert sha(Path(row['file']))==row['sha256']
    directory=PROJECT/'identity_trigger_pair_20261030'
    trigger_recovered=json.loads((directory/'results/final_review_recovered_v2.json').read_text(encoding='utf-8'))
    recovered_expected={'original_timed_O8_forwards':1464,'original_qualification_O8':8,'original_warmup_O8':8,
        'actual_background_jobs':35,'identity_warmups':4,'original_total_board_image_forwards':1519,
        'actual_counts':[10,10,8,7],'processed_frames':[363,374,364,363],'skipped_slots':[29,18,28,29],
        'deadline_misses':[273,124,285,208],'accepted_provisional':[1,0,0,0],
        'all4_original_terminal_and_raw_results_received':True,'raw_event_photo_numeric_verification_complete':True,
        'producer_records_verified':1568,'CPU_frame_windows_verified':1464,'full_tracker_observation_ticks':8596,
        'full_tracker_counter_paths':8,'Torch_reference_image_forwards':89,'unique_reference_model_inputs':29,
        'fixed_reference_decisions':116,'CPU_reference_job':'130923','preforward_failed_job':'130922',
        'literal_event_pairs':6,'unmatched_job_rows':23,'same_photo_pairs':3,'unique_photos_actually_viewed':26,
        'actual_photo_pages_viewed':5,'board_access_restored':True,'current_IP':'192.168.3.100','Jupyter_login_HTTP':200,
        'current23_bound_runtime_hashes_match':True,'current_loaded_O8_identity_claimed':False,
        'new_boot_before_collection':True,'new_board_forwards_by_recovery':0,'original_experiment_restarted':False,
        'new_training_updates':0,'current_source_passage_independent_GT_obtained':False,
        'current12_permanent_identity_GT_obtained':False,'full5FPS_target_achieved':False,
        'reliable_identity_recovery_proven':False,'actual_camera_RFID_proven':False,'power_failure_root_cause_proven':False,
        'whole_goal_complete':False}
    for key,value in recovered_expected.items():assert trigger_recovered[key]==value,(key,trigger_recovered[key],value)
    for relative,digest in trigger_recovered['evidence_hashes'].items():assert sha(directory/relative)==digest
    for row in trigger_recovered['documents']+trigger_recovered['access_evidence']:assert sha(Path(row['path']))==row['sha256']
    paper_v3=json.loads((PROJECT/'paper_readiness_20261030/results/manuscript_review_v3.json').read_text(encoding='utf-8'))
    assert paper_v3['numeric_table_rows_verified']==14 and paper_v3['pending_claims']==['C10','C11','C12']
    assert paper_v3['actual_trigger_originals_obtained']and not paper_v3['ready_for_submission']
    for row in paper_v3['documents']+paper_v3['source_files']+paper_v3['tools']:assert sha(Path(row['file']))==row['sha256']
    directory=PROJECT/'pynq_workload_ablation_20261031'
    workload=json.loads((directory/'results/final_review_v1.json').read_text(encoding='utf-8'))
    workload_expected={'task_status':'FAILED','planned_timed_cases':8,'completed_timed_cases':5,
        'sixth_prepared_period_unstarted':True,'last_two_cases_unstarted':True,
        'conditions':['A','B','C','D','D'],'actual_counts':[7,8,10,10,3],
        'processed_frames':[368,368,383,343,286],'skipped_slots':[24,24,9,49,106],
        'deadline_misses':[16,35,86,342,286],'actual_timed_O8_forwards':1748,
        'O8_qualification_forwards':8,'O8_warmups':12,'actual_identity_jobs':30,'identity_warmups':6,
        'all_actual_board_image_forwards':1804,'producer_records':1176,'frontend_receipts':997,
        'model_IO_overlapping_cases':765,'full_association_ticks':10663,'full_association_rows':2338,
        'counter_paths':10,'CPU_replay_job_id':'130931','new_CPU_model_reference_forwards':0,
        'threshold_accepts_repeated_same_photo':3,'original_failed_experiment_restarted':False,
        'first_five_not_a_complete_balanced_factorial':True,'full5FPS_target_achieved':False,
        'power_or_memory_or_IPC_root_cause_proven':False,'whole_goal_complete':False}
    for key,value in workload_expected.items():assert workload[key]==value,(key,workload[key],value)
    for name,digest in workload['evidence_hashes'].items():assert sha(directory/name)==digest
    for row in workload['documents']+workload['reviewed_tools']:assert sha(Path(row['path']))==row['sha256']
    directory=PROJECT/'pynq_startup_probe_20261031'
    startup_probe=json.loads((directory/'results/final_review_v1.json').read_text(encoding='utf-8'))
    assert startup_probe['actual_ARM_identity_warmups']==4 and startup_probe['actual_O8_image_forwards']==0
    assert startup_probe['source_import_only_variants_verified']and not startup_probe['original_40s_timeout_reproduced']
    assert startup_probe['parent_only_startup_s']==[2.362192845,2.366717514]
    assert startup_probe['two_sample_Pss_sum_savings_MiB']==[37.541015625,37.8671875]
    for name,digest in startup_probe['evidence_hashes'].items():assert sha(directory/name)==digest
    for row in startup_probe['documents']+startup_probe['reviewed_tools']:assert sha(Path(row['path']))==row['sha256']
    directory=PROJECT/'pynq_parent_only_workload_20261031'
    parent_only=json.loads((directory/'results/final_review_v1.json').read_text(encoding='utf-8'))
    parent_only_expected={'all8_complete':True,'actual_counts':[10,10,10,10,9,10,10,10],
        'processed_frames':[392,388,389,387,384,391,392,392],'skipped_slots':[0,4,3,5,8,1,0,0],
        'deadline_misses':[0,200,79,65,144,55,0,0],'actual_timed_O8_forwards':3115,
        'O8_qualification_forwards':8,'O8_warmups':16,'formal_identity_jobs':40,'identity_warmups':8,
        'all_actual_board_image_forwards':3187,'separate_startup_probe_warmups':4,'new_CPU_model_forwards':0,
        'producer_records':1568,'frontend_receipts':1551,'overlapping_model_IO_cases':1394,
        'full_association_ticks':17379,'full_association_rows':4162,'full_association_event_paths':16,
        'CPU_reference_job_id':'130932','accepted_same_fixed_photo_repeats':4,
        'drop_diagnosis_variants':9,'drop_diagnosis_observation_ticks':19519,'drop_diagnosis_event_paths':18,
        'single_backfill_9515_restores_model_reference10_not_human12':True,
        'same_boot_but_not_initial_overlay_cache_swap_matched_to_old_failed_trial':True,
        'original_failed_trial_restarted_or_overwritten':False,'original40s_timeout_root_cause_proven':False,
        'all_offered_slots_processed':False,'all_offered_200ms_deadlines_met':False,
        'human_total12_consistently_recovered':False,'independent_event_or_permanent_identity_GT_received':False,
        'real_camera_RFID_5FPS_proven':False,'whole_goal_complete':False}
    for key,value in parent_only_expected.items():assert parent_only[key]==value,(key,parent_only[key],value)
    for name,digest in parent_only['evidence_hashes'].items():assert sha(directory/name)==digest
    for row in parent_only['documents']+parent_only['reviewed_tools']:assert sha(Path(row['path']))==row['sha256']
    overview=json.loads((ROOT/'results/overview_review_20261031_v24_parent_only.json').read_text(encoding='utf-8'))
    assert sha(Path(overview['document']['path']))==overview['document']['sha256']
    for row in overview['current_numeric_record_files']:assert sha(Path(row['path']))==row['sha256']
    result = {'status': 'SYNTHESIS_LINKS_AUTHOR_BLOBS_AND_SELECTED_EVIDENCE_CHECKED',
              'created_UTC': datetime.now(timezone.utc).isoformat(),
              'documents': [{'path': str(p), 'sha256': sha(p)} for p in documents],
              'local_links_checked': len(links), 'captured_README_blobs': captured,
              'source_frame_interval_inclusive': [8912, 10873], 'frames': frames, 'duration_s': frames / 25,
              'QAT_evidence_sha256': sha(qat_path), 'formal_QAT_updates_in_original_failed_stage': 0, 'remaining_original_QAT_gate_failures': 1,
              'published_Cows2021_image_rows': 10402, 'published_rotated_annotations': 13165,
              'complete_source_result_exists': source_summary.exists(),
              'complete_source_verification_exists': source_verified.exists(),
              'complete_source_verification_and_hashes_rechecked': full_source_rechecked,
              'candidate_date_counts': date_counts,
              'author_weight_file_entries_and_HEAD_metadata_confirmed': confirmed_weight_files,
              'actual_completed_Cows_study_records_inspected': cows_study,
              'actual_orientation_diagnostic_records_inspected': orientation_study,
              'actual_video_rotation_records_inspected': video_study,
              'actual_integer_reference_records_inspected': integer_study,
              'actual_optimizer_causal_controls_inspected': optimizer_study,
              'actual_trainable_integer_smoke_inspected': trainable_study,
              'actual_six_epoch_paired_integer_QAT_inspected': paired_qat_study,
              'actual_frozen_identity_risk_diagnosis_inspected': risk_study,
              'actual_training_range_clipping_controls_inspected': range_study,
              'actual_independent_evaluation_intake_preparation_inspected': intake_study,
              'actual_user_steered_source_undercount_recovery_inspected': recovery_study,
              'actual_tracker_clock_controls_and_confirmation_case_probes_inspected': clock_study,
              'actual_confirmation_handoff_implementation_inspected': handoff_study,
              'actual_paired_event_intake_and_B_region_probe_inspected': paired_intake_study,
              'actual_secondstage_iou_single_factor_control_inspected': secondstage_study,
              'actual_lost_low_score_eligibility_control_inspected': lost_study,
              'actual_external_fixed_method_regression_and_overlap_case_inspected': external_study,
              'actual_duplicate_ID_readonly_audit_inspected': duplicate_study,
              'actual_MooTrack_native_video_GT_scale_and_admission_audit_inspected': mootrack_study,
              'actual_user_confirmed_clip_total_and_camera_scope_inspected': confirmed_total_study,
              'actual_four_ordinary_overhead_session_fixed_model_extension_inspected': overhead_study,
              'actual_long_ordinary_overhead_native_admission_and_positive_source_discovery_inspected': long_overhead_study,
              'actual_new_long_source_admission_and_assistant_event_reference_draft_inspected': positive_reference_study,
              'actual_native_pixel_conditional_event_timing_refinement_inspected': timing_study,
              'actual_four_frozen_model_native_long_video_replay_and_case_diagnosis_inspected': long_replay_study,
              'actual_native_gap_association_and_one_factor_firststage_control_inspected': gap_study,
              'actual_firststage_IOU_nine_source_regression_and_nonadoption_inspected': firststage_regression_study,
              'actual_confirmed12_native_capture_and_real_identity_query_chain_inspected': capture12_study,
              'actual_confirmed12_causal_RF_stream_real_fallback_and_pressure_controls_inspected': rf_stream12_study,
              'actual_published_identity_source_provenance_and_same_passage_evaluation_exclusion_inspected': identity_provenance_study,
              'actual_two_date_gallery_real_query_and_open_set_risk_intervention_inspected': crossdate_gallery_study,
              'actual_validation_frozen_crop_threshold_and_orientation_controls_inspected': crop_domain_study,
              'actual_native_detector_torso_pairs_input_scale_controls_and_training_route_inspected': torso_pair_study,
              'actual_user_192256320_baselines_and_unresolved_board_benchmark_inspected': lowres_board_study,
              'actual_fixed_lane_crop_lowres_input_and_nonadoption_inspected': lane_crop_study,
              'actual_recovered_PYNQ_board_three_size_latency_and_periodic_input_controls_inspected': recovered_board_study,
              'actual_cow_single_class_O8_compilation_and_real_FPGA_ARM_vector_qualification_inspected': cow_O8_compile_study,
              'actual_15_lowres_factor_seed_training_and_fixed_evaluation_nonadoption_inspected': lowres_factorial_study,
              'actual_lowres_raw_coverage_center_confirmation_oracles_and_native_case_pixels_inspected': lowres_event_audit_study,
              'actual_new15_fixed_lane_crop_39810_forwards_and_all54_visual_panels_inspected': new_lane_crop_study,
              'actual_preselected_rot192_new_weights_O8_eight_vector_qualification_only_inspected': rot192_vector_qualification,
              'actual_new_rot192_2654_real_O8_video_forwards_ARM_counting_and_quantization_quality_inspected': actual_rot192_video_study,
              'actual_torchfree_tracker_AST_and90_full_actual_ARM_regressions_inspected': numpy_tracker_port_study,
              'actual_ARM_identity_periodic_joint_idle_capture_encoding_remaining_case_and_same_O8_size_studies_inspected': actual_same_board_studies,
              'actual_fixed192_photometric_inputs_all25350_forwards36_event_paths_and_nonadoption_inspected': photometric_expectations,
              'actual_training_coverage_real_loader_and_six_mosaic_pair_training_evaluation_inspected':coverage_and_pair_studies,
              'actual_new_mosaic192_train_PTQ8_board_vectors2654_video_frames_and_six_real_joint_repeats_inspected':new_mosaic_board_studies,
              'actual_new_old_O8_event_comparison_and111_unconfirmed_stage_controls_nonadoption_inspected':confirmation_studies,
              'actual_causal_photo_six_board_runs39_ARM_queries69_Torch_references_and_nonadoption_inspected':causal_expectations,
              'actual_input_cost256_read_cases138_real_O8_forwards_file_residency_and_no_full_fix_claim_inspected':input_cost_expectations,
              'actual_async_input4_real_board_runs1465_raw784_released_reads40_ARM70_Torch_and_candidate_scope_inspected':async_expectations,
              'actual_backend_service4_runs1466_raw39_photos69_Torch_CPU_tradeoff_UART_recovery_and_original_archive_pending_inspected':backend_expectations,
              'latest_full_original_backend_archive_recovery_and_current_loaded_O8_followup_inspected':full_archive_expectations,
              'historical_pre_test_pixel_COLO_AutoCattlogger_CattleEyeView_source_intake_inspected':source_intake_expectations,
              'actual_COLO_test50_three_fixed_models_three_sizes450_FP32_CPU_forwards_and72_local_COCO_reruns_inspected':colo_expectations,
              'actual_retained_output9condition4050_GT173_FP5400_maximum_matching_certificates_and_object_contract_inspected':diagnosis_expectations,
              'actual_fixed10_photo_workload8_board_affinity_runs2963_O8_raw80_ARM_queries_full_archive_and_nonadoption_inspected':affinity_expectations,
              'actual_Cows2021_identity_metadata8670_test181_nonempty_IDs435_train_tracklets_and_detection_source_overlap_inspected':identity_intake_expectations,
              'actual_two_fixed_encoders540_crops1080_CPU_forwards_crossdate_known_unknown_errors_and_frozen_thresholds_inspected':identity_eval_expectations,
              'actual_posthoc_same_query20_vs40_ID_registry16controls2880_decisions_and_no_threshold_search_inspected':gallery_control_expectations,
              'actual_six_domain_training_pairs_rejection_calibration_NCNN_and_new_ARM_identity_chain_inspected':new_identity_chain,
              'actual_new_old_identity_pair4_real_O8_ARM_runs40_photos_and_full_association_replay_inspected':pair_expectations,
              'historical_final20_metadata_and_matched10ID_calibration_pixels_closed_at_prefreeze_verified':True,
              'actual_final20_fixed90_crops180_forwards480_decisions_low_auto_coverage_and_IDs_now_seen_inspected':final20_expectations,
              'actual_same90_inputs180_ARM_vectors480_decisions_and184_calls_full_originals_and_timing_scope_inspected':final20_arm_expectations,
              'partial_actual_trigger_stage3_observed_summaries_fourth_progress_access_loss_and_recovery_not_execution_verified':trigger_partial_expectations,
              'reviewed_paper_draft8_table_rows7_result_sources_and6_method_sources_not_submission_ready':{
                  'numeric_rows':paper_review['numeric_table_rows_verified'],'ready_for_submission':False,
                  'new_forwards':0,'actual_trigger_originals_obtained':False},
              'actual_new_BECA_migrated_archive_directory_texts_two_byte_proven_ID_conflicts_and8_QA_only_no_model_scores':source_recheck_expected,
              'completed_BECA_fixed20_transfer180_CPU_forwards_all480decisions_date_issues_and_negative_results':beca_transfer_expected,
              'posthoc_same_saved_scores122_states_zeroWFA_C1_C3_no_calibrated_or_deployed_threshold':{
                  'states':122,'zero_W_FA_max_C':[1,3],'new_model_forwards':0,'new_calibration':False},
              'paper_v2_with15claims_and10_numeric_rows_not_submission_ready':{
                  'claims':15,'numeric_rows':10,'ready_for_submission':False},
              'recovered_original_actual_trigger4runs1519board_forwards_and89CPU_references_full_archives':recovered_expected,
              'paper_v3_complete_original_trigger_evidence14rows_C09_supported_remaining3claims_pending':{
                  'numeric_rows':14,'actual_trigger_originals_obtained':True,'pending_claims':['C10','C11','C12'],'ready_for_submission':False},
              'actual_failed8_workload_plan5_complete_periods1804_board_forwards_full_references_and_preserved_failure':workload_expected,
              'four_startup_probes_known_ARM_warmups_import_only_variants_not_original40s_repro':{
                  'ARM_warmups':4,'O8_image_forwards':0,'parent_only_READY_s':[2.362192845,2.366717514],
                  'two_sequential_Pss_sum_savings_MiB':[37.541015625,37.8671875],
                  'original_40s_timeout_reproduced':False,'periodic5FPS_tested':False},
              'complete_parent_only_import8_workload3187_forwards_and_zero_neural_CPU_backfill_diagnosis':parent_only_expected,
              'scope': 'Links, exact captured author text, frame arithmetic, selected actual evidence; manual claim review remains necessary',
              'this_review_script_performs_model_training_or_forward': False,
              'Z2_joint_execution_verified': bool(actual_same_board_studies.get('pynq_periodic_joint_20261030')),
              'Z2_joint_execution_scope': 'Same-board actual O8 detector, ARM tracking/counting, runtime highres photo crop/preprocess, actual NCNN identity and retrieval on public replay with simulated noRFID; not independent identity accuracy or live camera/RFID or zero200mslate guarantee.',
              'main_paper_contribution_verified': False,
              'whole_goal_complete': False}
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    print(json.dumps({k: v for k, v in result.items() if k not in ['documents', 'captured_README_blobs']}), flush=True)


if __name__ == '__main__':
    main()
