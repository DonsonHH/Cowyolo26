from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
link='[裁剪域验证与采用决策](<C:/Users/Donson/Documents/ChatGPT/奶牛/crop_domain_20261029/裁剪域验证与采用决策.md>)'
para='最新完成'+link+'：先用80个验证输入冻结20阈值和5个规则选择，再打开102评价／实际输入，全部5编码器、4规则、原／新阈值共40评价条件保留。C28选择去边框，但复合方案为19C/0F，旧基线21C/0F；同原阈值两裁剪均21C，因子已拆开。C26校准后26C/3F，风险仍超小验证目标；实际只保留E010匿名009候选，仍未核实。3640真实图像编码、5080决定、70700余弦、728像素变换和六图72面板核查完成；不作默认替换，原12头达标计数保持。下一步转向真实检测框与躯干参考的成对定位，身份独立通行参考及PYNQ-Z2联合验收继续待补。'
records=[]
for rel,marker in [('研究总览_从想法到论文.md','最新完成[跨日期图库'),('研究进度.md','最新完成[跨日期图库'),('phase3_diagnosis_20261026/方案与执行状态.md','最新完成[跨日期图库')]:
    file=PROJECT/rel;before=file.read_bytes();text=before.decode('utf-8');assert 'crop_domain_20261029' not in text and marker in text
    nl='\r\n' if '\r\n' in text else '\n';position=text.index(marker);after=text[:position]+para+nl+nl+text[position:]
    if rel.startswith('phase3'):
        row=next(r for r in after.splitlines() if r.startswith('| I3 跨日期图库干预'))
        added='| I4 裁剪与校准隔离 | 旋转来源核对；验证身份先选择P0/P1/P2并固定阈值，P3控制不选择 | 全部规则／seed与原／新阈值；现有输出精确回归 | 40条件完成，无稳健默认替换；实际009仍候选，下步转向真实检测框／躯干成对参考 |'
        after=after.replace(row,row+nl+added,1)
    file.write_bytes(after.encode('utf-8'));records.append({'path':str(file.resolve()),'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':sha(file)})
file=ROOT/'计划与验收.md';text=file.read_text(encoding='utf-8');assert '## 执行收尾' not in text
text+='\n## 执行收尾\n\n步骤1–6完成。25新图／182输入、20验证／40评价条件、3640实际编码、5080决定、728像素变换、六图72面板均复核。主报告明确C28裁剪和阈值因子、C26未知风险及实际匿名候选限制；采用决策不作全局替换。原12头计数保持，研究入口同步；下步转向真实检测框与躯干定位参考，而非继续根据这些评价图调中心比例。\n'
file.write_text(text,encoding='utf-8')
meta=json.loads((ROOT/'evidence/result_transfer.json').read_text())
wrapper={'status':'COMPLETED_SINGLE_MODEL_JOB_PLUS_COMPLETED_PLOT_JOB_COLLECTION_VERIFIED','raw_metadata_sha256':sha(ROOT/'evidence/result_transfer.json'),
'raw_status_template_string':meta['status'],'template_status_string_is_not_model_failure_evidence':True,'actual_model_job130496':'COMPLETED0:0','actual_plot_job130497':'COMPLETED0:0'}
f=ROOT/'results/collection_metadata_interpretation.json';assert not f.exists();f.write_text(json.dumps(wrapper,indent=2)+'\n')
out=ROOT/'results/entrypoint_updates.json';assert not out.exists();out.write_text(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'files':records},indent=2)+'\n')
print(json.dumps({'entrypoints':len(records),'plan_complete':True,'metadata_template_interpreted':True}))
