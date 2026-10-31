from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old_review=load(ROOT/"results/manuscript_review_v2.json")
for row in old_review["documents"]+old_review["source_files"]+old_review["tools"]:assert sha(Path(row["file"]))==row["sha256"]
ledger_path=ROOT/"results/claim_ledger_v2.json";ledger=load(ledger_path)
stage=PROJECT/"identity_trigger_pair_20261030"
new_sources={
 "actual_trigger_verified":stage/"results/independent_verification.json",
 "actual_trigger_reference":stage/"results/reference_independent_verification.json",
 "actual_trigger_archive":stage/"results/recovery_archive_verification_v2.json",
 "actual_trigger_complete_review":stage/"results/final_review_recovered_v2.json"}
review=load(new_sources["actual_trigger_complete_review"])
assert review["actual_counts"]==[10,10,8,7]and review["raw_event_photo_numeric_verification_complete"]
assert review["Torch_reference_image_forwards"]==89 and not review["full5FPS_target_achieved"]
ledger["created_UTC"]=datetime.now(timezone.utc).isoformat()
ledger["status"]="V3_CLAIMS_BIND_RECOVERED_COMPLETE_ACTUAL_TRIGGER_STAGE_WITH_UNMET_TIMING_AND_GROUND_TRUTH_GATES"
ledger["previous_ledger"]={"file":str(ledger_path.resolve()),"sha256":sha(ledger_path)}
ledger["sources"] += [{"name":name,"file":str(path.resolve()),"sha256":sha(path)}for name,path in new_sources.items()]
claim=next(c for c in ledger["claims"]if c["ID"]=="C09")
claim.update({
 "status":"supported_actual_replay_system_unmet_target",
 "statement":"实际计数触发四轮原结果完整取回并复算；计数10／10／8／7、处理率4.630–4.770，35身份任务，未达到稳定5FPS。",
 "source":"actual_trigger_verified","fields":["cases","backgrounds","actual_background_identity_jobs","actual_O8_timed_forwards"],
 "unit":"4same-source repeats,392offered200ms slots perrun; original1519board image forwards,CPU reference89separately",
 "limits":"实际JPEG读取＋模拟RF全未读；当前新boot的PL不作原状态推断；缺独立事件／永久牛号，任务与照片变化，不能据此认领方法优越性。"})
ledger["numbers"]["actual_trigger_counts"]=[10,10,8,7]
ledger["numbers"]["actual_trigger_timed_O8"]=1464
ledger["numbers"]["actual_trigger_jobs"]=35
ledger["numbers"]["actual_trigger_CPU_reference_forwards"]=89
ledger["actual_trigger_originals_obtained"]=True
ledger["ready_for_submission"]=False;ledger["whole_goal_complete"]=False
out=ROOT/"results/claim_ledger_v3.json";assert not out.exists();out.write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
claims=(ROOT/"论文主张与证据对应_v2.md").read_text(encoding="utf-8")
claims=claims.replace("v2（v1保留）","v3（v1／v2保留）").replace("results/claim_ledger_v2.json","results/claim_ledger_v3.json")
start=claims.index("| C09 |");end=claims.index(chr(10),start)
line="| C09 | "+claim["status"]+" | "+claim["statement"]+" [actual_trigger_verified](<"+new_sources["actual_trigger_verified"].as_posix()+">) | "+claim["limits"]+" |"
claims=claims[:start]+line+claims[end:]
old="完整四轮实际触发原始数据是下一项验收，不由固定10照片控制替代。板卡恢复后先读取SD原任务、核验boot与终态，保持已冻结输入／权重／阈值；之后完成实际照片的CPU参考和完整关联重放。"
new="实际触发四轮原始数据、实际照片CPU参考和完整关联重放均已完成核验，补齐了C09。该配置仍有迟到、跳过和总量不足；下一项验收为独立事件参考与永久牛号对应，再按匹配条件定位和控制时序瓶颈。"
assert claims.count(old)==1;claims=claims.replace(old,new)
claims=claims.replace("；实际触发四轮待取回；具体新贡献尚需与最近工作对应并验证。","；实际触发四轮已完整核验但未达5FPS及人工12总量；具体新贡献尚需与最近工作对应并验证。")
out=ROOT/"论文主张与证据对应_v3.md";assert not out.exists();out.write_text(claims,encoding="utf-8")
paper=(ROOT/"论文方法与实验草稿_v2.md").read_text(encoding="utf-8")
paper=paper.replace("v0.2。v0.1保留为当时的结果快照。","v0.3。v0.1／v0.2保留为当时的结果快照。")
paper=paper.replace("论文主张与证据对应_v2.md","论文主张与证据对应_v3.md").replace("claim_ledger_v2.json","claim_ledger_v3.json")
needle="计数均为10，人工确认总量为12。"
assert paper.count(needle)==1
paper=paper.replace(needle,"计数均为10，人工确认总量为12。随后完整取回的实际计数触发四轮处理率为4.630–4.770帧/秒，计数为10、10、8、7，35项后台身份任务完成。",1)
paper=paper.replace("第三个问题的实际计数触发四轮原始记录尚待从SD卡取回，本文结果表只使用已经完整取包并复算的实验。",
                    "实际计数触发四轮原始记录现已完整取回，本文将其与固定后台负载分别报告；各阶段只使用已完整取包并复算的结果。")
paper=paper.replace("实际触发阶段的照片、时间因果关系和完整后台结果仍待原始记录核验。",
                    "实际触发阶段的35份照片、时间因果关系和后台结果已核验；完整事件的身份正确性仍需永久牛号参考。")
paper=paper.replace("| 实际计数触发 | 冻结四轮方案；当前保存部分主机摘要 | 待取回原始数据后验收，未纳入正式结果 |",
                    "| 实际计数触发 | 四轮392时隙；1464实际检测、35后台任务 | 原文件、照片、因果时序、关联及CPU特征核验完成；同源重复 |")
paper=paper.replace("其低分辨率输入仍为已就绪回放，完整结果待核验。",
                    "其低分辨率输入仍为已就绪回放，完整结果现已核验。")
start=paper.index("### 5.5 实际触发实验的待验收项目")
end=paper.index("### 5.6 固定模型的外来源迁移",start)
section="""### 5.5 实际计数触发的完整四轮结果

原boot中的旧／新／新／旧四次运行已完整取回，恢复本身没有重跑板端。异步生产者实际读取每个释放帧的高分JPEG，按当次计数触发因果取图与身份检索。全部采用low_priority_parallel，模拟RF全未读；没有强制每轮10个身份任务。主阈值仍为通道共用历史阈值0.8445389603236383。[原结果与完整核验](../identity_trigger_pair_20261030/实际计数触发四轮恢复结果与时序取舍.md)

| 轮次／身份 | 处理 /392 | 跳过 | 已处理帧迟到 | 处理率 /帧·s⁻¹ | 释放至计数P95 /ms | 计数 | 身份任务 |
|---|---:|---:|---:|---:|---:|---:|---:|
| r1_old | 363 | 29 | 273 | 4.630 | 429.31 | 10 | 10 |
| r1_new | 374 | 18 | 124 | 4.770 | 334.10 | 10 | 10 |
| r2_new | 364 | 28 | 285 | 4.643 | 393.94 | 8 | 8 |
| r2_old | 363 | 29 | 208 | 4.630 | 445.17 | 7 | 7 |

最长入队至身份结果分别为2037.62、2563.73、2020.19和1617.85毫秒，主阈值接受数1、0、0、0。接受项无永久牛号参考，身份正确性未知。35任务对应26张不同PNG和29个模型—tensor输入；只有6个事件JSON字面配对，其中3对同照片，其他23个未配对任务全部保留。任务少可能来自前台计数不足，不能将较短后台等待直接认领效率改善。

1464份实际raw、8596个含历史观察时刻、8条计数路径和202个几何候选观察已复算；完整关联重放的临时ID及事件一致。29查询与两套各30图库的89次CPU参考验证116项固定决定，归一化最大差4.046×10⁻⁶。1568次生产者读取及1464次接收时间核查，1160次处理帧存在模型与I/O重叠。该配置仍未达到完整5FPS，计数与人工12的总量差为2、2、4、5，缺逐事件参考时不拆成具体漏计数。

原包12,260,384字节、163成员／162清单完整保存；恢复时boot已变化，原PL_after记录与当前运行文件hash分开核查，没有重新加载O8来证明旧终态。当前设备访问恢复不增加独立测试会话或新的板端前向。[恢复原包范围](../identity_trigger_pair_20261030/results/recovery_archive_verification_v2.json)

"""
paper=paper[:start]+section+paper[end:]
old="先取回实际触发原始记录，完成实际照片CPU参考、关联重放、因果取图和后台时序复算。若只保存了部分运行，就按完整保存的范围报告，保留中断原因和分母。独立事件JSON到达后，将计数及每个RF异常事件统一匹配，报告方向、C/W/U/M和额外虚假事件。"
new="实际触发原始记录、实际照片CPU参考、关联重放与后台时序复算已完成。下一步接收独立事件JSON，将计数及每个RF异常事件统一匹配，报告方向、C/W/U/M与额外虚假事件；之后以相同输入取得方式及明确任务负载检验时序改动，保留迟到和跳帧。"
assert paper.count(old)==1;paper=paper.replace(old,new)
paper=paper.replace("BECA评价的180次CPU图前向另按其原始记录计算。",
                    "BECA评价的180次与实际触发参考的89次CPU图前向分别按原始记录计算。")
out=ROOT/"论文方法与实验草稿_v3.md";assert not out.exists();out.write_text(paper,encoding="utf-8")
review_text="""# 论文v3：接回原实际触发证据

2026-10-31。v3补齐实际计数触发四轮的原始数据验收，C09从待取回更新为已支持的回放系统结果；该配置未达5FPS及人工总量12。v1／v2正文和自审记录继续保留。

新摘要、方法时序、完整结果表与下一步均按恢复后的证据更新；逐项核对1464检测、35任务、8596观察、89次CPU参考及接受／计数分母。原boot终态、恢复新boot、当前文件hash与未观察的当前overlay身份分别说明，没有以重新上板替代原结果。

未完成项继续为独立事件、原12通行永久牛号、真实输入／功耗／长期运行及具体论文贡献；文稿不是投稿终稿。固定10照片、实际动态任务和BECA外来源的各自分母、阈值、时间与标签边界均保留。

完整复读新正文和变更表格，局部链接与SHA另行绑定。文稿更新增加0模型前向；原1519板端、此前180次BECA CPU及本次89次参考分开计算。[v3结构化复核](results/manuscript_review_v3.json)
"""
out=ROOT/"Review与当前状态_v3.md";assert not out.exists();out.write_text(review_text,encoding="utf-8")
print(json.dumps({"claims":len(ledger["claims"]),"bound_sources":len(ledger["sources"]),"C09_supported":True,"pending_claims":[c["ID"]for c in ledger["claims"]if c["status"].startswith("pending")],"ready_for_submission":False}))
