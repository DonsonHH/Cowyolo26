from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
para='最新已完成[真实PYNQ-Z2三尺寸性能与输入瓶颈验证](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_board_validation_20261029/PYNQ实机三尺寸结果与下一步.md>)及[自审](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_board_validation_20261029/Review与当前状态.md>)：SD卡插紧后SSH／Jupyter恢复，地址仍192.168.2.99。板上424次实际网络推理、406份raw、324次CPU输入操作已取回并独立核对；预热后192／256／旧引擎320检测均值158.79／261.82／1056.39ms。每帧从大JPEG缩略解码时192仅2.97FPS；相同像素低分辨率BGR已就绪控制为4.90FPS、98/100处理、2跳帧和16迟到，尚未满足完整系统稳定5Hz。当前是COCO量化权重，12照片均无牛类输出，奶牛微调权重、跟踪计数及后台身份尚未联合上板；不能把服务器12头与板端4.9FPS拼成一个成功系统。全部7自有实验进程终态，固件已读回已知O8。下一步对齐用户原测程序，以192为优先候选推进低分辨率训练、奶牛权重编译与实际输入／前后台联合验收。'
history='下文保留此前阶段的证据快照；连接未恢复、尚未上板等表述是当时状态，当前进展以顶部实机报告为准。'
records=[]
for rel in ['研究总览_从想法到论文.md','研究进度.md','phase3_diagnosis_20261026/方案与执行状态.md']:
    file=PROJECT/rel;before=file.read_bytes();text=before.decode('utf-8');marker='最新完成[固定通道裁剪与低分辨率对照]'
    assert marker in text and '真实PYNQ-Z2三尺寸性能与输入瓶颈验证' not in text
    newline='\r\n' if '\r\n' in text else '\n';index=text.index(marker)
    text=text[:index]+para+newline+newline+history+newline+newline+text[index:]
    if rel.startswith('phase3'):
        line=next(r for r in text.splitlines() if r.startswith('| D2 固定通道输入对照'))
        text=text.replace(line,line+newline+'| D3 真实PYNQ-Z2性能 | 已有COCO引擎三档、输入成本、5Hz实际时钟均上板运行 | 424前向、406raw；192低分辨率输入就绪4.90FPS | 本轮已自审；2跳帧16迟到，尚未加载奶牛微调权重／跟踪／后台身份，不宣称完整5FPS |',1)
    file.write_bytes(text.encode('utf-8'));records.append({'path':str(file.resolve()),'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
file=ROOT/'计划与验收.md';text=file.read_text(encoding='utf-8')
text+='\n## 本轮已实际执行\n\n恢复、1帧探针、三档32样本、324次CPU输入操作以及两种5Hz定时回放已完成，合计424次硬件网络调用。原始文件取回并独立核对，所有7自有进程终态，当前固件读回O8。已就绪低分辨率192为4.90FPS，仍2/100跳帧和16/98迟到；奶牛微调权重、跟踪及后台身份联合执行留待下一关口。原始JPEG路径、像素不一致和旧引擎负结果保留，未筛除慢帧或以均值倒数冒充系统FPS。\n'
file.write_text(text,encoding='utf-8')
save=ROOT/'results/entrypoint_updates.json';assert not save.exists();save.write_text(json.dumps({'created_host_UTC':datetime.now(timezone.utc).isoformat(),'files':records},indent=2)+'\n')
print(json.dumps({'entrypoints_updated':3,'hardware_profile_verified':True,'joint_foreground_background_5FPS_proven':False}))
