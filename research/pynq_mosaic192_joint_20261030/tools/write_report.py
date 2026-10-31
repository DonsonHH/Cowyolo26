from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def link(p,label):return '['+label+'](<'+str(Path(p).resolve()).replace('\\','/')+'>)'
v=load(ROOT/'results/independent_verification.json');photos=load(ROOT/'results/photo_panels/manifest.json');visual=load(ROOT/'results/visual_review.json')
assert len(v['cases'])==6 and visual['actually_viewed_photo_panels']==v['actual_background_identity_jobs']
names={'foreground_only':'前台独占','foreground_with_identity':'直接后台','foreground_idle_identity':'空闲后台'}
table=[]
for r in v['cases']:
    bg=next((x for x in v['backgrounds'] if x['run']==r['run']),None)
    table.append('| '+str(r['repeat'])+' | '+names[r['case']]+' | '+str(r['processed_frames'])+' | '+str(r['skipped_slots'])+' | '+str(r['deadline_misses'])+' | '+format(r['P95_release_to_count_ms'],'.2f')+' | '+format(r['processed_per_second_over_offered_duration'],'.3f')+' | '+str(r['source_down_count'])+' | '+str(r['actual_background_jobs'])+' | '+(format(bg['max_queue_wait_ms']/1000,'.2f') if bg else '—')+' |')
ranges=[]
for policy in names:
    rr=[r for r in v['cases'] if r['case']==policy]
    ranges.append('| '+names[policy]+' | '+str(min(r['skipped_slots'] for r in rr))+'–'+str(max(r['skipped_slots'] for r in rr))+' | '+str(min(r['deadline_misses'] for r in rr))+'–'+str(max(r['deadline_misses'] for r in rr))+' | '+format(min(r['processed_per_second_over_offered_duration'] for r in rr),'.3f')+'–'+format(max(r['processed_per_second_over_offered_duration'] for r in rr),'.3f')+' |')
accepted=sum(r['accepted_provisional_predictions'] for r in v['backgrounds'])
prior=load(PROJECT/'pynq_mosaic192_eval_20261030/results/independent_board_verification.json')
source=next(r for r in prior['source_counts'] if r['scene']=='original' and r['counter']=='handoff_events')['down']
picturelinks=' · '.join(link(r['file'],Path(r['file']).stem) for r in photos['files'])
text=f'''# 新mosaic0.5权重：两轮同板5Hz周期与实际身份后台

2026年10月30日。前台为固定mosaic050_seed26，后台为既有真实ARM NCNN身体编码器，照片实时裁剪、PNG0保存、预处理和图库检索均在PYNQ-Z2执行。以下每行都是真实运行；**平均吞吐、超过200ms、跳帧、完整计数和后台等待分别报告**，不由单独模型耗时相加推断。

本轮使用相同392时隙公开视频回放，每时隙200ms、每次78.4秒。第一轮独占→直接→空闲，第二轮空闲→直接→独占。两次是同一来源的设备重复，不能当两个独立牧场会话，也不足以宣称统计显著性。

## 全部六次运行

| 轮次 | 策略 | 处理／392 | 跳帧 | 释放→计数>200ms | P95 ms | 78.4s内FPS | 原片向下计数／人工12 | 实际身份作业 | 最大后台排队s |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
{chr(10).join(table)}

| 策略 | 两次跳帧范围 | 两次迟到范围 | 两次吞吐FPS范围 |
| --- | --- | --- | --- |
{chr(10).join(ranges)}

每个后台条件只由当次实际计数事件触发任务，作业数可能随跳帧／计数改变，不是预先固定注入11任务。新模型此前完整无周期O8原片计数为{source}，人工总量12。比较调度策略时同时看触发任务数，不能以漏计少做后台工作当作同负载优势。旧mosaic1.0的三组单次运行也不是本轮同权重同负载的严格因果对照。

## 确实在同板做了哪些事

每轮先以本候选真实O8的0–8910帧原始检测恢复1783个历史时刻，所有观察、框和两条计数路径与该候选完整视频记录精确相同。之后每个处理时刻都运行真实O8，计时区间没有使用缓存raw替代网络；{v['actual_O8_timed_forwards']}份实际raw与新模型对应完整视频逐字节一致。另有8次实际BGR资格前向和12次前台预热，不混入定时帧分母。

四个后台进程共执行{v['actual_background_identity_jobs']}次真实身份前向，另4预热；每个任务读取当帧1050×1440原生通道JPEG95，用当前实时轨迹框裁剪并顺时针旋转，保存PNG0、复现冻结224输入几何、运行576维身体特征、对固定图库检索和拒识。照片有JPEG来源损失，不能称完全无损原始相机抓拍；PNG0阶段不再引入额外像素损失。

空闲策略由父进程发SIGSTOP并经waitpid确认后才运行前台，完成计数后SIGCONT，网络从原计算位置继续。独立核查{v['pause_windows_verified']}个真实暂停区间。这里没有使用未来帧、GT身份或模型参照框进行抓拍。

## 身份输出的范围

全部{v['actual_background_identity_jobs']}张实际照片、输入张量、原始／归一化特征和登记ID分数已重算，固定阈值共接受{accepted}个候选。接受次数不是准确率：这些通行事件没有可靠永久身份真值，全部保持identity_reference_available=false。Aug19图库查询Aug14事件是回顾实验，尚未证明事件前已注册的在线顺序；同次通行的Aug14旧图库没有作为正式独立评价图库。

全部实际照片（包含拒识）可查看：{picturelinks}。

前台帧已经由服务器准备为192已就绪BGR；高分辨率图来自公开视频回放，RFID固定模拟全部未读。两个网络和照片处理确实同板运行，但没有真实相机／耳标输入，不能宣称现场异常关联已验证。相同来源重复、图库、模型和拒识门限都保留，未按新结果选择最佳一次。

## 独立复算与进程终态

核对全部时隙的释放、处理、跳过和截止时间；{v['counter_observation_ticks_with_history']}个含前史观察、12条计数路径，逐个当前框、同帧高分辨率裁剪、照片像素、224张量、576特征及分数都可追溯。暂停检查使用“确认已停止→前台完成”的可证区间，不把发送SIGCONT后的父进程打点当实际恢复时刻。

协议中的256输入量化对照摘要沿用旧模型记录；本轮另对新模型images_scale／zero_point的全部256个灰度值复查，除255与乘倒数的FP32中间值有微差外，全部INT8输入码一致。这项新模型复查发生于启动后，未修改运行协议；计时前8个实际BGR锚点及计时后每帧对同模型完整raw的严格核对分别保留，不把事后复查写成事前完成。

归档阶段SSH等待曾超时，后续根据打开压缩包的PID31517确认原归档进程仍活跃；等待其结束后读取原有transfer记录并核对文件大小和SHA，没有重建压缩包或重复执行模型。超时记录、进程检查和最终取回均保留。

父进程和四个身份工作进程均正常终态且已不存在，安全关闭后原O8 bit保持。本轮未新增训练、固件烧写、身份标签、独立测试或功率计数据。原始记录、全部不利运行与照片保留。

{link(ROOT/'results/independent_verification.json','完整复算与六次指标')} · {link(ROOT/'protocol/run_v1.json','冻结协议')} · {link(PROJECT/'pynq_mosaic192_eval_20261030/新候选量化与真实视频结果.md','同候选完整视频结果')}

## 研究决定

本轮补齐同一新权重的周期系统证据，但是否采用还需同时看原片12头缺口、侧视压力与普通俯视新会话。短期继续查缺失完整通行的连续检测与原生低对比场景，并改进只用过去帧的身份抓拍质量；不要因为时序达到约5FPS就停止质量评价。

独立逐事件JSON和永久身份参考仍待补齐，物理相机／RFID和实际功耗也未完成。论文应按“公开回放＋实机系统原型”的已证范围组织，现场或准确率结论等相应证据到位再写。
'''
f=ROOT/'新候选同板周期与两轮复测.md';assert not f.exists();f.write_text(text,encoding='utf-8')
review='''# 两轮同板周期Review与当前状态

- 六次真实运行与四个身份后台都已终态，所有raw和照片取回；旧任务／环境保持。
- 两次顺序反转用于观察设备波动，不作统计显著性或跨牧场独立性主张。
- 前台计时确有实际O8前向，历史缓存仅用于预热轨迹状态；用新模型历史，不用旧模型接续。
- 全部当前框／照片／输入／特征／拒识决定及两条计数路径独立复算，未把候选牛号当GT。
- 归档SSH超时后确认原归档PID活跃再等终态，未重跑；256量化码的新模型复查发生于启动后，时间范围明确。
- 高分辨率JPEG回放和RFID模拟、事件后图库的回顾顺序、已就绪低分辨率输入的计时范围均明确。
- IMPORTANT：少计会减少身份负载，策略比较同时报告计数和任务数；全部不利运行保留。
- BLOCKER：独立逐事件与永久身份参考、真实相机／RFID和功耗证据仍待补，整体科研目标继续。
'''
f=ROOT/'Review与当前状态.md';assert not f.exists();f.write_text(review,encoding='utf-8')
print(json.dumps({'actual_O8_timed_forwards':v['actual_O8_timed_forwards'],'actual_identity_jobs':v['actual_background_identity_jobs'],
    'case_counts':[r['source_down_count'] for r in v['cases']],'FPS':[r['processed_per_second_over_offered_duration'] for r in v['cases']],
    'new_permanent_ID_accuracy_proven':False,'whole_goal_complete':False}))
