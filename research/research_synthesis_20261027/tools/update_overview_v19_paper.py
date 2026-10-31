from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, difflib

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent

def load(p):
    return json.loads(p.read_text(encoding="utf-8"))

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def link(label, target):
    return f"[{label}](<{(PROJECT/target).as_posix()}>)"

main = PROJECT/"研究阶段总结_20261030.md"
previous = load(ROOT/"results/overview_review_20261030_v18_interruption.json")
assert sha(main) == previous["document"]["sha256"]
paper = load(PROJECT/"paper_readiness_20261030/results/manuscript_review_v1.json")
assert not paper["ready_for_submission"] and not paper["whole_goal_complete"]
assert paper["numeric_table_rows_verified"] == 8 and paper["new_model_forwards"] == 0
for item in paper["documents"]:
    assert sha(Path(item["file"])) == item["sha256"]
paths = [main, PROJECT/"研究总览_从想法到论文.md", PROJECT/"研究进度.md",
         PROJECT/"phase3_diagnosis_20261026/方案与执行状态.md", ROOT/"Review与当前状态.md"]
backup = ROOT/"snapshots/overview_v18_before_paper_draft"
backup.mkdir(parents=True, exist_ok=False)
snapshots = []
before = {}
for p in paths:
    before[p] = p.read_text(encoding="utf-8")
    dest = backup/p.relative_to(PROJECT)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(p.read_bytes())
    snapshots.append({"path":str(p),"snapshot":str(dest),"sha256":sha(dest)})
latest = (
    "2026年10月30日写作进展：" + link("方法与实验草稿","paper_readiness_20261030/论文方法与实验草稿.md") +
    "、" + link("12项主张与证据对应","paper_readiness_20261030/论文主张与证据对应.md") +
    "及" + link("五篇最接近原始论文对照","paper_readiness_20261030/文献对照_原始来源.md") +
    "已形成并完成数字与范围自审。草稿区分10ID×3组件图库与6ID/30图通道图库、各自校准与共用系统阈值，"
    "保留3／30自动接受、迟到及10／人工12的不利结果；当前尚不具备投稿条件。用户告知网线已接路由器，"
    "最近一次只读发现电脑为192.168.3.13／24，但未找到板卡22／9090服务，COM6仍无输出；"
    "等待板卡IP与供电状态确认后优先取回SD原实验。没有新增推理、训练、调参或重跑，实际触发四轮仍待原始数据核验。"
)
for p in paths[1:]:
    head, rest = before[p].split(chr(10),1)
    rest = rest.lstrip(chr(10))
    assert rest.startswith("2026年10月30日最新：")
    rest = rest.replace("2026年10月30日最新：","此前实机中断与恢复状态：",1)
    extra = " " + link("第19版总览复核","research_synthesis_20261027/results/overview_review_20261030_v19_paper.json") + "。" if p == ROOT/"Review与当前状态.md" else ""
    p.write_text(head+chr(10)*2+latest+extra+chr(10)*2+rest,encoding="utf-8")
s = before[main]
needle = "**当前进展："
at = s.index(needle)
s = s[:at]+latest+chr(10)*2+s[at:]
old = "6. 可以先完成问题定义、相关工作、方法与实验协议稿；最终结果与结论要等独立评分和实际设备证据齐全。稿件形成后再按真实贡献选择期刊／会议，不承诺某分区录用。"
new = "6. " + link("问题、方法与已完成结果草稿","paper_readiness_20261030/论文方法与实验草稿.md") + "及文献对照已形成并完成自审。按12项主张补齐对应实验后，再确定最终结果、结论及目标刊会；当前不认领投稿准备完成或分区录用。"
assert s.count(old) == 1
s = s.replace(old,new)
needle = "## 7. 本轮状态与自审"+chr(10)*2
assert s.count(needle) == 1
extra = (
    "写作整理完成一份方法及实验草稿，绑定7份结果来源与6份方法／统计来源；逐表核对8行结果，"
    "检查28个本地链接，并完整通读新增正文及原始文献对照。自审修正图库规模、阈值和时钟范围的混淆，"
    "未把候选排名、零误收观察或接近5FPS升级成可靠自动恢复和全链路实时保证。"
    "此为助手自审，不是独立事件审核、完整设备结果核验或同行评审。"
    + link("草稿自审记录","paper_readiness_20261030/Review与当前状态.md") + "。"
)
s = s.replace(needle,needle+extra+chr(10)*2,1)
main.write_text(s,encoding="utf-8")
diffs = []
for p in paths:
    diffs += list(difflib.unified_diff(before[p].splitlines(),p.read_text(encoding="utf-8").splitlines(),
                                    fromfile=str(p.relative_to(PROJECT))+" v18",
                                    tofile=str(p.relative_to(PROJECT))+" v19",n=2))
diff_path = ROOT/"results/overview_diff_20261030_v19_paper.txt"
assert not diff_path.exists()
diff_path.write_text(chr(10).join(diffs)+chr(10),encoding="utf-8")
value = {"status":"FIVE_ENTRYPOINTS_UPDATED_WITH_REVIEWED_PAPER_DRAFT_AND_UNCHANGED_HARDWARE_GAPS",
         "created_UTC":datetime.now(timezone.utc).isoformat(),
         "previous_files_and_snapshots":snapshots,
         "current_entrypoints":[{"path":str(p),"sha256":sha(p)} for p in paths],
         "diff":{"path":str(diff_path),"sha256":sha(diff_path)},
         "paper_review":{"path":str(PROJECT/"paper_readiness_20261030/results/manuscript_review_v1.json"),
                         "sha256":sha(PROJECT/"paper_readiness_20261030/results/manuscript_review_v1.json")},
         "whole_goal_complete":False}
target = ROOT/"results/entrypoint_update_20261030_v19_paper.json"
assert not target.exists()
target.write_text(json.dumps(value,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"status":value["status"],"main_lines":len(s.splitlines()),"diff_lines":len(diffs)}))
