from pathlib import Path
from datetime import datetime, timezone
import difflib, hashlib, json

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def link(relative, title):
    return f"[{title}](<{(PROJECT / relative).as_posix()}>)"


previous = json.loads((ROOT / "results/overview_review_20261030_v11.json").read_text(encoding="utf-8"))
overview = PROJECT / "研究阶段总结_20261030.md"
assert sha(overview) == previous["document"]["sha256"]
targets = [overview, PROJECT / "研究总览_从想法到论文.md", PROJECT / "研究进度.md",
           PROJECT / "phase3_diagnosis_20261026/方案与执行状态.md", ROOT / "Review与当前状态.md"]
snapshots = ROOT / "results/snapshots_affinity_diagnosis_20261030"
snapshots.mkdir(exist_ok=False)
before = {}
records = []
for index, path in enumerate(targets):
    snapshot = snapshots / (str(index) + "_" + path.name)
    snapshot.write_bytes(path.read_bytes())
    before[path] = path.read_text(encoding="utf-8")
    records.append({"target": str(path), "before_snapshot": str(snapshot), "before_sha256": sha(snapshot)})
diagnosis = link("colo_error_diagnosis_20261030/低召回分解与检测对象约定.md", "外来源错误分解与检测对象约定")
contract = link("colo_error_diagnosis_20261030/检测对象与标注使用约定.md", "躯干与整牛标签约定")
board = link("cpu_partition_combined_20261030/固定照片负载八次实机与CPU分配取舍.md", "固定10照片任务的八次实机")
current = (f"2026年10月30日最新：{diagnosis}完成4050个GT条件行、173个FP条件行和5400个匹配上界核查；"
           "新192的364个FN分为104个0.001–0.20候选、196个更低分候选、64个无IoU0.50几何，不能只归因于边界或用GT选框上界当新召回。"
           f"{board}已完成并完整取回原包：前台主线程可用两核时，共享后台4.987／5.000FPS、均计10，固定后台CPU1为4.885／4.770FPS、计10／8；"
           "各次均10身份任务。前一主线程CPU0的四次4.50–4.55FPS、计9／10／9／8也全部保留，两个限制策略均不全局采用。"
           "2963实际raw、17227观察、80照片／特征及40同照片配对复算通过；10份不同照片映射全部80次。"
           "本轮3083次新实机前向、0训练，固定任务与真实触发链路、主线程亲和性与严格核心隔离分别表述。"
           "O8、锁及服务终态复查通过，网口仍无载波，独立事件／永久身份和实际输入仍待补。")
text = before[overview]
old = next(line for line in text.splitlines() if line.startswith("**当前结论："))
new = ("**当前结论：检测、ARM计数和身体检索已在同一PYNQ-Z2运行；O8三尺寸均有实机记录。"
       "最新固定10照片任务中，共享后台两次4.987／5.000FPS、均计数10／人工12；固定后台CPU1一轮计数8，未采用。"
       "这是固定负载回放，仍有迟到且没有永久身份真值。外来源192检测在conf0.20下召回19.11%，检测与标注范围仍需改进，论文贡献尚未证明。**")
assert text.count(old) == 1
text = text.replace(old, new)
old = next(line for line in text.splitlines() if line.startswith("2026年10月30日最新："))
text = text.replace(old, current)
needle = "| 外来源俯视检测 | COLO官方50图／450有效框，9个固定条件 | 新192召回19.11%；无新增通行／永久身份GT |"
assert text.count(needle) == 1
text = text.replace(needle, needle + "\n| 相同10照片负载 | 主线程两核＋共享后台4.987／5.000FPS，身份最长1.882／1.967秒 | 58／68迟到、计数10；不同于真实触发或每帧高分输入 |")
needle = "最新调度对照固定相同有界输入、模型和选择规则，仅切换是否按帧暂停后台。两组均有CPU边界仪器，当前暂停组才是直接基线。四次结果为："
assert text.count(needle) == 1
insert = ("最新补充的是固定身份负载的CPU分配对照：八次都做相同10个JPEG裁剪／PNG0／实际NCNN／检索任务，"
          "与该次计数解耦。主线程CPU0的四次计数9／10／9／8、吞吐4.50–4.55FPS，全1423处理时刻迟到，未采用。"
          "追加四次令主线程可用两核，结果如下。两阶段按时间先后执行，不能将全部差异归因于亲和性；"
          "只核查主线程／发布线程和后台线程mask，不宣称严格核心隔离。\n\n"
          "| 轮次 | 后台CPU | 处理／392 | 跳过 | >200ms | FPS | 计数／人工12 | 最长身份完成s |\n"
          "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |\n"
          "| 1 | 共享0／1 | 391 | 1 | 58 | 4.987 | 10 | 1.882 |\n"
          "| 1 | 固定1 | 383 | 9 | 67 | 4.885 | 10 | 1.657 |\n"
          "| 2 | 固定1 | 374 | 18 | 64 | 4.770 | 8 | 1.770 |\n"
          "| 2 | 共享0／1 | 392 | 0 | 68 | 5.000 | 10 | 1.967 |\n\n"
          "固定CPU1略缩短身份等待，却未同时改善吞吐和计数，因此不采用。当前后台完成含JPEG、PNG和输入／特征NPZ证据写出，"
          "不能用约168–206ms纯身份网络用时代替完整任务；没有每帧高分JPEG环，也不代表真实触发或现场双流。"
          f"2963份raw、80照片／特征和40同照片配对均复核，完整原包已取回；详见{board}。\n\n"
          "此前的每帧有界输入调度阶段保留如下，负载与上述固定照片控制不同。\n\n")
text = text.replace(needle, insert + needle.replace("最新调度对照", "此前调度对照"))
needle = "## 4. 数据还需要怎样补"
assert text.count(needle) == 1
addition = ("### 3.7 外来源低召回已经分解，标签范围继续保留\n\n"
            "在固定conf0.20／IoU0.50的静态图上，9条件的最大一对一匹配数均等于原TP；仅换静态分配不能补回缺口。"
            "新192的364个未匹配框中，104个仅有0.001–0.20 cow候选、196个只有更低分候选、64个没有足够几何。"
            "这不证明低分候选正确，也不把GT选框上界当召回改善。内部186框仅28匹配，边界264框58匹配，小框外仍有缺口。\n\n"
            f"4050逐框记录、173条件级FP、5400个最大匹配证书和13原图案例已经核查，见{diagnosis}。"
            f"已固定{contract}：当前训练与计数中心沿用躯干，COLO保留作者整牛／遮挡推断范围作压力评价；"
            "没有可靠映射前不混成标注一致训练集，不自动重标或删难例，默认模型和阈值不变。\n\n")
text = text.replace(needle, addition + needle)
old = "3. 全程低优先级后台对照已完成：等待降到约2秒，前台吞吐与一次计数退步，默认不采用。接下来明确前台迟到及身份完成上限，研究有服务预算的后台；以固定作业／照片作调度压力对照，同时保留完整真实触发链路和独立身份评价。"
new = "3. 同负载CPU分配控制现已完成：共享后台接近5FPS且身份最长约2秒，但仍迟到和少计；固定后台CPU1未改善整体取舍，不采用。下一步回到真实通行触发的按需抓拍，明确前台迟到与身份完成要求，保留PNG／NPZ记录开销并逐项计时，不将固定任务当真实触发。"
assert text.count(old) == 1
text = text.replace(old, new)
old = "2. 外来源固定检测评价已经完成，当前跨来源召回和标注对象差异仍明显；先统一躯干／整牛／边界牛的任务定义，再固定训练或检测控制协议。COLO测试不作调参集；94的检测缺口和103的确认损失分别保留，不用换seed或帧号特判追12。"
new = "2. 外来源固定评价与错误分解已完成，躯干／作者整牛范围约定已经写出；据此冻结下一次数据与验证协议，COLO50图不作阈值或seed调参集。94的检测缺口和103的确认损失分别保留；身份方向先核查公开带ID数据的日期／同次通行来源，不提前打开现有最终留出图。"
assert text.count(old) == 1
text = text.replace(old, new)
old = next(line for line in text.splitlines() if line.startswith("同板部署已有真实记录。最新四次后台对照及恢复任务"))
new = ("最新八次固定照片任务、八身份子任务和两采集任务均终态／消失；O8、锁和板内服务再次核查通过，网口仍无载波。"
       "338成员／337清单文件的完整12.7MB原包已取回，2963raw、17227观察／16路径、80原照片／输入／特征与40同照片配对均复算。"
       "本轮新增3083次实际模型前向，无训练或新Torch参考；10份不同照片的80次重复不能当80头牛。"
       "COLO错误分解新增前向0；默认模型、计数／拒识和Notebook不变。")
text = text.replace(old, new)
overview.write_text(text, encoding="utf-8")
for target in targets[1:]:
    head, rest = before[target].split("\n", 1)
    extra = " " + link("research_synthesis_20261027/results/overview_review_20261030_v12.json", "第12版总览复核") + "。" if target == ROOT / "Review与当前状态.md" else ""
    target.write_text(head + "\n\n" + current + extra + "\n\n以下为此前阶段记录，其“当前／下一步”按当时证据解释。\n" + rest, encoding="utf-8")
for target, record in zip(targets, records):
    record["after_sha256"] = sha(target)
    record["unified_diff"] = list(difflib.unified_diff(before[target].splitlines(), target.read_text(encoding="utf-8").splitlines()))
result = {"created_UTC": datetime.now(timezone.utc).isoformat(), "records": records, "frozen_phase_reports_overwritten": False,
          "new_model_forwards_by_this_script": 0, "current_stage_actual_new_model_forwards": 3083,
          "new_training_updates": 0, "whole_goal_complete": False}
target = ROOT / "results/affinity_diagnosis_entrypoint_updates_20261030.json"
assert not target.exists()
target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({"entrypoints_updated": len(records), "snapshots_preserved": len(records), "actual_stage_new_forwards": 3083}))
