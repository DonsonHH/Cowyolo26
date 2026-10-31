from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
marker='最新完成[新192模型量化与真实PYNQ视频计数]'
paragraph=marker+'(<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_rot192_eval_20261029/新192量化与PYNQ视频计数结果.md>)及[自审](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_rot192_eval_20261029/Review与当前状态.md>)：新192直角seed26在用户指定O8上真实执行2654视频前向、2734跟踪时刻及6计数路径，原片为11，人工总数12；Toros仍1／0／5。FP32／QDQ／实际整数原片分别10／11／11，后两者raw并不相同；8实际视频锚点与CPU整数参考逐字节一致。无损192 PNG至计数平均178.24ms、P95198.02ms，118帧超过200ms，不能宣称稳定5Hz。132图身份编码器NCNN服务器特征／检索一致性已通过，ARM隔离编译进行中；下一步[392时刻周期释放与同板后台](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_periodic_joint_20261030/计划与验收.md>)已固定，真实摄像头和RFID未接入。三栏1962帧视频与5图16面板已核查，原640的12头版本保持。'
records=[]
for relative in ['研究总览_从想法到论文.md','研究进度.md','phase3_diagnosis_20261026/方案与执行状态.md']:
 file=PROJECT/relative;before=file.read_bytes();text=before.decode('utf-8');assert marker not in text
 old='最新完成[15新模型固定通道裁剪对照]';assert old in text;index=text.index(old);nl='\r\n' if '\r\n' in text else '\n'
 text=text[:index]+paragraph+nl+nl+text[index:]
 if relative.startswith('phase3'):
  line=next(x for x in text.splitlines() if x.startswith('| D8 新192模型O8与板上计数'))
  text=text.replace(line,line+nl+'| D9 新192实际视频与量化对照 | 8450ORT前向、2654实际O8视频前向、ARM计数 | 全raw、6计数路径及1962三栏视频独立核查 | 原片11、Toros1／0／5；178.24ms平均但118帧超过200ms，同板周期后台待验 |',1)
 file.write_bytes(text.encode('utf-8'));records.append({'path':str(file.resolve()),'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
file=ROOT/'results/entrypoint_updates.json';assert not file.exists();file.write_text(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'updates':records},indent=2)+'\n');print(json.dumps({'updated_entrypoints':3,'whole_goal_complete':False}))
