from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,difflib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
link=lambda label,name:f"[{label}](<{(PROJECT/name).as_posix()}>)"
old=load(ROOT/"results/overview_review_20261031_v21_transfer.json")
main=PROJECT/"研究阶段总结_20261030.md";assert sha(main)==old["document"]["sha256"]
complete_path=PROJECT/"identity_trigger_pair_20261030/results/final_review_recovered_v2.json"
paper_path=PROJECT/"paper_readiness_20261030/results/manuscript_review_v3.json"
complete,paper=map(load,[complete_path,paper_path])
assert complete["actual_counts"]==[10,10,8,7]and complete["all4_original_terminal_and_raw_results_received"]
assert complete["board_access_restored"]and paper["actual_trigger_originals_obtained"]and not paper["ready_for_submission"]
paths=[main,PROJECT/"研究总览_从想法到论文.md",PROJECT/"研究进度.md",
       PROJECT/"phase3_diagnosis_20261026/方案与执行状态.md",ROOT/"Review与当前状态.md"]
backup=ROOT/"snapshots/overview_v21_before_board_result_recovery";backup.mkdir(parents=True,exist_ok=False)
before={};snapshots=[]
for p in paths:
    before[p]=p.read_text(encoding="utf-8");dest=backup/p.relative_to(PROJECT)
    dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(p.read_bytes())
    snapshots.append({"path":str(p),"snapshot":str(dest),"sha256":sha(dest)})
report=link("实际计数触发四轮恢复结果","identity_trigger_pair_20261030/实际计数触发四轮恢复结果与时序取舍.md")
access=link("USB与网络恢复记录","pynq_access_resume_20261031/USB与网络恢复记录.md")
draft=link("论文草稿v3","paper_readiness_20261030/论文方法与实验草稿_v3.md")
latest=("2026年10月31日恢复进展："+access+"已确认192.168.3.100的SSH与Jupyter可用，主机密钥与原板一致。"
        +report+"完整原包已取回，原四轮计数10／10／8／7，处理率4.630／4.770／4.643／4.630；"
        "35实际身份任务、1464定时O8输出、26照片、8596观察／8计数路径及89次CPU参考全部核验。"
        "本次没有重跑板端或加载O8来补原终态；新boot与原实验boot分开记录。"
        "稳定全链路5FPS、独立逐事件、原12事件永久牛号和论文贡献仍未完成。"
        +draft+"已接回完整证据，v1／v2保留。")
for p in paths[1:]:
    head,rest=before[p].split(chr(10),1);rest=rest.lstrip(chr(10))
    assert rest.startswith("2026年10月31日最新：")
    rest=rest.replace("2026年10月31日最新：","此前外来源评价阶段：",1)
    extra=" "+link("第22版恢复复核","research_synthesis_20261027/results/overview_review_20261031_v22_recovery.json")+"。"if p==ROOT/"Review与当前状态.md"else""
    p.write_text(head+chr(10)*2+latest+extra+chr(10)*2+rest,encoding="utf-8")
s=before[main];at=s.index("2026年10月31日最新：")
s=s[:at]+latest+chr(10)*2+s[at:]
at=s.index("**当前进展：");end=s.index("**",at+2)+2
s=s[:at]+("**当前进展：板卡访问已恢复，原四轮实际计数触发结果全部取回并复核，计数10／10／8／7、处理率4.630–4.770FPS，"
           "尚未达到稳定完整5FPS。Cows新模型Top-1为30／30但只自动接受3／30；BECA固定迁移仍未知误收26／30。"
           "当前主要缺口转为独立事件与永久牛号、输入／调度的匹配控制、真实相机／RFID和功耗；论文草稿v3已更新，整体目标继续。**")+s[end:]
oldrow="| 新实际触发阶段（待核验） | 只取回前三轮摘要10／10／8；第四轮至少350帧 | 恢复SD结果，核对raw／轨迹／照片和第四轮终态 |"
newrow="| 实际计数触发四轮已完整核验 | 10／10／8／7；4.630–4.770FPS，35任务、原包及CPU参考通过 | 仍低于5FPS与人工12；逐事件／永久牛号缺失，任务负载不完全配对 |"
assert s.count(oldrow)==1;s=s.replace(oldrow,newrow)
needle="### 3.12 实际计数触发对照：部分摘要保留，原始结果待恢复"+chr(10)*2
assert s.count(needle)==1;s=s.replace(needle,needle+"以下为失联时点的保留记录；原始结果已于第3.14节接回，不以本段旧状态覆盖恢复后的完整核验。"+chr(10)*2,1)
section=f"""### 3.14 访问恢复后取回原四轮：完整结果通过，系统目标仍待达成

{access}捕获SD启动和约45秒的自行复位记录，随后用户提供192.168.3.100并确认DONE亮。SSH固定主机密钥一致，Jupyter登录页HTTP200；没有修改网络或重刷SD。当前boot e7059099与原实验boot9ecd4ca1不同，不把当前FPGA operating等同原O8驻留，供电根因仍未被测量证实。

{report}原包12,260,384字节、163成员／162清单完整取回。原完整record／terminal hash一致，旧RUNNING进度350帧只是历史快照。采集器执行一次、原实验没有重跑，23个绑定运行文件hash仍匹配。

| 原轮次 | 处理／392 | 跳过 | >200ms | 处理率FPS | 释放至计数P95ms | 计数／人工12 | 身份任务／接受 |
|---|---:|---:|---:|---:|---:|---:|---|
| r1_old | 363 | 29 | 273 | 4.630 | 429.31 | 10 | 10／1 |
| r1_new | 374 | 18 | 124 | 4.770 | 334.10 | 10 | 10／0 |
| r2_new | 364 | 28 | 285 | 4.643 | 393.94 | 8 | 8／0 |
| r2_old | 363 | 29 | 208 | 4.630 | 445.17 | 7 | 7／0 |

全部1568次JPEG生产与1464前台接收／raw、35张运行时照片和模型输入、202候选观察、8596时刻／8计数路径已复算。26唯一PNG全部5页实际查看；6个字面事件配对、23未配对任务、3对同照片分别保留，不以临时ID认定永久牛。接受1个候选不升级为正确找回。

完整关联重放精确匹配事件与临时ID；89次Torch参考（29唯一模型输入＋两套30图库）核对116固定决定，最大归一化差4.046e-6。参考130922因漏一份已冻结脚本在推理前失败，补同文件后130923完成0:0；首次过早下载半包隔离，等待归档终态后重取完整16,263,209字节参考包，没有重复推理。原阶段1519板端图前向与本次89CPU分别计，恢复板端新增0。

该配置未达5FPS，四轮总量误差2／2／4／5仍不能拆成具体漏计；固定10照片接近5FPS的阶段不替代实际触发负载。{draft}将C09更新为已核验的回放系统结果，C10／C11／C12继续待证据。

"""
needle="## 4. 数据还需要怎样补";assert s.count(needle)==1;s=s.replace(needle,section+needle,1)
oldstep="3. 实际计数触发的四次对照已启动，当前只保存前三轮摘要与第四轮进度，阶段未验收。恢复SD启动／USB后只读检查原任务和boot ID，取回所有已有原始结果；完整保存才做四轮评分，部分保存就报告实际范围，不补跑或替换。实际照片参考、关联重放和后台等待都须取包后验证。"
newstep="3. 实际计数触发四轮原包、数值、照片CPU参考和完整关联重放均已完成验收；保留10／10／8／7及全部迟到／跳过。下一步按独立事件参考定位质量差异，并以相同输入取得和明确任务负载做时序控制；不重跑替换原结果，也不把较少身份任务当效率改进。"
assert s.count(oldstep)==1;s=s.replace(oldstep,newstep)
s=s.replace("6. "+link("论文草稿v2","paper_readiness_20261030/论文方法与实验草稿_v2.md")+"已加入BECA固定迁移、日期疑点及事后单阈值上界；"+link("15项主张证据表","paper_readiness_20261030/论文主张与证据对应_v2.md")+"继续绑定已完成与未完成证据。补齐真实事件、原实机结果和具体贡献后再定最终结论及目标刊会，当前不是投稿终稿。",
            "6. "+draft+"已接入完整实际触发结果；"+link("15项主张证据表v3","paper_readiness_20261030/论文主张与证据对应_v3.md")+"将C09转为已核验回放结果，事件身份、真实输入／稳定5FPS与创新贡献仍待证据。文稿不是投稿终稿。")
needle="## 7. 本轮状态与自审"+chr(10)*2
extra=("本轮恢复了板卡访问并完整取回此前原结果，未重跑原板端；原1464检测／35任务、26照片、完整跟踪和89次CPU参考全部复核。"
       "两个可避免的打包／取包问题已保存并修正，最终原包和参考包SHA／清单均通过。论文v3完整复读，14行数字和15项主张核查；"
       "旧稿与失联证据保留，供电故障原因未认领。"
       +link("恢复后完整自审","identity_trigger_pair_20261030/Review与恢复后当前状态.md")+"。")
assert s.count(needle)==1;s=s.replace(needle,needle+extra+chr(10)*2,1)
main.write_text(s,encoding="utf-8")
diff=[]
for p in paths:
    diff+=list(difflib.unified_diff(before[p].splitlines(),p.read_text(encoding="utf-8").splitlines(),
                                 fromfile=str(p.relative_to(PROJECT))+" v21",tofile=str(p.relative_to(PROJECT))+" v22",n=2))
diff_path=ROOT/"results/overview_diff_20261031_v22_recovery.txt";assert not diff_path.exists();diff_path.write_text(chr(10).join(diff)+chr(10),encoding="utf-8")
record={"status":"FIVE_ENTRYPOINTS_UPDATED_COMPLETE_ORIGINAL_TRIGGER_RECOVERY_WITH_UNMET_TARGETS",
        "created_UTC":datetime.now(timezone.utc).isoformat(),"previous_files_and_snapshots":snapshots,
        "current_entrypoints":[{"path":str(p),"sha256":sha(p)}for p in paths],"diff":{"path":str(diff_path),"sha256":sha(diff_path)},
        "new_review_sources":[{"path":str(p),"sha256":sha(p)}for p in[complete_path,paper_path]],"whole_goal_complete":False}
out=ROOT/"results/entrypoint_update_20261031_v22_recovery.json";assert not out.exists();out.write_text(json.dumps(record,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"status":record["status"],"main_lines":len(s.splitlines()),"diff_lines":len(diff)}))
