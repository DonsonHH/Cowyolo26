from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
for phase in [ROOT,PROJECT/'training_coverage_20261030']:
    final=load(phase/'results/final_review.json');assert final['whole_goal_complete'] is False
    for row in final['documents']:assert sha(row['path'])==row['sha256']
old=load(PROJECT/'research_synthesis_20261027/results/overview_review_20261030_v3.json')
overview=PROJECT/'研究阶段总结_20261030.md';assert sha(overview)==old['document']['sha256']
latest='''最新完成[普通俯视训练覆盖审计](<C:/Users/Donson/Documents/ChatGPT/奶牛/training_coverage_20261030/训练覆盖审计与下一组对照.md>)及[192三seed的mosaic配对训练](<C:/Users/Donson/Documents/ChatGPT/奶牛/mosaic_pair_20261030/配对训练结果与量化候选.md>)：原生低亮度／低对比代理并不稀缺；6次新10轮训练共7350更新。mosaic0.5的原片三seed为10／10／11，对照10／10／10；Toros5Hz匹配3／3／0，对照1／1／0，FP均0。主seed26只保留为量化候选，未替换旧实机模型，也未恢复原片12头。25350次统一推理、36计数路径及1962帧对照视频已复核；下一步是该固定候选的PTQ、同O8实机及周期负载验证，独立事件与永久身份参考继续待补。'''
paths=[PROJECT/'研究总览_从想法到论文.md',PROJECT/'研究进度.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md',overview]
snapshot=ROOT/'evidence/entrypoints_before';snapshot.mkdir(exist_ok=False);updates=[]
for i,path in enumerate(paths):
    before=sha(path);text=path.read_text(encoding='utf-8');backup=snapshot/(str(i)+'_'+path.name);backup.write_bytes(path.read_bytes())
    assert text.count('最新质量对照：')==1;text=text.replace('最新质量对照：',latest+'\n\n上一轮输入对照：',1)
    if path==overview:
        match=re.search(r'^\*\*当前结论：.*?\*\*$',text,re.M);assert match
        conclusion='**当前结论：这条路线已在PYNQ-Z2公开视频回放中实现同板检测、计数、照片处理和身份检索，192输入测到约5FPS平均吞吐。已有实机基线原片为11／人工总数12、反向匹配1／6；新mosaic0.5主seed26仅FP32反向达到3／6、原片仍10，尚未量化或上板。永久身份恢复也缺独立真值。论文有继续研究的路径，当前不能把原型或局部改善写成完整现场效果已验证。**'
        text=text[:match.start()]+conclusion+text[match.end():]
        mark='### 3.2 用户指定的O8三尺寸实机'
        extra='''后续新增6次mosaic1.0／0.5配对训练（含3次新重复控制），各10轮。三个新1.0对照各708个参数／缓冲状态张量完全复现旧模型；0.5的开发图未匹配预测减少，但seed28静态匹配少20。原片为10／10／11，反向5Hz为3／3／0，均不足以宣称最终成功。主seed26保持预先选择，仅进入量化候选队列，不按seed28的原片11改选。[完整配对结果与候选](<C:/Users/Donson/Documents/ChatGPT/奶牛/mosaic_pair_20261030/配对训练结果与量化候选.md>)

'''
        assert text.count(mark)==1;text=text.replace(mark,extra+mark)
        old='检查全部300候选发现，入口有几何接近却分类分数很低的框。小幅降低阈值不足以恢复既定三次稳定要求，且可能引入额外框。下一步优先普通俯视暗色／遮挡正例和事先冻结的训练控制，而不是为凑12头改区域规则。这个定位基于开发模型参照，仍不能当作独立漏检真值。'
        new='对旧mosaic1.0候选检查全部300候选发现，入口有几何接近却分类分数很低的框。小幅降低阈值不足以恢复既定三次稳定要求，且可能引入额外框。这个定位基于开发模型参照，仍不能当作独立漏检真值，也不能自动定位新模型漏掉的是同一头牛。'
        assert text.count(old)==1;text=text.replace(old,new)
        mark='后台照片还暴露出另一问题：'
        extra='''训练覆盖审计现已完成：8888个原生躯干区域中，低亮度代理5899、低背景对比3707，不支持“训练缺少暗色牛”的简单归因。实际加载器6809幅增强图有20292个AABB、5466个短边<24px；原生旋转矩形与增强AABB口径不同，不能直接同比。一对高度相似框已回查原始XML，仅登记疑点，未自动删除。mosaic0.5配对提供局部反向改善，但原片仍未恢复12，所以下一步先验证固定主候选的量化与真实O8效果，而不是继续搜索区域或seed。[覆盖审计及边界](<C:/Users/Donson/Documents/ChatGPT/奶牛/training_coverage_20261030/训练覆盖审计与下一组对照.md>)

'''
        assert text.count(mark)==1;text=text.replace(mark,extra+mark)
        old='2. 先审计训练集本身的暗色／遮挡和有效牛体像素覆盖，再固定低分辨率配对训练；输入亮度对照已完成且未采用。使用全部事件与负例评价，同时保留Toros跨来源压力结果，不在Toros上训练后仍称其独立测试。'
        new='2. 覆盖审计和mosaic六组配对训练已完成；保留预先固定的mosaic050_seed26，先用训练图校准、同O8向量及完整视频检查，再复测周期负载。当前FP32反向3／6尚不能替代实际O8基线1／6；不向训练加入Toros后仍称其独立测试。'
        assert text.count(old)==1;text=text.replace(old,new)
        old='每个目录的Review、冻结协议、文件哈希和失败记录保留；所有本轮自有板端任务已终态，SSH与Jupyter仍可访问，O8固件保持。'
        new='每个目录的Review、冻结协议、文件哈希和失败记录保留。此前实机阶段结束时已记录自有任务终态、SSH／Jupyter可访问及O8固件状态；本轮只做训练和离线评价，未改动板端环境，也未把旧连接状态当作新的实时检查。'
        assert text.count(old)==1;text=text.replace(old,new)
        text=text.replace('本轮恢复8779本地服务的命令被自动审批策略拦截','此前恢复8779本地服务的命令被自动审批策略拦截')
    path.write_text(text,encoding='utf-8')
    updates.append({'path':str(path),'before_sha256':before,'after_sha256':sha(path),'before_snapshot':str(backup)})
r={'created_UTC':datetime.now(timezone.utc).isoformat(),'updates':updates,'pair_review_sha256':sha(ROOT/'results/final_review.json'),
    'coverage_review_sha256':sha(PROJECT/'training_coverage_20261030/results/final_review.json'),'whole_goal_complete':False}
f=ROOT/'results/entrypoint_updates.json';assert not f.exists();f.write_text(json.dumps(r,indent=2)+'\n',encoding='utf-8')
print(json.dumps({'updated':len(updates),'whole_goal_complete':False}))
