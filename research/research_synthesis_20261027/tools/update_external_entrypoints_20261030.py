from pathlib import Path
from datetime import datetime, timezone
import difflib
import hashlib
import json

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def link(relative, title):
    return f"[{title}](<{(PROJECT / relative).as_posix()}>)"


overview = PROJECT / "研究阶段总结_20261030.md"
previous = json.loads((ROOT / "results/overview_review_20261030_v10.json").read_text(encoding="utf-8"))
assert sha(overview) == previous["document"]["sha256"]
targets = [overview, PROJECT / "研究总览_从想法到论文.md", PROJECT / "研究进度.md",
           PROJECT / "phase3_diagnosis_20261026/方案与执行状态.md", ROOT / "Review与当前状态.md"]
snapshots = ROOT / "results/snapshots_full_archive_external_20261030"
snapshots.mkdir(exist_ok=False)
before = {}
records = []
for index, target in enumerate(targets):
    snapshot = snapshots / (str(index) + "_" + target.name)
    snapshot.write_bytes(target.read_bytes())
    before[target] = target.read_text(encoding="utf-8")
    records.append({"target": str(target), "before_snapshot": str(snapshot), "before_sha256": sha(snapshot)})
recovery = link("backend_service_20261030/完整归档恢复与复核补充_v2.md", "完整原包恢复补充")
intake = link("external_sources_20261030/公开俯视数据来源与准入结论.md", "公开来源准入快照")
colo = link("colo_eval_20261030/COLO三模型三尺寸外来源检测与下一步.md", "COLO三模型三尺寸评价")
current = (f"2026年10月30日最新：{recovery}已补齐20,018,871字节原包、178文件、1466原始输出和39份原PNG／特征；"
           "当前加载O8已用特权串口重查，网口carrier仍为0，未重跑旧实验。"
           f"{intake}之后已完成{colo}：官方50图／450有效框，三个固定模型×192／256／320，共450次离线CPU前向；"
           "新192在conf0.20下TP86／FP5／FN364、召回19.11%，旧192为92／21／358、20.44%，默认不变。"
           "全部72组COCO评分在本机复算差0，66面板已查看；这些是外来源图像检测，不是新通行GT、身份准确率或板端速度。"
           "独立事件／永久身份、稳定前后台性能及现场输入仍待补。")
text = before[overview]
old_conclusion = next(line for line in text.splitlines() if line.startswith("**当前结论："))
new_conclusion = ("**当前结论：检测、ARM计数和身体身份检索已在同一PYNQ-Z2运行；O8三尺寸均有实机记录。"
                  "新192实机原片10／人工12、反向3／6；持续后台约2秒完成身份任务，却降低前台吞吐。"
                  "完整原始归档现已取回。新增COLO50图检测评价显示低分辨率跨来源召回仍弱，新192为19.11%，默认未替换。"
                  "独立事件／永久身份、稳定5FPS与现场有效性仍未完成，论文贡献尚未证明。**")
assert text.count(old_conclusion) == 1
text = text.replace(old_conclusion, new_conclusion)
old_paragraph = next(line for line in text.splitlines() if line.startswith("最新完成[后台服务四次实机与串口恢复复核]"))
text = text.replace(old_paragraph, current)
old_sentence = "网口断开后以串口和板端只读审计恢复证据；原包留板待下载，不冒充完整归档完成。"
assert text.count(old_sentence) == 1
text = text.replace(old_sentence, f"网口断开后已通过串口取回完整原始包并本机复算，旧恢复报告按其历史状态保留；见{recovery}。")
needle = "| 256与320同O8 | 各8向量平均235.55／370.93ms | 尚不能据此承诺含输入／跟踪／后台的5FPS |"
assert text.count(needle) == 1
text = text.replace(needle, needle + "\n| 外来源俯视检测 | COLO官方50图／450有效框，9个固定条件 | 新192召回19.11%；无新增通行／永久身份GT |")
new_section = ("### 3.6 外来源俯视检测：9个固定条件\n\n"
               "COLO来源准入后，在首次打开测试像素前冻结三个既有模型与192／256／320输入、标签处理和评分。"
               "原451框保留，零宽ID127隔离，其余450框作裁边与原坐标敏感性对照；全部50图保留。"
               "本轮为450次Torch CPU前向、无训练或新板端运行。\n\n"
               "192输入下旧模型AP11.99%、TP92／FP21／FN358，新模型AP11.97%、86／5／364。"
               "新模型误检较少，召回20.44%→19.11%；尚无全面改善。320输入的新模型AP50较高，严格AP仍低于官方，"
               "因此不只报有利指标。这是同一套192训练权重改变测试输入，不是另外训练的256／320模型，也不是量化O8结果。\n\n"
               f"COLO图像含明显广角、饲喂边界牛与作者推断遮挡框；相机与标注对象差异需受控验证。"
               f"它不提供完整事件或永久身份。72组评分本机复算差0、66面板已查看；{colo}保留全部条件与失败记录。\n\n")
assert text.count("## 4. 数据还需要怎样补") == 1
text = text.replace("## 4. 数据还需要怎样补", new_section + "## 4. 数据还需要怎样补")
needle = "不一定要重新寻找另一个名字的数据集，但需要**独立于当前开发过程的新会话、事件参考和身份关系**。"
assert text.count(needle) == 1
text = text.replace(needle, needle + f"\n\n新增{intake}说明COLO适于外来源检测，AutoCattlogger样本直链当前404、CattleEyeView未取得数据。"
                    "COLO50测试图本次已用于固定评价；若后续据此改变方法，不能继续称其为未见最终测试。既有最终留出日期仍保持隔离。")
old_step = "2. 新旧实际通行差异及确认阶段单因素控制已完成，局部恢复1次但全局有回归，继续保留原规则。94的连续入口检测与103的确认损失分别验证，结合普通俯视新会话及独立参考，不通过换seed、帧号特判或向训练加入原片来追12。"
new_step = "2. 外来源固定检测评价已经完成，当前跨来源召回和标注对象差异仍明显；先统一躯干／整牛／边界牛的任务定义，再固定训练或检测控制协议。COLO测试不作调参集；94的检测缺口和103的确认损失分别保留，不用换seed或帧号特判追12。"
assert text.count(old_step) == 1
text = text.replace(old_step, new_step)
old_status = next(line for line in text.splitlines() if line.startswith("同板部署已有真实记录。最新四次后台对照"))
new_status = ("同板部署已有真实记录。最新四次后台对照及恢复任务均终态；完整20MB原包已取回、178文件清单通过，"
              "1466原始raw、39原PNG／NPZ与此前恢复结果一致。特权串口再次确认当前加载O8，共享锁可用，板内服务活动；"
              "网口仍无物理载波，外部访问未恢复。新COLO离线作业130734完成0:0，450次前向与72组评分／66面板已复核。"
              "本轮没有新训练或板端推理，旧四次实验1594次前向不重复计入。默认未替换。")
text = text.replace(old_status, new_status)
overview.write_text(text, encoding="utf-8")
for target in targets[1:]:
    head, rest = before[target].split("\n", 1)
    extra = ""
    if target == ROOT / "Review与当前状态.md":
        extra = " " + link("research_synthesis_20261027/results/overview_review_20261030_v11.json", "第11版总览复核") + "。"
    target.write_text(head + "\n\n" + current + extra + "\n\n以下保留此前阶段记录，其中旧“原包待下载”等表述只对应当时状态。\n" + rest, encoding="utf-8")
for record, target in zip(records, targets):
    record["after_sha256"] = sha(target)
    record["unified_diff"] = list(difflib.unified_diff(before[target].splitlines(), target.read_text(encoding="utf-8").splitlines()))
result = {"created_UTC": datetime.now(timezone.utc).isoformat(), "records": records,
          "frozen_phase_reports_overwritten": False, "new_model_forwards_by_this_script": 0,
          "current_new_offline_model_image_forwards": 450, "current_new_board_forwards": 0,
          "whole_goal_complete": False}
target = ROOT / "results/full_archive_external_entrypoint_updates_20261030.json"
assert not target.exists()
target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({"updated_entrypoints": len(records), "snapshots_preserved": len(records), "new_board_forwards": 0}))
