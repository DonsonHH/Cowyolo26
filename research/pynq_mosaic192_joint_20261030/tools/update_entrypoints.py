from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,re
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
for phase in ['pynq_mosaic192_compile_20261030','pynq_mosaic192_eval_20261030','pynq_mosaic192_joint_20261030']:
    f=load(PROJECT/phase/'results/final_review.json');assert not f['whole_goal_complete']
    for row in f['documents']:assert sha(row['path'])==row['sha256']
v=load(ROOT/'results/independent_verification.json');fps=[r['processed_per_second_over_offered_duration'] for r in v['cases']]
tasks=v['actual_background_identity_jobs'];counts=[r['source_down_count'] for r in v['cases']]
q=load(PROJECT/'pynq_mosaic192_eval_20261030/results/final_review.json')
overview=PROJECT/'研究阶段总结_20261030.md';old=load(PROJECT/'research_synthesis_20261027/results/overview_review_20261030_v4.json')
assert sha(overview)==old['document']['sha256']
summary=f'''最新完成固定mosaic0.5主seed26的[PTQ与8张同O8向量](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_mosaic192_compile_20261030/新主候选量化与O8实机准入.md>)、[2654次真实PYNQ视频](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_mosaic192_eval_20261030/新候选量化与真实视频结果.md>)和[两轮六次同板周期复测](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_mosaic192_joint_20261030/新候选同板周期与两轮复测.md>)。新实际O8原片计数10／人工12，反向5Hz3／0／3、30Hz源采样控制4／0／2；比旧模型反向1／0／5改善，原片比旧11少1，故保留比较而未默认替换。六次周期吞吐{min(fps):.3f}–{max(fps):.3f}FPS，后台共{tasks}次真实身份任务，仍有跳帧／迟到；这些是公开回放与模拟RF，身份正确率和现场设备未证明。独立事件／永久身份参考继续待补，下一步转向普通俯视新会话、连续检测及因果抓拍质量。'''
conclusion=f'''**当前结论：同一PYNQ-Z2已实际完成新mosaic0.5检测、ARM计数、实时照片处理及身份检索，六次公开回放周期运行平均吞吐范围{min(fps):.3f}–{max(fps):.3f}FPS。新模型完整实机原片10／人工12、反向3／6；旧模型分别11和1／6，存在质量取舍，未默认替换。永久身份真值、独立通行评价和真实相机／耳标仍缺，论文可继续推进，完整现场效果尚未证明。**'''
names={'foreground_only':'独占','foreground_with_identity':'直接后台','foreground_idle_identity':'空闲后台'}
table='\n'.join('| '+str(r['repeat'])+' | '+names[r['case']]+' | '+str(r['processed_frames'])+' | '+str(r['skipped_slots'])+' | '+str(r['deadline_misses'])+' | '+format(r['processed_per_second_over_offered_duration'],'.3f')+' | '+str(r['source_down_count'])+' |' for r in v['cases'])
new_periodic=f'''新mosaic0.5权重已完成两轮顺序反转的6次同板实测，所有时间点确有实际O8，后台合计{tasks}次真实身份前向。输入、图库、照片和拒识口径保持；公开回放与RFID全未读模拟不等于现场传感器。

| 轮次 | 策略 | 处理／392 | 跳帧 | 释放→计数>200ms | FPS | 计数／人工12 |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
{table}

每次计数与任务数同时报告，两次重复不能支持统计显著性或跨牧场泛化。当前及全部实际照片、后台排队与终态见[新候选两轮复测](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_mosaic192_joint_20261030/新候选同板周期与两轮复测.md>)。新旧模型的计数、实际触发负载不同，不能把旧单次与新两次直接解释为纯调度改善。

下表保留旧mosaic1.0的历史单次控制，范围与新权重分开。

'''
paths=[PROJECT/'研究总览_从想法到论文.md',PROJECT/'研究进度.md',PROJECT/'phase3_diagnosis_20261026/方案与执行状态.md',overview]
snapshot=ROOT/'evidence/entrypoints_before';snapshot.mkdir(exist_ok=False);updates=[]
for i,path in enumerate(paths):
    text=path.read_text(encoding='utf-8');before=sha(path);backup=snapshot/(str(i)+'_'+path.name);backup.write_bytes(path.read_bytes())
    marker='最新完成[普通俯视训练覆盖审计]'
    assert text.count(marker)==1;text=text.replace(marker,summary+'\n\n前一训练阶段：[普通俯视训练覆盖审计]',1)
    if path!=overview:
        text,n=re.subn(r'^当前统一入口：.*$',
            '当前统一入口：[研究阶段总结（2026年10月30日）](<C:/Users/Donson/Documents/ChatGPT/奶牛/研究阶段总结_20261030.md>)。最新模型、旧基线、完整视频和同板周期的范围在入口分别记录；下文较早的“下一步”或“未上板”等内容保留为历史阶段快照。',text,count=1,flags=re.M)
        assert n==1
    if path==overview:
        match=re.search(r'^\*\*当前结论：.*?\*\*$',text,re.M);assert match;text=text[:match.start()]+conclusion+text[match.end():]
        old='主seed26只保留为量化候选，未替换旧实机模型，也未恢复原片12头。25350次统一推理、36计数路径及1962帧对照视频已复核；下一步是该固定候选的PTQ、同O8实机及周期负载验证，独立事件与永久身份参考继续待补。'
        new='该阶段只保留主seed26作量化候选，25350次统一推理、36计数路径及1962帧对照视频已复核；后续PTQ、真实O8和周期复测现已完成，结果见上。独立事件与永久身份参考继续待补。'
        assert text.count(old)==1;text=text.replace(old,new)
        text=text.replace('主seed26保持预先选择，仅进入量化候选队列，不按seed28的原片11改选。','主seed26保持预先选择，随后已完成PTQ及实机，不按seed28的原片11改选。')
        mark='### 3.3 完整192视频：模型可执行与计数质量分开'
        note='新mosaic0.5主seed26另完成同O8的8训练向量＋2预热，完整raw逐字节一致，平均140.32ms；该次短测不混入旧三尺寸数据。之后完整2654帧的网络均值144.24ms、PNG到计数及raw保存均值179.79ms，两种计时范围也分别报告。\n\n'
        assert text.count(mark)==1;text=text.replace(mark,note+mark)
        old='板端实际完成2654个视频图条件推理、2734个跟踪时刻和6计数路径，另有预热；所有raw及轨迹已取回。'
        new='旧mosaic1.0板端曾完成2654个视频图条件推理、2734个跟踪时刻和6计数路径；下表是该历史模型。新mosaic0.5主seed26也独立完成同样2654帧：FP32／QDQ／实际O8原片都为10，Toros5Hz都为3／0／3、30Hz控制都为4／0／2。新静态FP32／QDQ匹配1838／1839，所有2654帧QDQ raw仍不等于实际O8，8个新原生锚点逐字节相同。[新模型完整实机与视频](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_mosaic192_eval_20261030/新候选量化与真实视频结果.md>)'
        assert text.count(old)==1;text=text.replace(old,new)
        text=text.replace('当前实际O8交接计数TP1／FP0／FN5','旧实际O8交接计数TP1／FP0／FN5')
        marker='### 3.5 同板约5FPS已经测到，但每帧200ms仍未全部满足\n\n'
        assert text.count(marker)==1;text=text.replace(marker,marker+new_periodic)
        old='2. 覆盖审计和mosaic六组配对训练已完成；保留预先固定的mosaic050_seed26，先用训练图校准、同O8向量及完整视频检查，再复测周期负载。当前FP32反向3／6尚不能替代实际O8基线1／6；不向训练加入Toros后仍称其独立测试。'
        new='2. 新主候选PTQ、2654实际O8视频与两轮周期负载已完成。反向3／6已是真实板端结果，但原片10比旧11退步，暂不默认替换。继续定位两种模型的完整通行差异，并在普通俯视新会话及独立参考上比较，不通过换seed或加源片训练来追12。'
        assert text.count(old)==1;text=text.replace(old,new)
        text=text.replace('所以下一步先验证固定主候选的量化与真实O8效果，而不是继续搜索区域或seed。','量化与真实O8验证现已确认这种质量取舍，下一步转向完整通行差异和普通俯视新会话，不继续按单片搜索区域或seed。')
        old='此前实机阶段结束时已记录自有任务终态、SSH／Jupyter可访问及O8固件状态；本轮只做训练和离线评价，未改动板端环境，也未把旧连接状态当作新的实时检查。'
        new='最新实验结束后已重新读取3个新父任务和4个身份子任务，均正常终态且PID消失，SSH与Jupyter可访问、共享加速锁空闲且原O8 bit保持。没有更改全局运行环境或自动全局替换模型。'
        assert text.count(old)==1;text=text.replace(old,new)
    path.write_text(text,encoding='utf-8');updates.append({'path':str(path),'before_sha256':before,'after_sha256':sha(path),'before_snapshot':str(backup)})
f=ROOT/'results/entrypoint_updates.json';assert not f.exists();f.write_text(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'updates':updates,'whole_goal_complete':False},indent=2)+'\n',encoding='utf-8')
print(json.dumps({'updated':4,'FPS_range':[min(fps),max(fps)],'actual_identity_jobs':tasks,'source_counts':counts,'whole_goal_complete':False}))
