from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,difflib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
link=lambda label,name:f"[{label}](<{(PROJECT/name).as_posix()}>)"
old=load(ROOT/"results/overview_review_20261030_v19_paper.json");main=PROJECT/"研究阶段总结_20261030.md"
assert sha(main)==old["document"]["sha256"]
stage=PROJECT/"independent_source_recheck_20261030"
review=load(stage/"results/final_review_v1.json")
assert review["metadata_conflict_groups"]==40 and review["byte_verified_conflict_groups"]==2
assert review["actually_viewed_frozen_QA_images"]==8 and review["new_model_forwards"]==0
for name,digest in review["evidence_hashes"].items():assert sha(stage/name)==digest
paths=[main,PROJECT/"研究总览_从想法到论文.md",PROJECT/"研究进度.md",
       PROJECT/"phase3_diagnosis_20261026/方案与执行状态.md",ROOT/"Review与当前状态.md"]
backup=ROOT/"snapshots/overview_v19_before_source_recheck";backup.mkdir(parents=True,exist_ok=False)
before={};snapshots=[]
for p in paths:
    before[p]=p.read_text(encoding="utf-8");dest=backup/p.relative_to(PROJECT)
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
    snapshots.append({"path":str(p),"snapshot":str(dest),"sha256":sha(dest)})
ref=link("新BECA背部身份数据准入与冲突核查","independent_source_recheck_20261030/BECA身份数据准入与冲突核查.md")
latest=("2026年10月30日来源进展："+ref+
        "已实际取得迁移后官方归档目录与文本：合并身份目录12,172文件／103ID／134日期，另有牛舍副本不可重复计数。"
        "模型预测前发现40组同来源／CRC／大小却不同身份的候选冲突，两个固定代表组已确认完整JPEG字节相同；其余38组仅元数据。"
        "8张冻结QA图已看，含棕色／棕白肉牛、饲喂栏杆遮挡和源时间字样，与目标荷斯坦通道不同。"
        "BECA暂为需补标签核查的外来源身份候选，新增计数真值、身份评分、训练和模型前向均0；"
        "实际触发四轮原始结果、独立事件JSON及原12事件永久牛号仍缺，板卡访问未恢复。")
for p in paths[1:]:
    head,rest=before[p].split(chr(10),1);rest=rest.lstrip(chr(10))
    assert rest.startswith("2026年10月30日写作进展：")
    rest=rest.replace("2026年10月30日写作进展：","此前论文写作阶段：",1)
    extra=" "+link("第20版来源复核","research_synthesis_20261027/results/overview_review_20261030_v20_sources.json")+"。"if p==ROOT/"Review与当前状态.md"else""
    p.write_text(head+chr(10)*2+latest+extra+chr(10)*2+rest,encoding="utf-8")
s=before[main];at=s.index("2026年10月30日写作进展：")
s=s[:at]+latest+chr(10)*2+s[at:]
needle="| 外来源俯视检测 |";at=s.index(needle)
s=s[:at]+"| 新外来源背部身份准入 | BECA12,172文件／103ID；日期可解析，8张QA已看 | 40组身份冲突线索，2组字节证实；非连续通道GT，尚未评分 |"+chr(10)+s[at:]
needle="## 4. 数据还需要怎样补"+chr(10)*2
paragraph=(ref+"新增可实际读取的背部跨日期来源。包内readme、1,424个BECA-D配对和BECA-L的8,321图／15,788对象标注已核验；"
           "bbox为xyxy、关键点为26坐标值，不能直接照搬标准COCO解析。合并身份目录12,172文件对应103ID，"
           "三个牛舍目录为其副本；完整68,350项目录已与Python zipfile匹配。40组同来源多ID线索涉及15个ID，"
           "两个固定代表组（16／5和71／79）JPEG字节完全相同，其余38组尚未字节核验。"
           "未来先隔离受影响ID与已见QA身份11／65／100，再冻结相应日期及已知／未知划分；原标签未改。"
           "8张联系表样本显示视角为背部俯拍，但有肉牛外观、栏杆、旋转裁剪及相机时间字样，"
           "不能直接换算成目标荷斯坦通道的身份可靠性。当前没有新增身份成绩、训练或计数事件GT。")
assert s.count(needle)==1;s=s.replace(needle,needle+paragraph+chr(10)*2,1)
needle="## 7. 本轮状态与自审"+chr(10)*2
paragraph=("新来源阶段完成31份响应记录绑定、68,350目录双解析、文本CRC、4成员／2组字节取证和8张QA视觉检查。"
           "共保存14,561,616响应字节（含失败正文），没有下载20.31GB整包或核验整包MD5。"
           "初始HTTP403、ZIP64哨兵处理与后缀不唯一假设的失败均保留。"
           "自审将发现限制在实际读取范围，未认领全库标签正确、真实永久牛号或新增模型效果。"
           +link("来源阶段自审","independent_source_recheck_20261030/Review与当前状态.md")+"。")
assert s.count(needle)==1;s=s.replace(needle,needle+paragraph+chr(10)*2,1)
main.write_text(s,encoding="utf-8")
diff=[]
for p in paths:
    diff+=list(difflib.unified_diff(before[p].splitlines(),p.read_text(encoding="utf-8").splitlines(),
                                 fromfile=str(p.relative_to(PROJECT))+" v19",tofile=str(p.relative_to(PROJECT))+" v20",n=2))
diff_path=ROOT/"results/overview_diff_20261030_v20_sources.txt";assert not diff_path.exists()
diff_path.write_text(chr(10).join(diff)+chr(10),encoding="utf-8")
record={"status":"FIVE_ENTRYPOINTS_UPDATED_WITH_ACTUAL_NEW_SOURCE_ADMISSION_LIMITS_NO_NEW_MODEL_RESULTS",
        "created_UTC":datetime.now(timezone.utc).isoformat(),"previous_files_and_snapshots":snapshots,
        "current_entrypoints":[{"path":str(p),"sha256":sha(p)}for p in paths],
        "diff":{"path":str(diff_path),"sha256":sha(diff_path)},
        "new_source_review":{"path":str(stage/"results/final_review_v1.json"),"sha256":sha(stage/"results/final_review_v1.json")},
        "whole_goal_complete":False}
out=ROOT/"results/entrypoint_update_20261030_v20_sources.json";assert not out.exists()
out.write_text(json.dumps(record,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"status":record["status"],"main_lines":len(s.splitlines()),"diff_lines":len(diff)}))
