"""Check manuscript numbers and local provenance; no model/data-pixel execution."""
from pathlib import Path
from datetime import datetime, timezone
from urllib.parse import unquote
from collections import Counter
import hashlib, json, math, re

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent

def read(p):
    return p.read_text(encoding="utf-8")

def load(p):
    return json.loads(read(p))

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def row(*cells):
    return "| " + " | ".join(map(str, cells)) + " |"

ledger = load(ROOT/"results/claim_ledger_v1.json")
sources = {}
for record in ledger["sources"]:
    p = Path(record["file"])
    assert sha(p) == record["sha256"], record
    sources[record["name"]] = load(p)
assert len(sources) == 7
assert len(ledger["claims"]) == 12
assert not ledger["ready_for_submission"] and not ledger["whole_goal_complete"]
assert ledger["new_model_forwards"] == 0
pending = {r["ID"]: r["status"] for r in ledger["claims"] if r["status"].startswith("pending")}
assert set(pending) == {"C09", "C10", "C11", "C12"}

method_paths = {
    "final_protocol": PROJECT/"identity_final20_20261030/protocol/run_v1.json",
    "final_execution": PROJECT/"identity_final20_20261030/protocol/execution_v1.json",
    "training_protocol": PROJECT/"identity_domain_adapt_20261030/protocol/run_v1.json",
    "joint_protocol": PROJECT/"identity_joint_pair_20261030/protocol/run_v1.json",
    "trigger_protocol": PROJECT/"identity_trigger_pair_20261030/protocol/run_v1.json",
    "paired_ID_differences": PROJECT/"identity_final20_20261030/delivery/results/evaluation/paired_ID_differences.json",
}
methods = {key: load(p) for key, p in method_paths.items()}
paper_path = ROOT/"论文方法与实验草稿.md"
paper = read(paper_path)
table_rows = set(paper.splitlines())
primary = [r for r in sources["identity_CPU"]["outcomes"] if r["policy"] == "primary_cal10_fold0"]
assert [r["model"] for r in primary] == ["old_C", "new_C_domain_seed26"]
for label, actual in zip(["原编码器", "新域编码器，种子26"], primary):
    assert actual["known_queries"] == actual["unknown_queries"] == 30
    assert actual["C"] + actual["W"] + actual["U"] == 30 and actual["M"] == 0
    assert row(label, *(actual[k] for k in ["known_Top1","known_Top5","C","W","U","unknown_FA"])) in table_rows
    assert repr(actual["threshold"]) in paper
arm = sources["identity_ARM"]
for label, model in [("原编码器","old_C"), ("新域编码器","new_C_domain_seed26")]:
    t = arm["timings"][model]
    assert row(label, t["images"], f'{t["network_mean_ms"]:.2f}', f'{t["network_P95_ms"]:.2f}') in table_rows
assert arm["actual_ARM_measured_forwards"] == 180
assert arm["actual_ARM_warmup_forwards"] == 4 and arm["fixed_decisions"] == 480
assert all(arm[k] == 0 for k in ["numeric_failed_images","Top1_changes","Top5_order_changes","full_ranking_changes","decision_changes"])
assert f'{arm["maximum_normalized_feature_error"]*1e6:.3f}×10⁻⁶' in paper
for key in ["JPEG_read_decode_preprocess_mean_ms", "JPEG_read_decode_preprocess_P95_ms"]:
    assert f"{arm[key]:.2f}" in paper

fixed = sources["fixed_workload"]["cases"]
assert len(fixed) == 4
for actual in fixed:
    label = "原" if actual["identity_model"] == "old" else "新"
    cells = [actual["run"], label, actual["processed_frames"], actual["skipped_slots"],
             actual["deadline_misses"], f'{actual["processed_per_second_over_offered_duration"]:.3f}',
             f'{actual["P95_release_to_count_ms"]:.2f}', actual["source_down_count"],
             f'{actual["maximum_identity_result_ms"]:.2f}']
    assert row(*cells) in table_rows, cells
    assert actual["processed_frames"] + actual["skipped_slots"] == 392
    assert actual["actual_background_jobs"] == 10
    assert actual["fixed_jobs_not_triggered_by_this_counter"]
    assert actual["processed_frames"]/78.4 == actual["processed_per_second_over_offered_duration"]
    assert actual["accepted_predictions"] == (1 if actual["identity_model"] == "old" else 0)
assert [c["identity_model"] for c in fixed] == ["old","new","new","old"]
assert all(c["source_down_count"] == 10 for c in fixed)
sizes = sources["detector_sizes"]
for key in ["s256_mean_tensor_to_raw_ms", "s320_mean_tensor_to_raw_ms"]:
    assert f"{sizes[key]:.2f}" in paper
assert sizes["s256_all8_over200ms"] and sizes["s320_all8_over200ms"]
assert sources["detector_video"]["FP32_QDQ_actual_O8_original_counts"] == [10,10,10]

final = methods["final_protocol"]
joint = methods["joint_protocol"]
trigger = methods["trigger_protocol"]
training = methods["training_protocol"]
assert final["gallery_IDs"] == 10 and final["references_per_ID"] == 3
assert final["known_queries"] == final["unknown_queries"] == 30 and final["image_count"] == 90
gallery_counts = Counter(r["identity"] for r in joint["identity_reference_images"][:30])
assert len(joint["registered_IDs"]) == len(gallery_counts) == 6 and sum(gallery_counts.values()) == 30
assert "10ID、每ID3张图" in paper and "6个注册ID、共30张图" in paper
assert joint["fixed_jobs_per_case"] == 10 and joint["jobs_decoupled_from_current_counter"]
assert not joint["actual_camera_or_RFID_hardware"] and joint["original_framebank_is_ready_lowres_replay"]
assert all(repr(joint[k]) in paper for k in ["fixed_identity_threshold", "secondary_Cows_threshold"])
assert joint["foreground_affinity"] == [0,1] and joint["background_NCNN_threads"] == 1 and joint["backend_nice_increment"] == 10
assert trigger["counter_kwargs"] == {"lower":0.4,"upper":0.6,"stable_samples":3,"maximum_gap_s":2.0}
assert trigger["selector"]["maximum_age_frames_at25fps"] == 25 and trigger["video"]["fps"] == 25
assert trigger["selector"]["maximum_compressed_JPEG_frames"] == 6
assert trigger["selector"]["edge_guard_px"] == 16 and not trigger["selector"]["uses_future_frames"]
assert trigger["source_frame0_first"] == 8915 and trigger["source_frame0_last"] == 10870
assert (10870-8915)//5+1 == trigger["offered_slots_per_case"] == 392
assert joint["video"]["human_down_total"] == 12
assert trigger["video"]["scope_start_frame0"] == 8912 and trigger["video"]["scope_end_exclusive"] == 10874
assert training["formal_updates_per_condition"]*sources["training"]["training_conditions"] == sources["training"]["formal_optimizer_updates"] == 1800
assert training["input_size"] == 224 and training["primary_seed_preselected"] == 26
assert training["learning_rate"] == training["weight_decay"] == 0.0001
assert len(training["Cows_training_IDs"]) == sources["training"]["new_Cows_training_IDs"] == 16
assert sources["training"]["new_Cows_training_images"] == 457
execution = methods["final_execution"]
assert execution["bootstrap_seed"] == 26030 and execution["bootstrap_draws"] == 2000
contrasts = [r for r in methods["paired_ID_differences"] if r["policy"] == "primary_cal10_fold0"]
top1 = next(r for r in contrasts if r["metric"] == "Top1")
coverage = next(r for r in contrasts if r["metric"] == "C")
assert f'{top1["mean_difference"]*100:.2f}个百分点' in paper
assert "13.33–43.33个百分点" in paper and "−50.00–0.00个百分点" in paper
assert math.isclose(top1["percentile95"][0], 0.13333333333333336)
assert math.isclose(top1["percentile95"][1], 0.4333333333333333)
assert coverage["percentile95"] == [-0.5,0.0]
partial = sources["actual_trigger_partial"]
assert not partial["original_results_archive_obtained"] and not partial["fourth_case_terminal_observed"]
assert not (PROJECT/"identity_trigger_pair_20261030/delivery").exists()

required_scope = ["尚未达到投稿状态","模拟无RF输入","未模拟逐帧相机取图","入队至身份结果最大值",
                  "独立逐事件参考","不同年份","父图可能已用于检测","回顾图库","待核验",
                  "上述20ID现已用于评分","复用","实际触发四轮曾启动"]
assert all(value in paper for value in required_scope)
assert paper.count(r"\[") == paper.count(r"\]") == 3
assert paper.count(r"\(") == paper.count(r"\)") == 0

review_text = """# 论文整理自审与当前状态

2026-10-30。已完整通读方法与实验草稿、12项主张对应表及五篇最接近原始文献的对照记录，并逐表对照已完成阶段的当前原始摘要及冻结协议。此为助手自审，不是独立人工事件审核或期刊同行评审。

自审修正了两处容易混淆的协议：Cows身份组件的10ID×3图库与通道回放的6ID/30图分别说明；Cows各自校准阈值与系统共用历史阈值分别说明。另补充已就绪低分辨率回放输入、固定10照片负载和实际计数触发负载的区别，将后台计时明确为入队至结果，并保留全部不利结果。

数字检查覆盖两行身份决定、两行ARM计时、四行系统时序、256/320预算、分组统计和方法参数。七份结果来源SHA保持一致，新增方法来源单独绑定。所有本地Markdown链接均检查存在；外链的网络可达性不由本脚本验证，文献实际读取范围见原始来源记录。数学式按Markdown源文件核对，未执行独立排版渲染。

论文状态为草稿：实际触发原始数据待取回；独立逐事件JSON和当前视频永久牛号仍缺；真实相机/RFID、功耗和长期运行未完成。当前证据不支持可靠掉标自动找回、稳定全链路5FPS或“首个”系统。后续优先按恢复方案只读取得SD卡原始结果，再做完整评分。

本阶段新增训练、模型前向、标签修改和设备运行均为0。没有替换模型或阈值，没有提交稿件。以上检查只证明本稿在所声明范围内与已有证据一致，整体研究目标保持进行中。[结构化自审](results/manuscript_review_v1.json)
"""
review_path = ROOT/"Review与当前状态.md"
assert not review_path.exists()
review_path.write_text(review_text, encoding="utf-8")
documents = [ROOT/n for n in ["计划与范围.md","论文主张与证据对应.md","论文方法与实验草稿.md","文献对照_原始来源.md","Review与当前状态.md"]]
local_links = []
external_links = set()
for doc in documents:
    content = read(doc)
    for target in re.findall(r"\[[^\]]+\]\((<[^>]+>|[^)]+)\)", content):
        target = target.strip("<>")
        if target.startswith(("http://","https://")):
            external_links.add(target)
            continue
        base = unquote(target.split("#",1)[0])
        if not base:
            continue
        path = Path(base)
        if not path.is_absolute():
            path = doc.parent/path
        if path.resolve() == ROOT/"results/manuscript_review_v1.json":
            continue
        assert path.exists(), (doc, target)
        local_links.append({"document":str(doc.resolve()),"target":str(path.resolve())})
out = ROOT/"results/manuscript_review_v1.json"
assert not out.exists()
result = {
    "status":"MANUSCRIPT_NUMBERS_PROTOCOLS_LOCAL_LINKS_AND_CLAIM_SCOPE_SELF_REVIEWED_DRAFT_ONLY",
    "created_UTC":datetime.now(timezone.utc).isoformat(),
    "reviewer_kind":"assistant_self_review_not_independent_human_or_peer_review",
    "full_manuscript_and_literature_note_manually_read":True,
    "numeric_table_rows_verified":8,
    "result_sources_bound_and_hash_verified":ledger["sources"],
    "method_sources_bound":[{"name":k,"file":str(p.resolve()),"sha256":sha(p)} for k,p in method_paths.items()],
    "gallery_ID_image_counts_in_system":dict(gallery_counts),
    "local_links_verified":len(local_links),
    "external_link_count":len(external_links),
    "external_network_accessibility_verified_by_this_script":False,
    "new_model_forwards":0,"new_training_updates":0,"new_board_experiments":0,
    "whole_goal_complete":False,"ready_for_submission":False,
    "actual_trigger_originals_obtained":False,
    "manual_scope_checks":required_scope,
    "documents":[{"file":str(p.resolve()),"sha256":sha(p)} for p in documents],
    "tools":[{"file":str(p.resolve()),"sha256":sha(p)} for p in sorted((ROOT/"tools").glob("*.py"))],
}
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({k:result[k] for k in ["status","numeric_table_rows_verified","local_links_verified","external_link_count","ready_for_submission","whole_goal_complete"]}))
