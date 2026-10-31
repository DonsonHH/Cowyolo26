from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
report='[跨日期图库与实际抓拍结果](<C:/Users/Donson/Documents/ChatGPT/奶牛/crossdate_gallery_20261029/跨日期图库与真实抓拍身份结果.md>)'
paragraph='最新完成'+report+'：固定5编码器／原阈值，旧Aug14与新Aug19图库共10条件，60有标签裁剪＋12实际照片完整配对。C26登记正确23→27/30，但图库外误接收1→5/30；新图库只剩E010在C28给匿名009候选，仍未确认为身份。30新图官方校验、132输入检查、720决定／21600余弦、全部新误认病例及四图54面板复核完成；失败数值门限与CPU直接复现均保留。原12头达标计数保持，本轮无训练、无真实RF／板测；Aug19晚于原片，只作回溯开发诊断。下一步固定隔离身份的裁剪域及图库风险校准，再到新通行和PYNQ-Z2前后台共同验收。'
records=[]
for rel,marker in [('研究总览_从想法到论文.md','最新[身份来源审计]'),('研究进度.md','最新完成[原视频身份来源核查'),('phase3_diagnosis_20261026/方案与执行状态.md','新增完成[原视频与作者ID来源审计]')]:
    p=PROJECT/rel;raw=p.read_bytes();text=raw.decode('utf-8');assert 'crossdate_gallery_20261029' not in text
    newline='\r\n' if '\r\n' in text else '\n';assert marker in text
    pos=text.index(marker);updated=text[:pos]+paragraph+newline+newline+text[pos:]
    if rel.startswith('phase3'):
        line=next(r for r in updated.splitlines() if r.startswith('| I2 原视频身份来源'))
        added='| I3 跨日期图库干预 | 同6ID相机1五图，固定全部权重／原阈值与两类查询 | 旧结果精确重现；登记C/W/U、图库外误接收、实际候选分别报告 | 10条件已完成，C26覆盖提高但未知误认上升；009跨日候选仍非身份真值，裁剪域与独立校准待推进 |'
        updated=updated.replace(line,line+newline+added,1)
    p.write_bytes(updated.encode('utf-8'));records.append({'path':str(p.resolve()),'before_sha256':hashlib.sha256(raw).hexdigest(),'after_sha256':sha(p)})
plan=ROOT/'计划与验收.md';text=plan.read_text(encoding='utf-8')
text+='\n## 本轮执行收尾\n\n步骤1–6均已执行。30新图／132输入、10条件、成功轮660前向／720检索决定、全部错误病例与4图54面板均已核查。初次C28数值门限失败及v2直接CPU核查完整保留；实际12照片身份仍未独立接受，不报告事件身份准确率。研究入口已同步，下一步按报告推进隔离验证身份的裁剪域和图库校准，不据本轮评价挑seed或调阈值。\n'
plan.write_text(text,encoding='utf-8')
out=ROOT/'results/entrypoint_updates.json';assert not out.exists();out.write_text(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'files':records},indent=2)+'\n')
print(json.dumps({'updated_entrypoints':len(records),'plan_complete':True}))
