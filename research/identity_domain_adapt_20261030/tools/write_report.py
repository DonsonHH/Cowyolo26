from pathlib import Path
import json

ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
summary=json.loads((ROOT/'delivery/results/evaluation/summary.json').read_text());verified=json.loads((ROOT/'results/independent_verification.json').read_text())
assert verified['formal_updates_checked']==1800
lines=['| 分支／seed | 开发组 | Top-1／60 | 新域C／W／U | 新域未知FA／120 | 原阈值C／W／U | 原阈值未知FA／120 |','| --- | --- | ---: | --- | ---: | --- | ---: |']
for name in[condition['name']for condition in json.loads((ROOT/'protocol/run_v1.json').read_text())['conditions']]:
 for fold in['fold0','fold1']:
  candidates=[row for row in summary['outcomes']if row['condition']==name and row['scope']==fold]
  new=next(row for row in candidates if row['threshold_policy']=='Cows_calibrated');old=next(row for row in candidates if row['threshold_policy']=='original_MultiCam');a,b=new['metrics'],old['metrics']
  lines.append(f"| {name} | {fold} | {a['known_closed_top1_correct']} | {a['known_correct_accepted_C']}／{a['known_wrong_accepted_W']}／{a['known_rejected_U']} | {a['unknown_false_accepts']} | {b['known_correct_accepted_C']}／{b['known_wrong_accepted_W']}／{b['known_rejected_U']} | {b['unknown_false_accepts']} |")
retention=['| 分支／seed | 原MultiCam Top-1／30 | C／W／U | 未知FA／30 |','| --- | ---: | --- | ---: |']
for row in summary['outcomes']:
 if row['dataset']=='MultiCam2023':
  a=row['metrics'];retention.append(f"| {row['condition']} | {a['known_closed_top1_correct']} | {a['known_correct_accepted_C']}／{a['known_wrong_accepted_W']}／{a['known_rejected_U']} | {a['unknown_false_accepts']} |")
primary=[row for row in summary['outcomes']if row['condition']=='C_domain_seed26'and row['dataset']=='Cows2021'and row['scope']in['fold0','fold1']and row['threshold_policy']=='Cows_calibrated']
assert len(primary)==2
top=[row['metrics']['known_closed_top1_correct']for row in primary];cw=[[row['metrics'][key]for key in['known_correct_accepted_C','known_wrong_accepted_W','known_rejected_U','unknown_false_accepts']]for row in primary]
transfer=json.loads((ROOT/'results/transfer_verification.json').read_text());candidate=next(row for row in summary['models']if row['condition']['name']=='C_domain_seed26')
text=f'''# 身份来源配对训练与同规模图库开发评价

2026年10月30日。完成两个来源分支×三个seed的六次新训练，每次300更新；所有末轮权重冻结后统一评价。事先指定的C_domain_seed26在两个20ID开发组上的Top-1分别为{top[0]}／60和{top[1]}／60；新域阈值的C／W／U／未知FA为{cw[0]}、{cw[1]}。以下报告全部seed、原来源保留能力和错误接受，不按其中一组结果选择模型。

## 先固定来源和训练预算

两分支从同一已上板encoder开始，SHA`6653555c9c806e23d2747b06db53424541254364065c53c5311b7ae2ded06b8b`。M_continue用原580张MultiCam训练图、20ID；C_domain用新457张Cows2021身体图、16ID，日期≤2020-02-27。新16ID与之前Cows120校准／开发ID及未来20候选ID互斥；未来20的像素、本次03-05至03-11保留日期均未开启。[先冻结计划](计划与验收.md) · [全部协议与名单](protocol/run_v1.json)

Cows图来自作者命名为Identification/Test的分区；本项目明确将其中16个未用ID改作监督训练，不能说成复现作者原测试协议。原始分区／ID／日期已核查，编号属于各数据集命名空间，不将跨2020／2023未映射的数字用作正负身份对。[作者来源和范围](../cows2021_identity_intake_20261030/身份来源核查与跨日期评价准入.md)

两分支同样的224增强、每步8ID×4图、跨日期正样本、CE＋batch-hard triplet、AdamW学习率1e-4，seeds26／27／28各300更新，只取末轮，不用开发成绩选epoch。来源同时改变相机／场景、样本与ID数，因此对照支持“增加该新域训练后的系统取舍”，不证明某一个摄影因素是唯一原因。

预检两个分支各1步CUDA更新后丢弃；正式六次共1800更新、57600训练图像前向。六个末轮权重共同冻结时，校准／开发／保留能力的特征前向仍为0。之后六模型校准180图各自拒识阈值共同落盘，再运行开发360图与原MultiCam90图；共3780次评价图像前向，无预热。包含预检64图在内总新增模型图像前向**61444**，正式更新1800与丢弃的2次预检分开。

## 匹配20ID图库的全部开发结果

沿用先前已看开发牛号，40个注册ID按原SHA顺序分为两个20ID组。每组图库每牛3参考、60个已登记查询，使用同一批120个未知查询；校准图库也是20ID，避免上一阶段20→40的规模变化。每模型仍报告原MultiCam阈值0.844539与仅用Cows校准选出的新阈值，不在开发查询上调阈值。

{chr(10).join(lines)}

这两个组的未知查询重复，不能相加当240张新未知图／80头独立未知牛。完整40ID图库仍作压力附录保存，没有隐藏；全部42个主／压力／保留条件与逐查询决定可复算。[完整评价](delivery/results/evaluation/summary.json)

新模型和未继续训练encoder的同牛配对差、C相对M的同seed配对差均另存；阈值不同的比较体现整套“编码器＋独立校准”策略，不能说是只改特征。[按牛配对及区间](results/paired_analysis.json)

## 原来源保留能力

原MultiCam30图图库、30已登记＋30未知查询，阈值继续0.844539。它们早已用于开发，不称新最终测试；用来暴露Cows适配对原来源的代价。

{chr(10).join(retention)}

不凭Cows单组提高就忽略原来源回退，也不凭原来源较好就跳过新域错误。按牛bootstrap的区间保留；三个seed是训练随机性，不是三个牧场独立重复。新的最终牛号还未做评价。

## 实际训练与独立复核

CUDA预检作业130772完成0:0；正式数组130777的6个任务均COMPLETED／0:0；CPU评价作业{summary['Slurm_job_id']}完成0:0。训练、校准和评价在Slurm分配内，mu01只做文件和轻量核查，没有改变其他项目作业或现有环境。服务器速度不写成PYNQ性能。

本机核对1800条正式梯度更新，按独立随机采样复现全部源索引、8×4身份与至少两日期正样本，检查有限损失／非零梯度与起终参数摘要不同；每次第一批4张实际输入另存。保存的输入hash是日志绑定，不冒充逐像素重放所有随机增强。3780份完整特征、42组指标／7560个决定和所有按牛区间均另行复算。[独立核验](results/independent_verification.json)

新增训练图全部与作者ZIP CRC、字节数、解码hash一致，与原540及750身份输入无精确像素重复。原下载进程退出原因未观察到，直接检查进程已不在、350份JPEG与350条持久化日志仍完整；只补107个缺失图，没有重新下载350图或替换牛号。首次／恢复日志及原脚本均保留。[图像准入](results/input_admission.json) · [恢复原因](evidence/download_resume_reason.json)

全部结果和六个末轮encoder已完整取回，归档{transfer['bytes']:,}字节、{transfer['members']}成员，SHA`{transfer['sha256']}`。权重、训练日志、实际输入、所有特征、阈值冻结和失败记录保留。[原始包核验](results/transfer_verification.json)

## 后续采用门禁

事先固定的主seed26候选SHA为`{candidate['sha256']}`。当前阶段只提供训练与开发评价证据，不把它写成最终改进或自动替换板端模型。下一步先根据全部开发与原来源取舍确定候选是否值得继续，再冻结NCNN数值一致性、真实板端推理和最终20ID实验；若评价不足则保留负面结果，不开最终数据反复找工作点。

当前原12头牛仍无可靠永久身份对应，检测漏计、逐事件JSON、实际RFID／相机和完整C／W／U／M门禁不变。公开裁剪输入的检索不能替代通行抓拍全链路。

BLOCKER：整体论文主张仍缺新的最终身份评价与完整事件／现场证据。

IMPORTANT：全部seed、两20ID组、40ID压力及原来源保留均报告；未采用新阈值、未声称板端速度、未对未来20ID开图。

POLISH：输出前核对来源范围、实际更新／前向、数据访问顺序、原始特征及图像面板；助手自审和独立程序复算不冒充独立人工标注或外部审稿。
'''
target=ROOT/'身份域适配配对训练与开发结果.md';assert not target.exists();target.write_text(text,encoding='utf-8')
candidate_record={'status':'PRESELECTED_SEED26_RESEARCH_CHECKPOINT_RETAINED_NOT_DEPLOYED','checkpoint_original_server':candidate['checkpoint'],
                  'local_checkpoint':str((ROOT/'delivery/results/training/C_domain_seed26/last_encoder.pt').resolve()),'sha256':candidate['sha256'],
                  'seed26_fixed_before_training':True,'final20_ID_pixels_opened':False,'board_default_changed':False,'whole_goal_complete':False}
p=ROOT/'results/retained_candidate.json';assert not p.exists();p.write_text(json.dumps(candidate_record,indent=2)+'\n')
print(str(target))
