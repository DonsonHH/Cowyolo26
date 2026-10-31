from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
marker='当前统一入口：[研究阶段总结（2026年10月30日）]'
paragraph=marker+'(<C:/Users/Donson/Documents/ChatGPT/奶牛/研究阶段总结_20261030.md>)。已实际完成同板O8检测／ARM跟踪、高分辨率照片裁剪与身份网络：直接后台或空闲策略在部分392时隙运行达到5FPS平均吞吐，但仍有200ms迟到、运行波动；原片计数11／人工总数12，Toros1／0／5，真实永久身份准确率未证明。132张照片身份输入与144检索决定完成ARM一致性核查；PNG0保存像素不变、存储约3倍，完整三组控制保留所有不利结果。192／256／320已统一O8实测，受控训练向量张量至raw均值155.46／235.55／370.93ms；256／320没有完整视频或同板5FPS证明。320初始NumPy参考差异、显式浮点顺序合同、失败脚本及全部原始输出保留。当前下一步是独立逐事件参考、暗色／遮挡计数质量、跨来源与重复时序验证，整体科研目标继续。下文较早的“未上板”等内容是历史阶段快照。'
updates=[]
for rel in ['研究总览_从想法到论文.md','研究进度.md','phase3_diagnosis_20261026/方案与执行状态.md']:
 file=PROJECT/rel;before=file.read_bytes();text=before.decode('utf-8');assert marker not in text
 nl='\r\n' if '\r\n' in text else '\n';old='最新完成[新192模型量化与真实PYNQ视频计数]';assert old in text;at=text.index(old)
 text=text[:at]+paragraph+nl+nl+text[at:]
 if rel=='研究进度.md':text=text.replace('更新：2026年10月29日。','更新：2026年10月30日。',1)
 if rel.startswith('phase3'):
  line=next(x for x in text.splitlines() if x.startswith('| D9 新192实际视频与量化对照'))
  text=text.replace(line,line+nl+'| D10 同板身份与调度 | ARM132图资格、直接／空闲及PNG保存单因素 | 实际同板44个触发身份作业，原始照片／特征及定时raw核对 | 平均约5FPS可达，仍有迟到与队列取舍，计数11／12、独立GT待补 |'+nl+'| D11 同O8三尺寸与剩余案例 | 256／320各8实际向量；192三实现诊断 | 三尺寸统一O8，320浮点合同与原失败均保留 | 192主候选继续；优先独立事件与暗色／遮挡检测质量 |',1)
 file.write_bytes(text.encode('utf-8'));updates.append({'path':str(file.resolve()),'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
file=ROOT/'results/overview_updates.json';assert not file.exists();file.write_text(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'updates':updates},indent=2)+'\n')
print(json.dumps({'overview_entrypoints_updated':3,'summary_document':str(PROJECT/'研究阶段总结_20261030.md'),'whole_goal_complete':False}))
