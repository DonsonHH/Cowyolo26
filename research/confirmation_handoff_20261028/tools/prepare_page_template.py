from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT.parent/'counting_recovery_20261028/templates/preview.html').read_text(encoding='utf-8')
source=source.replace('奶牛通道漏计优化对照','确认前入口观察交接对照').replace('奶牛通道：旧8头结果与新对照','奶牛通道：确认前入口观察交接')
source=source.replace('video_rotation_preview.html','counting_recovery_preview.html')
start=source.index('<div class="notice">');end=source.index('</div>',start)+6
source=source[:start]+'<div class="notice">两组使用相同冻结权重、全图640、5Hz和跟踪框。右侧仅在轨迹确认后接回紧邻的一次入口观察，三次稳定规则保持不变。三个seed的向下预测11／10／11→12／11／11；尚未取得独立逐事件准确率。</div>'+source[end:]
source=source.replace('旧方案：整幅图320 · 5Hz','原计数：只接收已确认轨迹')
start=source.index('<p class="muted">5Hz方案');end=source.index('</p>',start)+4
source=source[:start]+'<p class="muted">两组均为5Hz推理、25fps回放，非推理帧保留最近跟踪框；每ID仅暂存一次观察，确认失败即丢弃。事件只在当前已确认观察时发布。临时ID不代表档案身份，服务器回放不代表板上速度。</p>'+source[end:]
source=source.replace('全部开发对照与后续三seed确认','三个冻结模型的配对结果')
source=source.replace('<th>配置 / seed</th><th>输入边长 / Hz</th><th>向下 / 向上预测</th><th>ROI原始检测帧</th><th>ROI跟踪帧</th><th>稳定样本</th>',
 '<th>seed</th><th>原向下 / 向上</th><th>新向下 / 向上</th><th>接回观察 / 次</th><th>新增事件源帧</th><th>消失事件</th>')
start=source.index('<p class="muted">先按固定检测');end=source.index('</p>',start)+4
source=source[:start]+'<p class="muted">全部三个seed均保留；接回观察次数不是实际奶牛数量。当前只修复一种入口观察交接损失，B区断续与真实重复／漏计风险仍需独立复核。</p>'+source[end:]
source=source.replace('counting_recovery_preview_data.json','confirmation_handoff_preview_data.json')
source=source.replace('；ROI检测${row.raw_ROI_frames}/${row.sampled_frames_in_scope}帧','；相同跟踪框，保留确认前一次观察')
old='for(const r of data.all_results){const tr=document.createElement(\'tr\');for(const value of [r.name,`${r.arm.imgsz} / ${25/r.arm.stride}`,`${r.predicted_down} / ${r.predicted_up}`,`${r.raw_ROI_frames}/${r.sampled_frames_in_scope}`,`${r.tracked_ROI_frames}/${r.sampled_frames_in_scope}`,r.arm.stable_samples])'
new='for(const r of data.comparisons){const tr=document.createElement(\'tr\');for(const value of [r.seed,`${r.baseline_down} / ${r.baseline_up}`,`${r.handoff_down} / ${r.handoff_up}`,r.history_acceptances_in_scope,r.added_events.map(e=>e.source_frame).join(\', \')||\'无\',r.removed_events.length])'
assert old in source;source=source.replace(old,new)
folder=ROOT/'templates';folder.mkdir(exist_ok=True);path=folder/'preview.html';assert not path.exists();path.write_text(source,encoding='utf-8');print('handoff page template created')
