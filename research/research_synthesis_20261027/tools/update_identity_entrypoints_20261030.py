from pathlib import Path
from datetime import datetime, timezone
import difflib, hashlib, json

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def link(relative, title):
    return f"[{title}](<{(PROJECT / relative).as_posix()}>)"


overview = PROJECT / "研究阶段总结_20261030.md"
previous = json.loads((ROOT / "results/overview_review_20261030_v12.json").read_text(encoding="utf-8"))
assert sha(overview) == previous["document"]["sha256"]
targets = [overview, PROJECT / "研究总览_从想法到论文.md", PROJECT / "研究进度.md",
           PROJECT / "phase3_diagnosis_20261026/方案与执行状态.md", ROOT / "Review与当前状态.md"]
snapshots = ROOT / "results/snapshots_Cows2021_identity_20261030"
snapshots.mkdir(exist_ok=False)
records, before = [], {}
for index, path in enumerate(targets):
    snapshot = snapshots / (str(index) + "_" + path.name)
    snapshot.write_bytes(path.read_bytes())
    before[path] = path.read_text(encoding="utf-8")
    records.append({"target": str(path), "before_snapshot": str(snapshot), "before_sha256": sha(snapshot)})
intake = link("cows2021_identity_intake_20261030/身份来源核查与跨日期评价准入.md", "Cows2021身份来源核查")
evaluation = link("cows2021_identity_eval_20261030/跨日期身份检索与拒识结果.md", "540图跨日期身份评价")
control = link("cows2021_identity_gallery_control_20261030/图库规模控制与拒识限制.md", "20／40牛号图库控制")
current = (f"2026年10月30日最新：{intake}确认官方身份Test有8670图、181非空ID，README13784与论文8670测试口径已厘清；"
           f"{evaluation}按预先SHA选120ID／540图，两个冻结编码器共1080次CPU前向。当前C在120已登记查询Top-1为65（54.17%），"
           "新域阈值C30／W21／U69，未知误接受20／120（16.67%）；ImageNet基线Top-1为69。"
           f"{control}保持查询和阈值，确认加20干扰ID使C的未知误接受12或16→20；即便20ID仍未维持校准5%，不采用新阈值或自动可靠身份主张。"
           "全部540输入、1080特征、24000分数／960决定和图库控制2880决定均复算；12固定源样例、11事后解释面板已查看。"
           "原结果包与失败记录保留，03-05至03-11像素继续隔离。本轮0训练、0板端推理；已有同板八次实机保留，原12事件永久牛号与独立逐事件JSON仍缺。")
text = before[overview]
old = next(line for line in text.splitlines() if line.startswith("**当前结论："))
new = ("**当前结论：检测、计数和身体检索已在同一PYNQ-Z2运行，固定负载可接近5FPS，但原片计数仍未恢复人工确认12。"
       "新公开跨日期身份评价已完成：当前编码器Top-1为54.17%，新域阈值下已登记错误接受21／120、未知误接受20／120，尚不能可靠自动找回牛号。"
       "当前优先改进身份特征与按图库规模验证的拒识，再补独立通行和真实输入；论文贡献仍待验证。**")
assert text.count(old) == 1
text = text.replace(old, new)
old = next(line for line in text.splitlines() if line.startswith("2026年10月30日最新："))
text = text.replace(old, current)
needle = "| 两网络同板 | ARM身体网络、真实裁剪／预处理／图库检索已经执行 | 永久身份正确率、未登记牛风险、实际RF关联 |"
assert text.count(needle) == 1
text = text.replace(needle, "| 两网络同板 | ARM身体网络、真实裁剪／预处理／图库检索已经执行 | 当前12事件的可靠身份与实际RF关联 |\n"
                    "| 外来源身份评价 | Cows2021新540裁剪，C Top-1 65／120 | 新域错误接受21／120、未知误接受20／120；非完整事件 |")
needle = "### 3.5 同板周期回放：吞吐、迟到与后台等待"
assert text.count(needle) == 1
addition = ("新的带作者ID评价已经完成，不能再将“当前事件没有永久身份”写成“完全没有身份评价数据”。"
            "Cows2021的120个ID按预先规则分校准／评价及已登记／未知，540张身体裁剪中图库至少早于查询7天；"
            "输入日期不晚于03-04，03-05至03-11继续隔离。当前C的Top-1为65／120，基线B为69／120；"
            "新域阈值下C正确接受30、错误身份接受21、拒绝69，未知误接受20／120，不能认作可靠找回。\n\n"
            "原协议的校准图库20ID、评价40ID存在规模变化。保持查询与阈值的事后控制显示C未知误接受12或16→20；"
            "规模解释一部分，20ID下仍未维持校准经验5%。不在评价集调阈值，也不按4个Top-1差异替换模型。"
            f"{evaluation}和{control}保存全部4主条件、16规模控制与独立复算。\n\n"
            "这里是作者提供的身体裁剪，未包含检测／抓拍漏失；7,931原测试裁剪能对应检测原图体系，"
            "跨年物理牛号映射也未知。它支持冻结编码器的公开图像评价，不是原12头牛的档案答案或独立端到端测试。\n\n")
text = text.replace(needle, addition + needle)
needle = "不一定要重新寻找另一个名字的数据集，但需要**独立于当前开发过程的新会话、事件参考和身份关系**。"
assert text.count(needle) == 1
text = text.replace(needle, needle + f"\n\n{intake}与{evaluation}已经补充带作者ID的跨日期已登记／未知检验；当前模型暴露高错误接受。"
                    "余下缺口是独立于方法选择的新会话／牛号、真实事件照片对应以及全链路漏失，并非网上没有身份数据。")
needle = "| 已登记身份与拒识 | 带身份公开图、不同日期图库和既定编码器 | 按牛／会话／日期隔离的未见查询，未登记牛及真实永久身份标签 |"
assert text.count(needle) == 1
text = text.replace(needle, "| 已登记身份与拒识 | 原MultiCam研究及新Cows2021 540图／120ID评价，已有完整失败结果 | 改善错误接受并匹配实际图库规模；新的最终牛号、原事件对应及全链路C／W／U／M |")
old = "2. 外来源固定评价与错误分解已完成，躯干／作者整牛范围约定已经写出；据此冻结下一次数据与验证协议，COLO50图不作阈值或seed调参集。94的检测缺口和103的确认损失分别保留；身份方向先核查公开带ID数据的日期／同次通行来源，不提前打开现有最终留出图。"
new = "2. 公开身份来源核查和540图评价已完成，当前C错误接受仍高；优先冻结按目标图库规模校准／评价的协议，再比较身份训练覆盖与拒识策略，保留新的最终牛号。COLO50图与这次240评价查询不作阈值或seed调参集；94的检测缺口和103的确认损失分别保留。"
assert text.count(old) == 1
text = text.replace(old, new)
old = next(line for line in text.splitlines() if line.startswith("最新八次固定照片任务、八身份子任务"))
new = ("本轮新增身份Slurm作业130743完成0:0，原始结果6.0MB／35清单文件已完整取回；1080次CPU前向、540输入、24000分数／960决定及按牛区间复算通过，"
       "12源图与11解释面板已查看。图库规模控制新增前向0、2880决定／86400分数另行核查。没有新训练、板端运行或阈值替换，"
       "旧八次O8／ARM实机、完整归档和板卡终态按其阶段保留；网口载波本轮未重新排查。03-05至03-11保留像素未打开。")
text = text.replace(old, new)
overview.write_text(text, encoding="utf-8")
for path in targets[1:]:
    title, rest = before[path].split("\n",1)
    extra = " " + link("research_synthesis_20261027/results/overview_review_20261030_v13.json", "第13版总览复核") + "。" if path == ROOT / "Review与当前状态.md" else ""
    path.write_text(title + "\n\n" + current + extra + "\n\n以下保留历史阶段，旧“身份真值缺失”应按原事件或当时数据范围解释。\n" + rest, encoding="utf-8")
for path, record in zip(targets, records):
    record["after_sha256"] = sha(path)
    record["unified_diff"] = list(difflib.unified_diff(before[path].splitlines(), path.read_text(encoding="utf-8").splitlines()))
result = {"created_UTC": datetime.now(timezone.utc).isoformat(), "records": records, "frozen_phase_reports_overwritten": False,
          "current_stage_new_model_image_forwards": 1080, "current_stage_new_board_forwards": 0,
          "new_training_updates": 0, "whole_goal_complete": False}
target = ROOT / "results/Cows2021_identity_entrypoint_updates_20261030.json"
assert not target.exists()
target.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
print(json.dumps({"entrypoints_updated": len(records), "snapshots_preserved": len(records), "actual_new_CPU_image_forwards":1080, "new_board_forwards":0}))
