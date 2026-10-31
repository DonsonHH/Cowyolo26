from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
audit=load(ROOT/'delivery/results/audit/summary.json');v=load(ROOT/'results/independent_verification.json')
loader=load(ROOT/'results/loader_recovery_local/summary.json');lv=load(ROOT/'results/loader_independent_verification.json')
flag=load(ROOT/'results/publisher_annotation_flag.json');media=load(ROOT/'results/media_and_XML_verification.json')
assert audit['objects']==8888 and loader['augmented_label_rows']==20292 and lv['actual_RGB_images_byte_hash_checked']==96
assert media['SVG_histogram_bars']==108 and flag['labels_removed_or_changed']==0
a=audit['all_objects']
report=f'''# 普通俯视训练覆盖：暗色代理不少，原图与增强输入必须分开

2026年10月30日。**审计不支持直接把剩余漏计解释成“训练中没有暗色牛”。** 6809张训练图的8888个躯干标注中，5899个区域中位亮度≤80，3707个与背景的中位亮度差≤15。实际加载器的一轮增强输出又有20292个AABB，其中5466个短边<24像素。接下来检验训练增强强度，而不是继续调整运行时提亮或为原片凑12改计数规则。

本轮没有正式训练或检测／身份网络前向。后续mosaic配对训练在独立目录记录，不能把其短跑或计划计入这里的模型成果。

## 原始训练图审计

只读取已准入的6809张训练图，逐张校验源SHA；1571验证图、保留日期及源视频像素没有进入覆盖审计。区域使用发布方旋转躯干矩形裁到画面后的多边形，背景为外扩16像素方形环带，排除全部躯干标注。它不是像素分割。

| 固定代理 | 个数／8888 | 比例 |
| --- | ---: | ---: |
| 区域中位亮度Y≤80 | {a['dark_proxy_median_le80']} | {a['dark_proxy_median_le80']/8888:.1%} |
| 与环带背景中位亮度差≤15 | {a['low_contrast_proxy_le15']} | {a['low_contrast_proxy_le15']/8888:.1%} |
| 同时满足上述两项 | {a['dark_and_lowcontrast']} | {a['dark_and_lowcontrast']/8888:.1%} |
| 两躯干矩形相交占较小区域≥0.1 | {a['overlap_min_fraction_ge01']} | {a['overlap_min_fraction_ge01']/8888:.1%} |
| 可见矩形面积／完整矩形面积<0.99 | {a['truncated_visible_fraction_lt099']} | {a['truncated_visible_fraction_lt099']/8888:.1%} |
| 原生矩形短边按192名义缩放后<24px | {a['short_side192_lt24']} | {a['short_side192_lt24']/8888:.2%} |

低亮度不等于毛色标签，矩形重叠不等于真实遮挡，几何裁断也不是发布方人工遮挡等级。当前准入标注只有annotation_key、bbox、类别及发布方编号／目录五字段，没有独立遮挡真值。上述比例是代理分布，不能用于宣称“66.4%的牛是黑牛”或“3%被遮挡”。

亮度中位数的10／50／90分位为45／67／194；绝对背景对比为4／19／134；原生矩形投影到192后的短边为30.45／33.6／37.05px。192／256／320名义投影均有逐对象记录，但常规mosaic、尺度和裁剪会进一步改变真实训练输入，不能只按原图推断训练曝光。

![全部原生覆盖分布](<{(ROOT/'delivery/results/media/training_coverage_histograms.png').as_posix()}>)

![按固定规则选择的12份训练样例](<{(ROOT/'delivery/results/media/training_proxy_extremes12.png').as_posix()}>)

图中绿色为被选躯干，灰色为同图其他发布方躯干。依次为最低亮度、最低背景对比、最大重叠和最小192名义短边；同值按annotation_key排列，排除重复key。两个不同标注可能来自同一源图，不能把12个面板写成12头独立奶牛。

## 真正的增强加载器

用当前安装的Ultralytics8.4.63实际训练加载器及既有直角旋转函数，保持192、batch32、seed26、mosaic1.0、scale0.5和常规增强，提供完整213批、6809幅图；没有构建或运行检测网络。这里是CPU加载器开发观察，不是原历史训练所有epoch的逐像素重放。后台预取可能额外读取训练样本，不计入已交付图像数。

| 实际增强后AABB指标 | 数量 |
| --- | ---: |
| 已交付训练图 | 6809 |
| 交付框 | 20292 |
| 短边<24px | 5466（26.9%） |
| 短边<16px | 1949（9.6%） |
| 区域中位Y≤80 | 13596 |
| 区域与背景中位亮度差≤15 | 9748 |
| AABB相交占较小框≥0.1 | 4037 |

增强后短边的10／50／90分位约16.34／32.38／57.37px。原图使用旋转躯干区域，增强后使用真实训练AABB；二者的亮度区域和几何定义不同，不能把两套百分比当作只有增强因素不同的严格配对。

实际保存前三批96幅192 RGB图及全部框，逐字节核对输入hash，并独立检查258个存储框与背景环带。Pillow与OpenCV两种Y实现的中位数在这些图中相差最多1灰度；没有声称保存或逐像素复算全部6809幅增强图。anchor文件名只标记拼图的锚图，不代表每个框的原始来源或永久身份。

![前12幅实际增强输入与训练框](<{(ROOT/'results/local_media/first12_actual_augmented_inputs.png').as_posix()}>)

## 一对发布方疑似重复标注

全部2563个同图矩形对中，只有02191.jpg的一对IoU≥0.5，具体IoU约0.975。它的两个框尺寸、角度相同，中心仅相差2px；原始发布方XML也确实包含这两个cow对象，并非本项目读取JSON时复制出来。

原图目视支持“同一躯干被重复标注”的高度疑点；XML自身verified属性为no，不能将其升级成独立确认真值。本轮保留原标签，仅登记疑点，没有自动删除。这个单例也不能解释全部跨来源退化或剩余漏计。后续两个训练分支使用同一未修改标签集，避免把清洗与增强因素混在一起。

## 执行与复核

Slurm130617原生审计COMPLETED／0:0，用时1分15秒；130618媒体COMPLETED／0:0，用时2秒。130619实际交付213批并保存全部样本记录后，在汇总JSON处因NumPy int64序列化失败；130620恢复辅助任务又因计算节点无法连接Slurm记账数据库，在读取数据前退出。两个失败状态和日志保留。

终态在mu01重新确认后，取回原输出并在本机恢复统计，未重跑加载器；所有已保存原文件哈希保持。没有伪造失败前未落盘的运行时transform repr、实际worker数或pin-memory值。数字序列化的真实int64错误已本机复现，转成Python数字后的回写检查通过。

独立复算覆盖8888个可见几何、17776份亮度直方图、2563个交叠对、35个原生像素控制、20292个增强框几何和96幅实际RGB输入。矩形交叠的FP32与独立双精度面积最大差约0.02158px²；另检查108根实际SVG柱、12个固定样例选择及发布方XML来源。

原生／媒体包33,283,804字节，SHA256 `311308288440a6addde07fa41fe0d2f7ef6c3b9440793dde3e284617b385218c`；加载器失败记录包9,036,701字节，SHA256 `2ced38cbd3f48cf84e1b1cde1b1cde513ef2a5433aee8c3fe9aa1048265d576c`，均已本地核验。

## 下一步

下一组只把mosaic概率1.0改为0.5，并保留两个配置各三个seed、相同初始化、训练长度和其他增强。选择0.5是一个固定开发对照，不是本审计证明的最优值；增强后的大小分布也不证明mosaic是漏计的原因。两分支不同的随机调用和拼图组成属于该配置干预，不能声称逐像素输入完全相同。

新模型仍需统一源片／Toros评价、量化与实际O8验证。原片只有人工总数12，独立事件JSON、真实双向普通俯视及永久身份参考仍待补充。

[配对训练计划](<{(PROJECT/'mosaic_pair_20261030/计划与验收.md').as_posix()}>) · [原生独立复算](<{(ROOT/'results/independent_verification.json').as_posix()}>) · [加载器独立复算](<{(ROOT/'results/loader_independent_verification.json').as_posix()}>) · [发布方XML疑点](<{(ROOT/'results/publisher_annotation_flag.json').as_posix()}>)
'''
path=ROOT/'训练覆盖审计与下一组对照.md';assert not path.exists();path.write_text(report,encoding='utf-8')
review='''# 覆盖审计Review与当前状态

本轮审计完成，不新增正式模型或板端效果。原图与实际增强输入的区域／几何口径分别说明，暗色／低对比并非稀缺的假设已修正。

- 已独立复算8888个原生区域及20292个增强AABB；不把代理当毛色或遮挡真值。
- 213批／6809幅增强图记录从真实失败作业恢复，没有重跑或伪造未落盘元数据。
- 发布方XML中的一对近似重复仅登记，未自动删标签，也不把单例当系统退化原因。
- 108根SVG柱与3图28面板已核查；图片中的框是训练标签，没有混入模型预测。
- 下一组训练仅改变mosaic概率，原片12头不用于选seed或直接写事件F1。
- BLOCKER：独立逐事件JSON、真实双向普通俯视和永久身份参考仍缺，整体科研目标继续。
'''
p=ROOT/'Review与当前状态.md';assert not p.exists();p.write_text(review,encoding='utf-8')
files=[]
for name,panels in [('delivery/results/media/training_coverage_histograms.png',4),('delivery/results/media/training_proxy_extremes12.png',12),('results/local_media/first12_actual_augmented_inputs.png',12)]:
    f=ROOT/name;files.append({'path':str(f.resolve()),'sha256':sha(f),'actually_viewed':True,'panels':panels})
save(ROOT/'results/visual_review.json',{'status':'THREE_FIGURES28_PANELS_ACTUALLY_VIEWED','created_UTC':datetime.now(timezone.utc).isoformat(),'files':files,
    'figures_actually_viewed':3,'panels_actually_viewed':28,'note':'native published labels and actual augmentation labels;no model outputs or claimed independent cow identities'})
print(json.dumps({'report':str(path),'new_formal_training_updates_in_audit':0,'whole_goal_complete':False}))
