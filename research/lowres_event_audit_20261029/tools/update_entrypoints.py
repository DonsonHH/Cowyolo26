from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
para='最新完成[低分辨率漏计分解](<C:/Users/Donson/Documents/ChatGPT/奶牛/lowres_event_audit_20261029/低分辨率漏计分解与下一步.md>)及[自审](<C:/Users/Donson/Documents/ChatGPT/奶牛/lowres_event_audit_20261029/Review与当前状态.md>)：只读27整幅＋12既有裁剪缓存，78条件／234辅助路径独立核对。固定192直角seed26实际6，6未计开发参照在IoU0.3／0.5下即使辅助对应原始框仍缺现行区域证据；5条入口连续观察不足，1条出口不足，单改ID关联不够。18源帧／6页36面板已实际检查并按绝对PTS逐像素复核；参照为模型轨迹，不新增正式框／身份真值，辅助路径也不是单调误差上界。本轮无新网络、训练或板端动作。下一步[15新模型固定裁剪对照](<C:/Users/Donson/Documents/ChatGPT/奶牛/factorial_lane_crop_20261029/计划与验收.md>)已冻结原ROI和39810前向计划，尚未提交；保持权重、跟踪和计数规则，保留原12头成功版本。'
records=[]
for relative in ['研究总览_从想法到论文.md','研究进度.md','phase3_diagnosis_20261026/方案与执行状态.md']:
    file=PROJECT/relative;before=file.read_bytes();text=before.decode('utf-8');marker='最新完成[15组低分辨率训练与统一评价]'
    assert marker in text and '最新完成[低分辨率漏计分解]' not in text;nl='\r\n' if '\r\n' in text else '\n';i=text.index(marker)
    text=text[:i]+para+nl+nl+text[i:]
    if relative.startswith('phase3'):
        line=next(r for r in text.splitlines() if r.startswith('| D5 低分辨率正式训练'))
        text=text.replace(line,line+nl+'| D6 低分辨率事件诊断 | 固定框对应与三辅助路径，区分覆盖／中心／确认阶段 | 39缓存、78条件、234路径、18源帧核对 | 主要192案例关键区域观察不足；不改规则，下一步15新模型固定ROI对照尚未提交 |',1)
    file.write_bytes(text.encode('utf-8'));records.append({'path':str(file.resolve()),'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
file=ROOT/'计划与验收.md';text=file.read_text(encoding='utf-8')
text+='\n## 执行结果\n\n27整幅缓存诊断完成后，又按独立冻结协议读取12个既有固定ROI缓存作为同权重控制，没有新增推理或搜索参数。合计78分析条件、234辅助计数路径及55848关联问题已独立核对；18源帧按帧号与实际PTS两种选择逐像素一致，六页36面板已实际查看。主要192案例未计6参照在辅助关联后仍缺当前区域证据，原12头组合不替换。下一步已另存15新模型固定ROI协议，尚未提交作业。修正版裁剪汇总、核对路径及失败时间seek记录均保留。\n';file.write_text(text,encoding='utf-8')
file=ROOT/'results/entrypoint_updates.json';assert not file.exists();file.write_text(json.dumps({'created_host_UTC':datetime.now(timezone.utc).isoformat(),'files':records},indent=2)+'\n')
print(json.dumps({'entrypoints_updated':3,'new_forwards':0,'next_crop_job_submitted':False,'whole_goal_complete':False}))
