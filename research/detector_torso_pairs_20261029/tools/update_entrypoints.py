from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
link='[检测框躯干配对与尺度诊断](<C:/Users/Donson/Documents/ChatGPT/奶牛/detector_torso_pairs_20261029/检测框躯干配对与尺度诊断.md>)'
para='最新完成'+link+'：8380源图／10752旋转躯干参考已建立完整对应，主640CW90条件4模型配对为1141／592／505／226（分母1864）；seed26训练仅2920/8888配对，未把成功子集当全部数据。固定8图追加288输入控制，排除坐标还原错误，seed26同方向／补边320为11/12、640为4/12；未据此全局改320。独立几何／关联／目标及12图82面板核查完成，保留全部边界和未匹配项。原12头成功组合保持，下一步优先尺寸与直角旋转增强的三seed训练对照，再决定躯干定位；本轮无新训练或身份真值，PYNQ-Z2联合关口继续待验。'
records=[]
for rel in ['研究总览_从想法到论文.md','研究进度.md','phase3_diagnosis_20261026/方案与执行状态.md']:
    file=PROJECT/rel;before=file.read_bytes();text=before.decode('utf-8');marker='最新完成[裁剪域验证与采用决策]'
    assert marker in text and 'detector_torso_pairs_20261029' not in text;nl='\r\n' if '\r\n' in text else '\n'
    i=text.index(marker);updated=text[:i]+para+nl+nl+text[i:]
    if rel.startswith('phase3'):
        row=next(r for r in updated.splitlines() if r.startswith('| I4 裁剪与校准隔离'))
        new='| I5 检测框／躯干配对 | 全开发源图绑定旋转参考、检测框与可见几何，保留未匹配；输入尺寸／方向控制 | 独立匹配／像素和输入重复；不把框当身份 | 已完成13381实际检测与2920训练定位目标；640出现明显适配问题，下步先做尺寸×直角增强训练因素对照 |'
        updated=updated.replace(row,row+nl+new,1)
    file.write_bytes(updated.encode('utf-8'));records.append({'path':str(file.resolve()),'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':sha(file)})
file=ROOT/'计划与验收.md';text=file.read_text(encoding='utf-8');assert '## 执行收尾' not in text
text+='\n## 执行收尾与追加控制\n\n步骤1–6均完成。实际主检测13093图次、额外输入控制288图次；源图8380、唯一参考10752、全部匹配／漏检和5384定位目标保留。出现640条件配对下降后，使用预测前固定8张图追加方向×尺寸×补边因子及首尾重复协议，没有改主规则或挑换样本；排除坐标逆变换后优先尺度／方向训练，而非直接只用2920个成功训练裁剪。三作业均完成，12页82图像面板及独立几何／目标／绘图核查通过。原12头计数冻结版本保持，下一步9候选训练路线另行冻结执行，本轮未启动训练。\n'
file.write_text(text,encoding='utf-8')
out=ROOT/'results/entrypoint_updates.json';assert not out.exists();out.write_text(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'files':records},indent=2)+'\n')
print(json.dumps({'updated_entrypoints':3,'plan_completed_with_explicit_adaptive_probe':True}))
