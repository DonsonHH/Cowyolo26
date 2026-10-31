from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT.parent/'confirmation_handoff_20261028/templates/preview.html').read_text(encoding='utf-8')
s=s.replace('确认前入口观察交接对照','第二阶段纯IoU配对对照').replace('奶牛通道：确认前入口观察交接','奶牛通道：低分匹配恢复，事件数量未变')
s=s.replace('counting_recovery_preview.html','confirmation_handoff_preview.html').replace('confirmation_handoff_preview_data.json','secondstage_iou_preview_data.json')
start=s.index('<div class="notice">');end=s.index('</div>',start)+6
s=s[:start]+'<div class="notice">右侧只去掉第二阶段的分数融合，门槛0.5不变；第一阶段、Lost资格、检测框输入和入口观察交接计数保持相同。三个seed均维持向下12／11／11，事件时间和方向一致；低分匹配已恢复，独立准确率仍待人工参考。</div>'+s[end:]
s=s.replace('原计数：只接收已确认轨迹','原第二阶段：分数融合代价')
s=s.replace('；相同跟踪框，保留确认前一次观察','；第二阶段纯IoU，计数规则相同')
start=s.index('<p class="muted">两组均为5Hz');end=s.index('</p>',start)+4
s=s[:start]+'<p class="muted">两组均为全图640、5Hz推理、25fps回放和相同3次稳定规则。绿色框为各自实际跟踪输出；ID编号变化不代表奶牛身份变化。服务器回放不代表PYNQ-Z2速度。</p>'+s[end:]
s=s.replace('<th>seed</th><th>原向下 / 向上</th><th>新向下 / 向上</th><th>接回观察 / 次</th><th>新增事件源帧</th><th>消失事件</th>',
 '<th>seed</th><th>原向下 / 向上</th><th>新向下 / 向上</th><th>本段低分匹配次数</th><th>ROI观察行 原→新</th><th>事件时间 / 方向</th>')
start=s.index('<p class="muted">全部三个seed');end=s.index('</p>',start)+4
s=s[:start]+'<p class="muted">低分匹配次数统计本时间段全画面，不等于ROI奶牛数量。全部三个seed及无新增事件结果均保留；当前不将该控制认领为计数准确率改进。</p>'+s[end:]
old='[r.seed,`${r.baseline_down} / ${r.baseline_up}`,`${r.handoff_down} / ${r.handoff_up}`,r.history_acceptances_in_scope,r.added_events.map(e=>e.source_frame).join(\', \')||\'无\',r.removed_events.length]'
new='[r.seed,`${r.baseline_down} / ${r.baseline_up}`,`${r.candidate_down} / ${r.candidate_up}`,r.low_matches_in_scope,`${r.ROI_rows_before} → ${r.ROI_rows_after}`,r.event_times_directions_equal?\'一致\':\'有变化\']'
assert old in s;s=s.replace(old,new)
folder=ROOT/'templates';folder.mkdir(exist_ok=True);path=folder/'preview.html';assert not path.exists();path.write_text(s,encoding='utf-8');print('singlefactor preview template prepared')
