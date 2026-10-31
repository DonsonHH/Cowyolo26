from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
PROJECT=Path(__file__).resolve().parents[2];ROOT=PROJECT/'lowres_roi_20261029'
para='最新完成[固定通道裁剪与低分辨率对照](<C:/Users/Donson/Documents/ChatGPT/奶牛/lowres_roi_20261029/固定通道裁剪与低分辨率结果.md>)：12冻结模型尺寸条件新增31848次真实前向，72计数路径独立复算一致。原片三个seed的192计数从0／1／2升至7／4／8，但256、320仍有无改善或退步，所有条件均未恢复人工12头；Toros官方256／320亦有退步，裁剪不默认采用。8源锚点、24真实网络输入、9173框、完整1962帧视频和13图73面板已核查。用户明确192／256／320及约5FPS来自实机约束，必须实机验证；SD卡插紧后SSH／Jupyter已恢复、IP仍192.168.2.99，旧PID8082无完整可采信性能结果，已归档。[PYNQ实机复测计划](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_board_validation_20261029/计划与验收.md>)按单帧探针、三档受控样本、真实前台时序及同板后台逐步验收，当前尚未宣称5FPS达标。'
records=[]
for relative in ['研究总览_从想法到论文.md','研究进度.md','phase3_diagnosis_20261026/方案与执行状态.md']:
    file=PROJECT/relative;before=file.read_bytes();text=before.decode('utf-8');marker='最新按用户要求转向[192／256／320与5Hz基线]'
    assert marker in text and 'lowres_roi_20261029' not in text
    newline='\r\n' if '\r\n' in text else '\n';index=text.index(marker)
    text=text[:index]+para+newline+newline+text[index:]
    if relative.startswith('phase3'):
        line=next(r for r in text.splitlines() if r.startswith('| D1 低分辨率与单板目标'))
        row='| D2 固定通道输入对照 | 先按原ROI裁剪、恢复完整坐标，再检查三尺寸计数 | 12条件31848前向、72计数路径及真实输入图 | 独立复核完成；存在改善和退步，未达12，不默认采用；实机恢复后继续验收 |'
        text=text.replace(line,line+newline+row,1)
    file.write_bytes(text.encode('utf-8'));records.append({'path':str(file.resolve()),'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
file=ROOT/'计划与验收.md';text=file.read_text(encoding='utf-8')
text+='\n## 执行收尾\n\nSlurm130506／130507／130508均完成0:0，分别负责31848真实前向、独立像素核查及媒体导出。9173框、72计数路径、24输入数组、1962视频帧和13图73面板已复核；裁剪只作开发对照。用户随后澄清参数来自实机，并协助查明SD卡未插紧；插回后实际IP仍192.168.2.99，旧中断结果归档，新单板验证另立协议。整体保持进行，不升级裁剪为全局方案，不将5Hz采样当实机吞吐。\n'
file.write_text(text,encoding='utf-8')
out=ROOT/'results/entrypoint_updates.json';assert not out.exists();out.write_text(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'files':records},indent=2)+'\n')
print(json.dumps({'research_entrypoints_updated':3,'roi_plan_updated':True,'whole_goal_complete':False}))
