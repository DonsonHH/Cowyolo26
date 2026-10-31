from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
marker='最新完成[15新模型固定通道裁剪对照]'
paragraph=marker+'(<C:/Users/Donson/Documents/ChatGPT/奶牛/factorial_lane_crop_20261029/固定裁剪结果与部署下一步.md>)及[自审](<C:/Users/Donson/Documents/ChatGPT/奶牛/factorial_lane_crop_20261029/Review与当前状态.md>)：39810真实前向、90计数路径，9图54面板与两段视频3924帧已核对。192直角三seed由6／5／5升为10／10／10，256为11／11／12，320为12／12／11；Toros跨来源召回仍不足，原片12头仅为人工总数，不是逐事件真值。结果读取前固定的192直角seed26已完成[新候选O8编译与实机向量资格检查](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_rot192_compile_20261029/计划与验收.md>)：仅128训练图校准，8实际板上输出与CPU整数参考逐字节一致，张量到原始输出平均155.46ms。正在推进量化后的完整视频计数和板上NumPy跟踪回归；采集、计数、后台身份同板联合5FPS仍未证明，原640成功版本保留。'
updates=[]
for rel in ['研究总览_从想法到论文.md','研究进度.md','phase3_diagnosis_20261026/方案与执行状态.md']:
 file=PROJECT/rel;before=file.read_bytes();text=before.decode('utf-8');assert marker not in text
 old='最新完成[低分辨率漏计分解]';assert old in text;index=text.index(old);nl='\r\n' if '\r\n' in text else '\n'
 text=text[:index]+paragraph+nl+nl+text[index:]
 if rel.startswith('phase3'):
  line=next(r for r in text.splitlines() if r.startswith('| D6 低分辨率事件诊断'))
  text=text.replace(line,line+nl+'| D7 新权重固定通道裁剪 | 15模型同权重全输入配对 | 39810真实前向、90计数路径、两视频3924帧 | 192直角三seed均10；保留负例，固定seed26推进O8 |'+nl+'| D8 新192模型O8与板上计数 | 训练集校准、整数输出、NumPy移植和实机回放 | 8新模型板上向量逐字节一致；90缓存服务器回归通过 | 实际视频计数和同板后台联合仍进行中 |',1)
 file.write_bytes(text.encode('utf-8'));updates.append({'file':str(file.resolve()),'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
out=ROOT/'results/entrypoint_updates.json';assert not out.exists();out.write_text(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'updates':updates},indent=2)+'\n')
print(json.dumps({'entrypoints_updated':len(updates),'whole_goal_complete':False}))
