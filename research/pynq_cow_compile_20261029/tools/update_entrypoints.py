from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
para='最新在用户确认的O8引擎完成[奶牛单类权重实机准入](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_cow_compile_20261029/奶牛单类权重O8实机准入.md>)及[自审](<C:/Users/Donson/Documents/ChatGPT/奶牛/pynq_cow_compile_20261029/Review与当前状态.md>)：冻结旧seed26权重经128训练图PTQ、单类头和三个精确索引／广播结构改写后，生成94PL＋8ARM整数卷积、25对驻留的192部署图。8训练输入上，CPU整数参考、原生C++和真实PYNQ-Z2输出相同，含2预热10次板端推理，原O8固件／SO保持。均值140.30ms仅为固定张量到raw短测，未合并为完整FPS；源视频计数和前后台联合仍待验。15个新低分辨率候选已全部完成10轮并共同冻结，训练作业收尾LF误判及记录恢复边界保留，统一评价继续进行，不按原片12头选择权重。'
records=[]
for relative in ['研究总览_从想法到论文.md','研究进度.md','phase3_diagnosis_20261026/方案与执行状态.md']:
    file=PROJECT/relative;before=file.read_bytes();text=before.decode('utf-8');marker='最新已完成[真实PYNQ-Z2三尺寸性能与输入瓶颈验证]'
    assert marker in text and '最新在用户确认的O8引擎' not in text;nl='\r\n' if '\r\n' in text else '\n';i=text.index(marker)
    text=text[:i]+para+nl+nl+text[i:]
    if relative.startswith('phase3'):
        line=next(row for row in text.splitlines() if row.startswith('| D3 真实PYNQ-Z2性能'))
        text=text.replace(line,line+nl+'| D4 奶牛单类权重O8准入 | 训练内校准、整数参考与真实PL/ARM输出 | 192旧seed26，8训练向量输出相同，设备安全关闭 | 编译／首轮实现核查通过；新15权重统一评价、实际视频计数及后台联合仍待验 |',1)
    file.write_bytes(text.encode('utf-8'));records.append({'path':str(file.resolve()),'before_sha256':hashlib.sha256(before).hexdigest(),'after_sha256':hashlib.sha256(file.read_bytes()).hexdigest()})
file=ROOT/'计划与验收.md';text=file.read_text(encoding='utf-8');text+='\n## 首轮实现准入完成\n\n服务器130531导出和PTQ完成后在分类LUT模块路径上失败；续编130539只复用成功导出／校准，在新工作副本改写结构并完成整数参考核对。真实板端PID12010执行2预热＋8训练向量，raw与CPU整数参考一致并安全关闭，未编程新固件。15新训练权重由130542完成共同冻结；单类模型实际视频计数、256／320同O8和后台联合5FPS保持下一关口。\n';file.write_text(text,encoding='utf-8')
file=ROOT/'results/entrypoint_updates.json';assert not file.exists();file.write_text(json.dumps({'created_host_UTC':datetime.now(timezone.utc).isoformat(),'files':records},indent=2)+'\n')
print(json.dumps({'updated_entrypoints':3,'old_seed26_cow_O8_implementation_verified':True,'whole_goal_complete':False}))
