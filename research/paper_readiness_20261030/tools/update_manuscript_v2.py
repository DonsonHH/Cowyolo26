"""Create v2 without mutating the hash-bound v1 draft or completed result records."""
from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
load=lambda p:json.loads(p.read_text(encoding="utf-8-sig"))
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
old_review=load(ROOT/"results/manuscript_review_v1.json")
for r in old_review["documents"]+old_review["tools"]:assert sha(Path(r["file"]))==r["sha256"]
old_ledger=ROOT/"results/claim_ledger_v1.json";ledger=load(old_ledger)
sources={
    "BECA_fixed_transfer":PROJECT/"beca_fixed_transfer_20261030/results/independent_verification.json",
    "BECA_visual_dates":PROJECT/"beca_fixed_transfer_20261030/results/visual_review.json",
    "BECA_score_oracle":PROJECT/"beca_score_diagnosis_20261031/results/score_diagnosis_v1.json",
    "BECA_score_recalculation":PROJECT/"beca_score_diagnosis_20261031/results/independent_verification_v1.json"}
transfer=load(sources["BECA_fixed_transfer"]);diagnosis=load(sources["BECA_score_oracle"])
assert [[r[k]for k in["known_Top1","C","W","U","unknown_FA"]]for r in transfer["main_outcomes"]]==[[14,13,15,2,26],[15,13,11,6,26]]
assert [diagnosis["models"][name]["constrained_correct_acceptance_upper_bounds"]["zero_observed_W_and_FA"]["max_C"]for name in["old_C","new_C_domain_seed26"]]==[1,3]
ledger["created_UTC"]=datetime.now(timezone.utc).isoformat()
ledger["status"]="V2_CLAIMS_INCLUDE_COMPLETED_EXTERNAL_TRANSFER_AND_SEPARATELY_LABELLED_POSTHOC_THRESHOLD_BOUND"
ledger["previous_ledger"]={"file":str(old_ledger.resolve()),"sha256":sha(old_ledger)}
ledger["sources"] += [{"name":name,"file":str(path.resolve()),"sha256":sha(path)}for name,path in sources.items()]
ledger["claims"] += [
    {"ID":"C13","status":"supported_external_component_under_publisher_labels",
     "statement":"BECA固定20ID／90图迁移评价中，旧／新Top-1为14／30、15／30，主工作点未知FA均26／30；新mAP48.50%，旧51.46%。",
     "source":"BECA_fixed_transfer","fields":["main_outcomes"],"unit":"30 registered and30 unknown query images,10publisher IDs each; filename-based chronological split",
     "limits":"肉牛饲喂区作者OBB；已隔离15冲突ID及3QA身份；其余作者标签未独立认证；不提供通道身份或实机时序。"},
    {"ID":"C14","status":"supported_date_discrepancy_not_resolved",
     "statement":"索引40、41的文件名日期与原图相机叠字日期不一致；本轮日期间隔只按文件名定义。",
     "source":"BECA_visual_dates","fields":["filename_camera_date_discrepancy_examples"],"unit":"2 observed examples, not a complete dataset timestamp audit",
     "limits":"未判定哪一时钟正确；不改日期、不排除或重跑；不认领已验证真实跨日52–167天。"},
    {"ID":"C15","status":"supported_posthoc_observed_set_bound_not_calibration",
     "statement":"在BECA保存分数全部可达最高余弦阈值中，若W=FA=0，旧／新最大正确接受仅1／30和3／30。",
     "source":"BECA_score_oracle","fields":["models.*.constrained_correct_acceptance_upper_bounds.zero_observed_W_and_FA"],
     "unit":"2x61 reachable observed decision states; bound uses evaluation labels after scoring",
     "limits":"事后诊断；未选择部署门限，不构成独立校准或总体风险保证。"}]
ledger["numbers"]["BECA_primary_outcomes"]=transfer["main_outcomes"]
ledger["numbers"]["BECA_zero_observed_error_max_C"]=[1,3]
out=ROOT/"results/claim_ledger_v2.json";assert not out.exists()
out.write_text(json.dumps(ledger,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
old_claims=(ROOT/"论文主张与证据对应.md").read_text(encoding="utf-8")
claims=old_claims.replace("2026年10月30日。","2026年10月31日，v2（v1保留）。",1).replace("results/claim_ledger_v1.json","results/claim_ledger_v2.json")
added=chr(10).join("| "+r["ID"]+" | "+r["status"]+" | "+r["statement"]+
                    " ["+r["source"]+"](<"+Path(sources[r["source"]]).as_posix()+">) | "+r["limits"]+" |"for r in ledger["claims"][-3:])
needle="| C12 |";at=claims.index(chr(10),claims.index(needle));claims=claims[:at]+chr(10)+added+claims[at:]
needle="完整四轮实际触发原始数据是下一项验收"
at=claims.index(needle)
claims=claims[:at]+"新增外来源结果已否定“原Cows阈值可直接维持低误收”的推广：BECA两模型FA均26／30；事后最高余弦阈值的零观察错误覆盖也很低。具体原因尚未由控制实验确定，不把它改写成毛色或硬件的因果结论。"+chr(10)*2+claims[at:]
out=ROOT/"论文主张与证据对应_v2.md";assert not out.exists();out.write_text(claims,encoding="utf-8")
old=(ROOT/"论文方法与实验草稿.md").read_text(encoding="utf-8");paper=old
paper=paper.replace("版本：2026-10-30，v0.1。","版本：2026-10-31，v0.2。v0.1保留为当时的结果快照。",1)
paper=paper.replace("论文主张与证据对应.md","论文主张与证据对应_v2.md").replace("results/claim_ledger_v1.json","results/claim_ledger_v2.json")
needle="这些结果把候选检索、自动接受和完整系统时序分开评价，为后续实际事件触发与真实输入验证提供依据。"
replacement="另一次按BECA作者文件名日期划分的外来源评价中，旧／新编码器Top-1为14/30和15/30，主工作点均误接受26/30张未登记查询。这些结果把候选检索、拒识迁移与系统时序分开评价，说明目标域身份验证和完整事件证据是进一步部署的必要条件。"
assert paper.count(needle)==1;paper=paper.replace(needle,replacement)
needle="| 同90图ARM核验 |"
at=paper.index(needle)
paper=paper[:at]+"| BECA固定模型迁移 | 另10注册、10未知ID；30图库＋30已登记查询＋30未知查询，90作者OBB图 | 来源、角色、日期与代码在取图前冻结；按作者ID评分，日期按文件名 |"+chr(10)+paper[at:]
needle="## 6. 讨论与适用范围"
new_section="""### 5.6 固定模型的外来源迁移

从BECA合并身份目录选择20个新发布方ID，先隔离15个冲突线索ID与3个已见QA身份。三个牛舍均含注册与未知角色，每个角色内取不同文件名日期；图库与查询文件名日期间隔52–167天。输入、两个既有权重、预处理和全部工作点在请求对应图像成员前冻结，没有BECA训练或新阈值校准。该数据为肉牛饲喂区的作者OBB裁剪，作为外来源压力检验。[固定协议与完整报告](../beca_fixed_transfer_20261030/固定模型外来源结果与阈值失配.md)

| 编码器 | 已登记Top-1 /30 | 图像检索mAP | C /30 | W /30 | U /30 | 未登记FA /30 |
|---|---:|---:|---:|---:|---:|---:|
| 原编码器 | 14 | 51.46% | 13 | 15 | 2 | 26 |
| 新域编码器，种子26 | 15 | 48.50% | 13 | 11 | 6 | 26 |

该表使用与第5.1节相同的各模型主阈值；mAP对已登记查询在30张图库图中计算，正例为该身份3图。原／新模型的未知误收均86.67%，正确自动接受同为13/30。新减旧Top-1为3.33个百分点，按ID且保持牛舍组成的2000次bootstrap百分位95%区间为−6.67至13.33；mAP差为−2.97个百分点，区间−11.58至6.96。既有较高阈值约0.87075下，新模型仍误收13/30，正确接受降至7/30。全部8工作点、180次CPU图前向和480决定已完整取包并独立复算，不据此换主工作点。[原始摘要](../beca_fixed_transfer_20261030/delivery/results/evaluation/summary.json)

所有90图实际查看后发现，至少两图的文件名日期与相机叠字日期不一致，尚未确定哪个时钟正确。因此该评价只按文件名日期定义时间隔离，发布方ID也未得到本项目的独立人工认证；保留原评分并报告疑点。[视觉与日期记录](../beca_fixed_transfer_20261030/results/visual_review.json)

### 5.7 已保存分数的事后阈值诊断

对BECA两模型分别枚举最高余弦阈值的全部61个可达接受状态，若要求观察到的已登记误认W和未知误收FA均为0，原／新模型最多正确接受1/30和3/30。这个上界使用了已评分标签，属于事后诊断，不是独立校准或新的部署门限；它说明单一最高分门限在该批固定预测上存在严重覆盖取舍。[完整状态与独立复算](../beca_score_diagnosis_20261031/results/independent_verification_v1.json)

"""
assert paper.count(needle)==1;paper=paper.replace(needle,new_section+needle,1)
needle="当前结果支持两个分开的判断：体纹候选可以在该公开划分上改善，且同一编码器可在PYNQ-Z2复现；自动接受覆盖和完整时序仍决定系统是否有用。"
replacement="当前结果显示，Cows划分的候选排序改善和同输入ARM复现可以成立，同时BECA的固定门限迁移表现出高误收。身份结果的适用范围依赖目标域、注册图库和拒识协议；两个来源不能据此当作训练因素完全匹配的因果对照。自动接受覆盖和完整时序仍决定系统是否有用。"
assert paper.count(needle)==1;paper=paper.replace(needle,replacement)
needle="当前缺少该12事件的独立逐事件参考及永久牛号映射；"
at=paper.index(needle)
paper=paper[:at]+"BECA已隔离已知冲突ID，但剩余标签和真实日期尚待独立核实，体纹以外背景／相机字样的作用也尚未由消融确定。本次20ID现已用于评分；后续若据此改变方法，需要新的独立材料。"+chr(10)*2+paper[at:]
paper=paper.replace("[claim_ledger_v1.json](results/claim_ledger_v2.json)","[claim_ledger_v2.json](results/claim_ledger_v2.json)")
paper=paper.replace("身份图库和查询按ID及日期规则选择，注册/查询日期至少相隔7天；","Cows保留身份的图库和查询按ID及日期规则选择，注册/查询日期至少相隔7天；")
paper=paper.replace("本稿没有新增训练或模型前向。","本次稿件整理没有新增训练或模型前向；BECA评价的180次CPU图前向另按其原始记录计算。")
paper=paper.replace("## 6. 讨论与适用范围","![BECA保存分数的事后诊断；不是新部署门限](../beca_score_diagnosis_20261031/results/figures_v2/threshold_score_overlap.png)"+chr(10)*2+"## 6. 讨论与适用范围")
out=ROOT/"论文方法与实验草稿_v2.md";assert not out.exists();out.write_text(paper,encoding="utf-8")
newreview="""# 论文草稿v2自审与当前状态

2026-10-31。v2增加固定BECA外来源结果及另行标明的事后单分数阈值诊断；v1正文、主张表、原校验与来源报告保留。原Cows、同90图ARM和固定负载结果保持原范围。

新增正文和所有改动已完整复读，数字逐表对照原始结果。BECA高误收、不利mAP、作者标签边界、文件名日期与原相机叠字不一致都进入结果和讨论，没有把它们改成主方法性能改进。C13/C14/C15分开固定迁移结果、日期疑点与事后观察集上界。

当前未完成项继续：PYNQ-Z2实际触发四轮原始结果、独立逐事件参考、原12事件永久牛号及真实输入验证；论文创新点也未由匹配对照确立。v2不是可投稿终稿。论文整理新增推理和训练为0；BECA固定评价此前180次CPU图前向另有完整证据，事后诊断0前向。

新的本地链接、主张来源SHA及正文数值在v2结构化复核中绑定；v1检查只对应保留的v1。没有更改权重、门限、作者标签或实验原文件。[v2结构化复核](results/manuscript_review_v2.json)
"""
out=ROOT/"Review与当前状态_v2.md";assert not out.exists();out.write_text(newreview,encoding="utf-8")
print(json.dumps({"new_claims":len(ledger["claims"]),"bound_sources":len(ledger["sources"]),"old_v1_preserved":True,"new_model_forwards":0}))
