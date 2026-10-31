from pathlib import Path
from datetime import datetime, timezone
import difflib, hashlib, json

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
load = lambda path: json.loads(path.read_text(encoding='utf-8-sig'))
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
link = lambda label, name: f'[{label}](<{(PROJECT / name).as_posix()}>)'
old = load(ROOT / 'results/overview_review_20261031_v22_recovery.json')
main = PROJECT / '研究阶段总结_20261030.md'
assert sha(main) == old['document']['sha256']
stage_path = PROJECT / 'pynq_workload_ablation_20261031/results/final_review_v1.json'
stage = load(stage_path)
assert stage['task_status'] == 'FAILED' and stage['completed_timed_cases'] == 5
assert stage['actual_counts'] == [7, 8, 10, 10, 3] and stage['all_actual_board_image_forwards'] == 1804
assert not stage['full5FPS_target_achieved'] and not stage['whole_goal_complete']
paths = [main, PROJECT / '研究总览_从想法到论文.md', PROJECT / '研究进度.md',
         PROJECT / 'phase3_diagnosis_20261026/方案与执行状态.md', ROOT / 'Review与当前状态.md']
snapshot = ROOT / 'snapshots/overview_v22_before_workload_failure'
snapshot.mkdir(parents=True, exist_ok=False)
before, copies = {}, []
for path in paths:
    before[path] = path.read_text(encoding='utf-8')
    destination = snapshot / path.relative_to(PROJECT)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(path.read_bytes())
    copies.append({'path': str(path), 'snapshot': str(destination), 'sha256': sha(destination)})
report = link('高分输入与身份负载五轮及启动超时', 'pynq_workload_ablation_20261031/高分输入与身份负载_五轮结果和启动超时.md')
review = link('本阶段完整复核', 'pynq_workload_ablation_20261031/results/final_review_v1.json')
supplement = link('论文负载实验补充', 'paper_readiness_20261030/论文补充_板上负载退化与启动失败_20261031.md')
latest = ('2026年10月31日最新实机进展：' + report + '原定八轮A/B/C/D/D/C/B/A，只完成五个正式时段，'
          '第6轮准备等待后台READY超过40秒后FAILED，未补跑。五轮处理率4.694／4.694／4.885／4.375／3.648FPS，'
          '计数7／8／10／10／3，人工总数12；1748正式raw、30身份任务、1804含预热板端图前向全部核验。'
          '10663观察／2338跟踪行及10计数路径的CPU完整关联复算通过，新增CPU神经参考0。'
          '当前boot未变，SSH／Jupyter仍active、未发现OOM相关日志；内存与READY分段根因尚未证实。'
          '稳定5FPS、独立事件和永久牛号仍待证据。' + supplement + '保留失败及未执行范围，v3原稿不改。')
for path in paths[1:]:
    heading, rest = before[path].split('\n', 1)
    rest = rest.lstrip('\n')
    assert rest.startswith('2026年10月31日恢复进展：')
    rest = rest.replace('2026年10月31日恢复进展：', '此前原结果恢复进展：', 1)
    extra = ' ' + link('第23版总览复核', 'research_synthesis_20261027/results/overview_review_20261031_v23_workload.json') + '。' if path == ROOT / 'Review与当前状态.md' else ''
    path.write_text(heading + '\n\n' + latest + extra + '\n\n' + rest, encoding='utf-8')
text = before[main]
assert text.count('2026年10月31日恢复进展：') == 1
text = text.replace('2026年10月31日恢复进展：', latest + '\n\n此前原结果恢复进展：', 1)
start = text.index('**当前进展：')
end = text.index('**', start + 2) + 2
text = text[:start] + ('**当前进展：访问已恢复，原四轮实际触发结果完整通过；新增同负载八轮方案只完成五轮，'
                       '第6轮后台启动READY超时，五轮3.648–4.885FPS、计数7／8／10／10／3，稳定完整5FPS仍未达到。'
                       '全部可得原始输出与CPU完整关联已验收；下一步先度量后台启动与驻留内存，根因及修复尚未证明。'
                       '身份覆盖、独立事件／永久牛号、真实输入和功耗仍缺；论文v3与本轮补充均非投稿终稿。**') + text[end:]
old_row = '| 实际计数触发四轮已完整核验 | 10／10／8／7；4.630–4.770FPS，35任务、原包及CPU参考通过 | 仍低于5FPS与人工12；逐事件／永久牛号缺失，任务负载不完全配对 |'
assert text.count(old_row) == 1
text = text.replace(old_row, '| 同负载资源控制：八轮计划失败 | 五轮A/B/C/D/D，3.648–4.885FPS；1748raw、30任务和完整关联通过 | 第6轮READY超时，缺后半重复；启动／换页根因和稳定5FPS未证实 |\n' + old_row, 1)
section = f'''### 3.15 高分取得与固定身份工作量：五轮通过复算，八轮方案失败

{report}保持同一192检测器、原O8、已就绪低分帧、相同身份编码器及10固定照片。每轮都启动同样后台并预热；I控制逐时隙JPEG生产／校验／有界银行，W控制0或10正式身份任务。镜像顺序A/B/C/D/D/C/B/A原定八轮，实际只完成前五轮。

| 轮次 | I/W | 处理/392 | 跳过 | >200ms | FPS | P95ms | 下行计数/人工12 |
|---|---|---:|---:|---:|---:|---:|---:|
| r1_A | 0/0 | 368 | 24 | 16 | 4.694 | 178.31 | 7 |
| r2_B | 1/0 | 368 | 24 | 35 | 4.694 | 235.76 | 8 |
| r3_C | 0/1 | 383 | 9 | 86 | 4.885 | 312.58 | 10 |
| r4_D | 1/1 | 343 | 49 | 342 | 4.375 | 486.24 | 10 |
| r5_D | 1/1 | 286 | 106 | 286 | 3.648 | 786.02 | 3 |

第6轮在父进程等待后台READY超过40秒后FAILED；它只完成前史、2检测预热和1身份预热，未开启正式时段。子进程随后留下正常0正式任务终态；最后B/A未开始。原任务未重启补跑。缺失的后半组使时间顺序、缓存／换页与条件仍混在一起，不认领已分离的因果效应。

1748正式检测＋8准入＋12检测预热＋30正式身份＋6身份预热，共1804板端图前向；全部已得raw及照片／tensor／特征／分数复核。1176生产记录、997前台接收、765调用重叠案例核对；CPU任务130931以0神经前向完整重放10663观察／2338跟踪行、10事件路径，ID／事件和坐标实际相同。

三轮10身份任务的主阈值接受各1，是同一照片重复，无永久牛号正确率。两次D的最大入队至结果1877.17／4794.70ms，父进程末VmSwap137.88／146.38MiB；这只是资源线索。第5轮起始资源采样晚于时钟37.018878ms，增量按实际窗口解释。boot未变、服务active、内核未发现OOM日志，不将READY超时直接归因于电源、OOM或模型崩溃。

本次在新boot持锁明确加载既有accepted O8，未改文件；与上一阶段只读取回原结果分开。原失败包16,856,960字节及参考包5,801,192字节均完整取回、清单／hash通过。协议旧四轮预算继承字段冲突和核验v1错误边界假定均保留修正说明；最终错误寄存器状态未采样，不用正常close补成error=0。

{review}与{supplement}已接入；当前依然没有现场相机／RFID、独立事件JSON、原12事件永久牛号或功耗。下一步先测量子进程导入／装载／预热／READY分段和PSS，再选择单因素改动；不能只延长超时就称修好实时性。

'''
assert text.count('## 4. 数据还需要怎样补') == 1
text = text.replace('## 4. 数据还需要怎样补', section + '## 4. 数据还需要怎样补', 1)
old_step = '3. 实际计数触发四轮原包、数值、照片CPU参考和完整关联重放均已完成验收；保留10／10／8／7及全部迟到／跳过。下一步按独立事件参考定位质量差异，并以相同输入取得和明确任务负载做时序控制；不重跑替换原结果，也不把较少身份任务当效率改进。'
new_step = '3. 原实际触发四轮保持完整核验；新增固定负载八轮方案在第6轮READY超时，前五轮全部原始数据／完整关联已验收，保留计数7／8／10／10／3。先记录导入、装载、预热、READY发布／接收及PSS，建立可区分原因的测量，再做单因素改动；不补跑替换原失败，不将缺失组当平衡对照。'
assert text.count(old_step) == 1
text = text.replace(old_step, new_step, 1)
for line in text.splitlines():
    if line.startswith('6. ') and '论文草稿v3' in line:
        assert text.count(line) == 1
        text = text.replace(line, line + ' ' + supplement + '补充本次5轮及启动失败，C11继续待证据。', 1)
        break
else:
    raise AssertionError('Expected v3 paper step')
needle = '## 7. 本轮状态与自审\n\n'
assert text.count(needle) == 1
text = text.replace(needle, needle + '本轮新增高分取得／固定身份工作量的八轮冻结方案，明确保留第6轮失败和后三个正式时段未执行。五轮数据、完整关联及实际结果图均自审；1748检测／30任务、含预热1804板端前向独立记账，CPU新增神经前向0。' + review + '。旧v22与原四轮恢复证据留在快照，本阶段不是稳定5FPS、根因修复或论文投稿完成。\n\n', 1)
main.write_text(text, encoding='utf-8')
diff = []
for path in paths:
    diff.extend(difflib.unified_diff(before[path].splitlines(), path.read_text(encoding='utf-8').splitlines(),
                                    fromfile=str(path.relative_to(PROJECT)) + ' v22', tofile=str(path.relative_to(PROJECT)) + ' v23', n=2))
diff_path = ROOT / 'results/overview_diff_20261031_v23_workload.txt'
with diff_path.open('x', encoding='utf-8') as stream:
    stream.write('\n'.join(diff) + '\n')
supplement_path = PROJECT / 'paper_readiness_20261030/论文补充_板上负载退化与启动失败_20261031.md'
record = {'status': 'FIVE_ENTRYPOINTS_UPDATED_WITH_FAILED_EIGHT_RUN_PLAN_AND_FIVE_VERIFIED_PERIODS',
          'created_UTC': datetime.now(timezone.utc).isoformat(), 'previous_files_and_snapshots': copies,
          'current_entrypoints': [{'path': str(path), 'sha256': sha(path)} for path in paths],
          'new_documents': [{'path': str(supplement_path), 'sha256': sha(supplement_path)}],
          'diff': {'path': str(diff_path), 'sha256': sha(diff_path)},
          'new_review_sources': [{'path': str(stage_path), 'sha256': sha(stage_path)}], 'whole_goal_complete': False}
with (ROOT / 'results/entrypoint_update_20261031_v23_workload.json').open('x', encoding='utf-8') as stream:
    json.dump(record, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'status': record['status'], 'main_lines': len(text.splitlines()), 'diff_lines': len(diff)}))
