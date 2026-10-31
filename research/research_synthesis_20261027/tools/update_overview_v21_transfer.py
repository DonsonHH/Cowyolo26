from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,difflib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
link=lambda label,name:f"[{label}](<{(PROJECT/name).as_posix()}>)"
old=load(ROOT/"results/overview_review_20261030_v20_sources.json")
main=PROJECT/"研究阶段总结_20261030.md";assert sha(main)==old["document"]["sha256"]
review_paths=[PROJECT/"beca_fixed_transfer_20261030/results/final_review.json",
              PROJECT/"beca_score_diagnosis_20261031/results/final_review.json",
              PROJECT/"paper_readiness_20261030/results/manuscript_review_v2.json"]
fixed,diag,paper=map(load,review_paths)
assert fixed["model_image_forwards"]==180 and fixed["main_counts"]==[[14,13,15,2,26],[15,13,11,6,26]]
assert diag["zero_W_FA_max_C"]==[1,3]and diag["new_model_forwards"]==0
assert paper["claims"]==15 and not paper["ready_for_submission"]
paths=[main,PROJECT/"研究总览_从想法到论文.md",PROJECT/"研究进度.md",
       PROJECT/"phase3_diagnosis_20261026/方案与执行状态.md",ROOT/"Review与当前状态.md"]
backup=ROOT/"snapshots/overview_v20_before_external_transfer";backup.mkdir(parents=True,exist_ok=False)
before={};snapshots=[]
for p in paths:
    before[p]=p.read_text(encoding="utf-8");dest=backup/p.relative_to(PROJECT)
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
    snapshots.append({"path":str(p),"snapshot":str(dest),"sha256":sha(dest)})
transfer_ref=link("固定BECA外来源评价","beca_fixed_transfer_20261030/固定模型外来源结果与阈值失配.md")
diagnosis_ref=link("单一最高分阈值诊断","beca_score_diagnosis_20261031/单阈值能解决多少问题.md")
draft_ref=link("论文草稿v2","paper_readiness_20261030/论文方法与实验草稿_v2.md")
latest=("2026年10月31日最新："+transfer_ref+"已完成20ID／90图、180次CPU图前向及全部决定复算；"
        "主工作点旧／新Top-1为14／30、15／30，C13／W15／U2与C13／W11／U6，未知FA均26／30。"
        +diagnosis_ref+"使用已评分标签事后枚举全部状态，观察W=FA=0时最多正确接受1／30和3／30，未选择部署阈值。"
        "图像日期与相机叠字存在两例不一致，结果限定按作者ID及文件名日期；20ID现在为已见材料。"
        +draft_ref+"已纳入高误收、日期疑点和事后诊断，v1保留。今天COM6未枚举，当前192.168.3.0／24未发现22／9090服务，"
        "访问未恢复；实际触发原始数据、独立事件JSON、原12事件身份与全链路5FPS继续待验。")
for p in paths[1:]:
    head,rest=before[p].split(chr(10),1);rest=rest.lstrip(chr(10))
    assert rest.startswith("2026年10月30日来源进展：")
    rest=rest.replace("2026年10月30日来源进展：","此前BECA来源准入：",1)
    extra=" "+link("第21版总览复核","research_synthesis_20261027/results/overview_review_20261031_v21_transfer.json")+"。"if p==ROOT/"Review与当前状态.md"else""
    p.write_text(head+chr(10)*2+latest+extra+chr(10)*2+rest,encoding="utf-8")
s=before[main]
s=s.replace("更新：2026年10月30日。","更新：2026年10月31日。",1)
at=s.index("2026年10月30日来源进展：");s=s[:at]+latest+chr(10)*2+s[at:]
start=s.index("**当前进展：");end=s.index("**",start+2)+2
s=s[:start]+("**当前进展：Cows保留ID的新模型Top-1为30／30但只接受3／30；BECA固定迁移Top-1为15／30、未知误收26／30，"
              "不支持原阈值跨来源自动使用。相同90图ARM实现一致性仍成立；实际触发四轮只取回部分摘要，原始文件及第四轮终态尚未取回。"
              "今天板卡串口和局域网入口均未找到，先恢复原结果访问；逐事件与永久牛号真值、稳定全链路5FPS和主要论文贡献继续待验证。**")+s[end:]
oldrow="| 新外来源背部身份准入 | BECA12,172文件／103ID；日期可解析，8张QA已看 | 40组身份冲突线索，2组字节证实；非连续通道GT，尚未评分 |"
newrow="| BECA固定模型外来源评价 | 20ID／90图，旧／新Top-1为14／30、15／30，未知FA均26／30 | 原阈值未保持低误收；标签／日期边界、非计数GT；单阈值事后零错误仅C1／C3 |"
assert s.count(oldrow)==1;s=s.replace(oldrow,newrow)
section=f"""### 3.13 BECA固定模型外来源：高误收及单阈值覆盖限制

{transfer_ref}先隔离15个冲突线索ID与3个已见QA身份，再在相应图像访问前冻结10注册＋10未知、90张OBB图、两模型和全部工作点。三个牛舍都有两种角色，图库及查询使用不同文件名日期。CPU作业130909完成0:0、180图前向／16网络调用，没有训练或板端推理。

| 编码器 | Top-1／30 | 图像检索mAP | C／30 | W／30 | U／30 | 未知FA／30 |
|---|---:|---:|---:|---:|---:|---:|
| 原 | 14 | 51.46% | 13 | 15 | 2 | 26 |
| Cows域 | 15 | 48.50% | 13 | 11 | 6 | 26 |

原主阈值不能在该来源保持低误收。已有较高新阈值约0.87075仍误收13／30，并把C降到7／30，附加工作点未升为主方法。按ID且保持牛舍组成的重采样中，Top-1差95%百分位区间−6.67至13.33个百分点，mAP差−11.58至6.96；不把一张Top-1增加认领跨来源方法优势。

完整28,326,942字节、496成员／495清单文件取回；90JPEG、180特征、3,600图库图像分数、1,200ID分数／480决定与24配对统计独立复算，10页全部90图实际看完。索引40／41的文件名日期为06-05／06-06，相机叠字却为05-13／05-20，哪个时钟正确尚未核实；日期隔离只按文件名定义，作者剩余ID也未独立认证。未删图、改日期、重跑或调阈值。

{diagnosis_ref}只使用这些已保存分数，分别枚举61个可达状态。观察W=FA=0时，旧／新最高正确接受只有1／30和3／30；即使事后挑门限，单一最高分也存在覆盖限制。此为利用已评分标签的诊断上界，不是独立校准或新部署方案，0新增模型前向／训练／数据像素。原因没有被归因于毛色或背景。

{draft_ref}及15项主张对应表保留原稿，区分固定评价、日期疑点与事后上界。BECA20ID现已评分，后续改方法须新证据；原12通行和实机目标没有由外来源图片替代。

"""
needle="## 4. 数据还需要怎样补";assert s.count(needle)==1;s=s.replace(needle,section+needle,1)
needle="当前没有新增身份成绩、训练或计数事件GT。"
assert s.count(needle)==1;s=s.replace(needle,"此前来源准入阶段没有身份成绩；随后已完成本节前述固定20ID迁移评价，仍无新增训练或计数事件GT。",1)
needle="| 已登记身份与拒识 | 原MultiCam、Cows120ID开发／16ID训练，另20ID／90图一次固定评价 |"
assert s.count(needle)==1;s=s.replace(needle,"| 已登记身份与拒识 | 原MultiCam、Cows开发／训练与20ID评价，另BECA20ID／90图固定迁移 |",1)
needle="6. "+link("问题、方法与已完成结果草稿","paper_readiness_20261030/论文方法与实验草稿.md")+"及文献对照已形成并完成自审。按12项主张补齐对应实验后，再确定最终结果、结论及目标刊会；当前不认领投稿准备完成或分区录用。"
replacement="6. "+draft_ref+"已加入BECA固定迁移、日期疑点及事后单阈值上界；"+link("15项主张证据表","paper_readiness_20261030/论文主张与证据对应_v2.md")+"继续绑定已完成与未完成证据。补齐真实事件、原实机结果和具体贡献后再定最终结论及目标刊会，当前不是投稿终稿。"
assert s.count(needle)==1;s=s.replace(needle,replacement)
needle="## 7. 本轮状态与自审"+chr(10)*2
reviewtext=("固定BECA评价完整取包、全部决定复算与90图视觉检查已完成。后续只读诊断复算122状态／8约束，"
            "最终PNG／SVG图实际查看；绘图作业130920／130921完成，新增模型前向为0。论文v2正文全部复读并核对10行结果、15项主张；"
            "v1和此前冻结实验证据未改。今天新访问观察没有COM6或当前网段22／9090候选，不据此判断原SD数据丢失。"
            +link("外来源评价自审","beca_fixed_transfer_20261030/Review与当前状态.md")+"、"
            +link("诊断自审","beca_score_diagnosis_20261031/Review与当前状态.md")+"和"
            +link("论文v2自审","paper_readiness_20261030/Review与当前状态_v2.md")+"。")
assert s.count(needle)==1;s=s.replace(needle,needle+reviewtext+chr(10)*2,1)
s=s.replace("未来先隔离受影响ID与已见QA身份11／65／100，再冻结相应日期及已知／未知划分；原标签未改。","固定迁移阶段已隔离受影响ID与已见QA身份11／65／100，在取图前冻结相应日期及已知／未知划分；原标签未改。")
main.write_text(s,encoding="utf-8")
diff=[]
for p in paths:
    diff+=list(difflib.unified_diff(before[p].splitlines(),p.read_text(encoding="utf-8").splitlines(),
                                 fromfile=str(p.relative_to(PROJECT))+" v20",tofile=str(p.relative_to(PROJECT))+" v21",n=2))
diff_path=ROOT/"results/overview_diff_20261031_v21_transfer.txt";assert not diff_path.exists()
diff_path.write_text(chr(10).join(diff)+chr(10),encoding="utf-8")
out=ROOT/"results/entrypoint_update_20261031_v21_transfer.json";assert not out.exists()
value={"status":"FIVE_ENTRYPOINTS_UPDATED_WITH_COMPLETED_EXTERNAL_TRANSFER_POSTHOC_LIMITS_V2_DRAFT_AND_NEW_ACCESS_OBSERVATION",
       "created_UTC":datetime.now(timezone.utc).isoformat(),"previous_files_and_snapshots":snapshots,
       "current_entrypoints":[{"path":str(p),"sha256":sha(p)}for p in paths],
       "diff":{"path":str(diff_path),"sha256":sha(diff_path)},
       "new_review_sources":[{"path":str(p),"sha256":sha(p)}for p in review_paths],
       "whole_goal_complete":False}
out.write_text(json.dumps(value,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"status":value["status"],"main_lines":len(s.splitlines()),"diff_lines":len(diff)}))
