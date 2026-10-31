from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
para='最新完成[15组低分辨率训练与统一评价](<C:/Users/Donson/Documents/ChatGPT/奶牛/detector_factorial_20261029/低分辨率训练对照与采用决定.md>)及[自审](<C:/Users/Donson/Documents/ChatGPT/奶牛/detector_factorial_20261029/Review与当前状态.md>)：各组10轮、18375次正式更新，全部末轮权重共同冻结后新增63375次真实图条件推理。直角增强的CW90躯干匹配召回均值达到192的98.00%、256的98.91%、320的98.96%，但原片5Hz计数仅6／5／5、7／8／8、7／8／7，未恢复12头；新模型暂不替换原640成功组合。23565关联、61225框逆变换、90计数路径与60事件评分独立复核一致。训练收尾LF误判导致原作业FAILED，成功权重经核验恢复，逐次梯度数组未回收、旋转日程为明确重建，全部失败证据保留。下一步先分析低分辨率检测／跟踪／稳定区间，再把固定候选接入已通过首轮向量验证的O8通路；新15模型的实际视频计数和同板后台5FPS仍待验。'
records=[]
for relative in ['研究总览_从想法到论文.md','研究进度.md','phase3_diagnosis_20261026/方案与执行状态.md']:
    file=PROJECT/relative;before=file.read_bytes();text=before.decode('utf-8');marker='最新在用户确认的O8引擎完成'
    assert marker in text and '最新完成[15组低分辨率训练与统一评价]' not in text;nl='\r\n' if '\r\n' in text else '\n';i=text.index(marker)
    text=text[:i]+para+nl+nl+text[i:]
    if relative.startswith('phase3'):
        line=next(row for row in text.splitlines() if row.startswith('| D4 奶牛单类权重O8准入'))
        text=text.replace(line,line+nl+'| D5 低分辨率正式训练 | 15新条件＋3历史控制，各seed固定末轮；统一定位／视频评价 | 18375更新、63375前向、90计数路径独立核对 | 躯干定位改善，原片计数未恢复12，新候选暂不替换；继续低分辨率事件诊断与O8实际视频验证 |',1)
    file.write_bytes(text.encode('utf-8'));records.append({'path':str(file.resolve()),'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
file=ROOT/'计划与验收.md';text=file.read_text(encoding='utf-8');text+='\n## 当前实际执行结果\n\n用户修订后的v4三尺寸方案已执行：15组各10轮训练完成，原130518任务在收尾LF字节比较中失败，130542核验成功权重并共同冻结，没有重复训练。130544完成63375图条件推理、90计数路径；全部新权重、本地原始结果及独立复算已保存。直角增强提升CW90躯干定位，但原片5Hz计数未恢复12，暂不替换原640组合。旧seed26的192单类模型已在O8通过8训练向量实现核对；本轮15个新模型的实际视频计数与后台联合仍待验。逐次梯度数组未回收，旋转日程明确为重建，不填实际旋转标签累计数。\n';file.write_text(text,encoding='utf-8')
file=ROOT/'results/entrypoint_updates.json';assert not file.exists();file.write_text(json.dumps({'created_host_UTC':datetime.now(timezone.utc).isoformat(),'files':records},indent=2)+'\n')
print(json.dumps({'entrypoints_updated':3,'new15_candidate_adopted':False,'whole_goal_complete':False}))
