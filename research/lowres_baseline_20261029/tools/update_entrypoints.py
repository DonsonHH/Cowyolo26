from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
PROJECT=Path(__file__).resolve().parents[2];ROOT=PROJECT/'lowres_baseline_20261029'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
para='最新按用户要求转向[192／256／320与5Hz基线](<C:/Users/Donson/Documents/ChatGPT/奶牛/lowres_baseline_20261029/低分辨率基线与5Hz计数结果.md>)，并完成[板端连接核查](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_lowres_20261029/PYNQ低分辨率部署与连接核查.md>)：PYNQ3.1.1／ARMv7环境已实际读到；短测PID8082启动后服务失联，终态及PL配置未能读回，未重复启动，5FPS尚未证明。服务器12条件50700前向和72计数路径完成，原片192三seed为0／1／2、256为7／7／7、320为10／8／10；Toros官方256／320由30Hz的6匹配降为5Hz的4。三视频、独立复算和当前图已核查，原640人工12头版本保持。旧9组640训练未执行，新低分辨率15训练候选仅为计划；先恢复硬件可观测状态，并离线检验固定通道裁剪与采样机制，再训练和验证同板前后台。'
records=[]
for rel in ['研究总览_从想法到论文.md','研究进度.md','phase3_diagnosis_20261026/方案与执行状态.md']:
    file=PROJECT/rel;before=file.read_bytes();text=before.decode('utf-8');marker='最新完成[检测框躯干配对与尺度诊断]'
    assert marker in text and 'lowres_baseline_20261029' not in text;nl='\r\n' if '\r\n' in text else '\n';i=text.index(marker);updated=text[:i]+para+nl+nl+text[i:]
    if rel.startswith('phase3'):
        line=next(r for r in updated.splitlines() if r.startswith('| I5 检测框／躯干配对'))
        row='| D1 低分辨率与单板目标 | 按用户192／256／320、前台5Hz，定位／计数／量化／板时延分别验收 | 全尺寸seed与5／30Hz采样对照；同板后台负载 | 离线12条件完成，当前直接缩小未保持12头；板清单已读、PID8082终态未明，禁止重启未知任务，待用户确认状态 |'
        updated=updated.replace(line,line+nl+row,1)
    file.write_bytes(updated.encode('utf-8'));records.append({'path':str(file.resolve()),'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':sha(file)})
file=ROOT/'计划与验收.md';text=file.read_text(encoding='utf-8');text+='\n## 执行收尾\n\n离线步骤1–6完成：50700源图条件、32808刻度、72计数路径、三段指定范围视频已复核。失败输出父目录和Toros路径保留；续行只补5748次剩余推理，已完成44952记录原样复用，参数不变。图例／数字拥挤另存v2，不修改数据与视频。板端PID8082仍未观测终态，与离线完成严格区分；没有宣称5FPS达标。下一步先恢复硬件可观测状态，离线则检查固定通道裁剪，再执行低分辨率训练计划。\n';file.write_text(text,encoding='utf-8')
file=PROJECT/'pynq_lowres_20261029/计划与当前状态.md';text=file.read_text(encoding='utf-8');text+='\n## 当前实际进展与限制\n\n已读到真实PYNQ3.1.1环境和既有YOLO运行器，后续仅一次启动自有硬件测试PID8082。观测阶段Jupyter／SSH失联，COM6无返回，无法读回固件状态或进程终态；未重启进程／板卡，用户状态问题仍待回答。初始化清单、照片上传及启动证据保留，不以历史帧率当本次达标。离线12条件与三视频已另行完成，见主报告；整体目标保持进行中。\n';file.write_text(text,encoding='utf-8')
file=PROJECT/'detector_factorial_20261029/计划与验收.md';text=file.read_text(encoding='utf-8');text+='\n## 用户低分辨率修订\n\n用户补充192／256／320与PYNQ-Z2连接后，原640九候选尚未开始，v1保留历史。新training_v2_lowres_plan.json列三尺寸×两增强×三seed，保留三个既有320普通控制，另15候选目前提交数0；没有进行短跑或正式训练。先完成低分辨率固定基线、固定通道裁剪与硬件路径核查，再执行训练。\n';file.write_text(text,encoding='utf-8')
out=ROOT/'results/entrypoint_updates.json';assert not out.exists();out.write_text(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'files':records},indent=2)+'\n')
print(json.dumps({'research_entrypoints_updated':3,'plans_updated':3,'board_goal_still_unverified':True}))
