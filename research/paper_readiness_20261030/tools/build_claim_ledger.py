from pathlib import Path
from datetime import datetime,timezone
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
sources={
 'identity_CPU':PROJECT/'identity_final20_20261030/delivery/results/evaluation/summary.json',
 'identity_ARM':PROJECT/'identity_final20_arm_20261030/results/independent_verification.json',
 'fixed_workload':PROJECT/'identity_joint_pair_20261030/results/independent_verification.json',
 'detector_sizes':PROJECT/'pynq_o8_sizes_20261030/results/final_review.json',
 'detector_video':PROJECT/'pynq_mosaic192_eval_20261030/results/final_review.json',
 'training':PROJECT/'identity_domain_adapt_20261030/results/final_review.json',
 'actual_trigger_partial':PROJECT/'identity_trigger_pair_20261030/results/partial_observation_v1.json'}
values={key:load(p)for key,p in sources.items()}
cpu=values['identity_CPU'];arm=values['identity_ARM'];fixed=values['fixed_workload'];video=values['detector_video'];train=values['training'];sizes=values['detector_sizes'];partial=values['actual_trigger_partial']
known=[r for r in cpu['outcomes']if r['policy']=='primary_cal10_fold0'];assert [[r[k]for k in['known_Top1','C','W','U','unknown_FA']]for r in known]==[[22,10,2,18,3],[30,3,0,27,0]]
assert arm['actual_ARM_network_calls']==184 and arm['fixed_decisions']==480 and arm['decision_changes']==0
assert [r['source_down_count']for r in fixed['cases']]==[10,10,10,10]
assert [r['processed_frames']for r in fixed['cases']]==[392,390,390,392]
assert video['FP32_QDQ_actual_O8_original_counts']==[10,10,10]
assert partial['fourth_case_terminal_observed']is False
claims=[
 {'ID':'C01','status':'supported_component','statement':'两套固定编码器在PYNQ-Z2上复现同90图的排名及8工作点接受决定。','source':'identity_ARM','fields':['actual_ARM_measured_forwards','actual_ARM_warmup_forwards','fixed_decisions','decision_changes'],'unit':'180model-image forwards,4warmups,480decisions; one cohort repeated on ARM','limits':'实现一致性；同90图不算第二个独立测试。'},
 {'ID':'C02','status':'supported_component','statement':'在10注册ID的30张查询中，新域编码器Top-1为30/30，旧编码器22/30。','source':'identity_CPU','fields':['outcomes[primary_cal10_fold0].known_Top1'],'unit':'query image;10known identities with3queries each','limits':'Cows命名空间保留ID、同场景作者裁剪；不是任意牧场100%识别。'},
 {'ID':'C03','status':'supported_tradeoff','statement':'新编码器主阈值下C3/W0/U27、未知FA0/30，旧编码器C10/W2/U18、未知FA3/30。','source':'identity_CPU','fields':['outcomes[primary_cal10_fold0]'],'unit':'known query30 and unknown query30 separately','limits':'新模型正确自动接受覆盖10%；零错误观察不保证总体零风险。'},
 {'ID':'C04','status':'supported_system_control','statement':'固定10照片负载时，四次处理率为5.000/4.974/4.974/5.000，迟到80/69/67/76，均计数10。','source':'fixed_workload','fields':['cases[].processed_per_second_over_offered_duration','cases[].deadline_misses','cases[].source_down_count'],'unit':'processed frames divided by392offered slots x200ms;78.4s per run','limits':'两次同源设备重复；固定任务独立于本次计数，没有现场双流或永久身份GT。'},
 {'ID':'C05','status':'supported_isolated_timing','statement':'同90图的新编码器纯网络均值150.35ms、P95 151.66ms。','source':'identity_ARM','fields':['timings.new_C_domain_seed26.network_mean_ms','timings.new_C_domain_seed26.network_P95_ms'],'unit':'ready224tensor to576feature return','limits':'先预处理、旧后新、无O8并发；不是完整任务或系统FPS。'},
 {'ID':'C06','status':'supported_isolated_timing','statement':'统一O8的256和320受控向量均值235.55/370.93ms，超过200ms预算。','source':'detector_sizes','fields':['s256_mean_tensor_to_raw_ms','s320_mean_tensor_to_raw_ms','s256_all8_over200ms','s320_all8_over200ms'],'unit':'8training calibration vectors per separately trained resolution model','limits':'不是同一权重的纯尺寸消融，不是完整视频／后台性能。'},
 {'ID':'C07','status':'supported_aggregate_count_only','statement':'新mosaic0.5模型的完整O8原片输出为10，人工总量12。','source':'detector_video','fields':['FP32_QDQ_actual_O8_original_counts'],'unit':'one public clip aggregate count','limits':'绝对总量差2，不能推断只有2漏计或给逐事件F1。'},
 {'ID':'C08','status':'supported_development_training','statement':'六个配对条件各300更新，共1800正式更新；新域为16ID/457图。','source':'training','fields':['formal_optimizer_updates','training_conditions','new_Cows_training_IDs','new_Cows_training_images'],'unit':'optimizer update and publisher namespace ID','limits':'初值相同，来源图数/ID数一起变化；支持训练来源取舍而非单一场景因素因果归因。'},
 {'ID':'C09','status':'pending_readback','statement':'实际计数触发四轮的完整照片、原始输出及后台等待比较。','source':'actual_trigger_partial','fields':['observed_complete_case_summaries','fourth_case_terminal_observed','original_results_archive_obtained'],'unit':'current evidence only host summaries10/10/8 plus fourth350frame lower bound','limits':'原始数据未取回，不能进入正式结果表或声称四轮已验证。'},
 {'ID':'C10','status':'pending_ground_truth','statement':'耳标关联失败后可靠找回真实通行牛号，或减少逐事件漏计/重计。','source':None,'fields':[],'unit':'complete passage with independent identity and event reference','limits':'目前缺独立逐事件JSON和当前12事件的永久ID映射。'},
 {'ID':'C11','status':'pending_live_input_and_energy','statement':'真实相机/RFID输入下稳定5FPS、功耗/每事件能量或长期可靠性。','source':None,'fields':[],'unit':'continuous system under declared input and workload','limits':'现有证据是公开回放、模拟RF输入；功率与现场输入尚未测量。'},
 {'ID':'C12','status':'pending_novelty','statement':'本系统或方法相对近期最接近论文构成明确的新贡献。','source':None,'fields':[],'unit':'specific methodological or system contribution and matched comparison','limits':'检测、跟踪、花纹识别及边缘部署都有先例；组合可运行本身不构成新颖性证明。'}]
source_rows=[{'name':key,'file':str(p.resolve()),'sha256':sha(p)}for key,p in sources.items()]
data={'status':'DRAFT_CLAIMS_BOUND_TO_COMPLETED_RESULTS_PARTIAL_AND_MISSING_CLAIMS_EXPLICIT','created_UTC':datetime.now(timezone.utc).isoformat(),'sources':source_rows,'claims':claims,
 'numbers':{'identity_primary_outcomes':known,'identity_network_timing':arm['timings'],'fixed_workload_cases':fixed['cases'],'detector_sizes_mean_ms':[sizes['s256_mean_tensor_to_raw_ms'],sizes['s320_mean_tensor_to_raw_ms']],'aggregate_original_prediction':10,'human_confirmed_aggregate':12},
 'new_model_forwards':0,'ready_for_submission':False,'whole_goal_complete':False}
(ROOT/'results').mkdir(exist_ok=True);out=ROOT/'results/claim_ledger_v1.json';assert not out.exists();out.write_bytes(json.dumps(data,ensure_ascii=False,indent=2).encode()+bytes([10]))
text='''# 论文主张、证据与缺口

2026年10月30日。当前适合先形成“公开回放下的单板系统研究”草稿。模型和系统已有可复核实现，核心待解决问题是完整事件效果、输入时序与相对既有工作的具体贡献。下面按完成状态组织，正式结果只取已完整取包并复算的阶段。

| 主张ID | 状态 | 可写入的内容 | 单位与适用范围 |
|---|---|---|---|
'''
source_map={r['name']:r for r in source_rows}
for c in claims:
 link='['+c['source']+'](<'+Path(source_map[c['source']]['file']).as_posix()+'>)'if c['source']else'待取得直接证据'
 text+=f"| {c['ID']} | {c['status']} | {c['statement']} {link} | {c['limits']} |"+chr(10)
text+='''

## 候选贡献怎样收紧

现有材料最适合支撑三个研究内容：将检测／通行计数与按需身体检索放在同一块PYNQ-Z2；分别评价候选排名、自动接受覆盖与未知误收；用同一释放时钟记录前台迟到、跳帧与后台完整完成时间。论文的新增价值应由可复现的系统机制或更好的风险—覆盖—时序权衡支撑，复用的O8、YOLO26和ByteTrack按来源引用。

完整四轮实际触发原始数据是下一项验收，不由固定10照片控制替代。板卡恢复后先读取SD原任务、核验boot与终态，保持已冻结输入／权重／阈值；之后完成实际照片的CPU参考和完整关联重放。

## 投稿前按这些证据判定

BLOCKER：独立逐事件及真实永久身份分母缺失，当前无法支持可靠掉标找回或计数方法优越性；实际触发四轮待取回；具体新贡献尚需与最近工作对应并验证。若选择公开回放系统研究路线，标题和实验必须保持该范围，并补足完整工作负载和对照。

IMPORTANT：每组计时起点、同源设备重复、图库晚于事件的回顾范围、同场景保留ID与已见检测父图、未知比例和拒识门限均进入方法表。后续根据已评分20ID改方法时，需要新的独立证据。

POLISH：问题、方法和已完成结果可以先写；作者、单位、资金、利益声明和目标刊会暂不填猜测信息。英文与版式在方法和结果范围固定后统一。所有主张的原始字段及SHA见[结构化对应表](results/claim_ledger_v1.json)。
'''
out=ROOT/'论文主张与证据对应.md';assert not out.exists();out.write_text(text,encoding='utf-8');print(json.dumps({'claims':len(claims),'bound_sources':len(source_rows),'ready_for_submission':False,'new_model_forwards':0}))
