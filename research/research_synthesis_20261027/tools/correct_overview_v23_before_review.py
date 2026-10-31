"""Resolve two prose scope ambiguities before the first V23 review is frozen."""
from pathlib import Path
from datetime import datetime, timezone
import difflib, hashlib, json

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
assert not (ROOT / 'results/overview_review_20261031_v23_workload.json').exists()
prior = ROOT / 'results/entrypoint_update_20261031_v23_workload.json'
entry = json.loads(prior.read_text(encoding='utf-8'))
for row in entry['current_entrypoints'] + entry['new_documents']:
    assert sha(Path(row['path'])) == row['sha256']
main = PROJECT / '研究阶段总结_20261030.md'
paper = PROJECT / 'paper_readiness_20261030/论文补充_板上负载退化与启动失败_20261031.md'
old = '4. 历次回放已暴露8／9／10计数波动，以及部分策略的后台饥饿；同负载控制已完成。继续补真实触发与长时负载，记录前台迟到和身份等待，不以少触发任务或事后挑一轮作为优胜。'
new = '4. 历次回放已暴露3／7／8／9／10计数波动，以及部分策略的后台饥饿。此前固定10照片的CPU分配和新旧编码器对照已完成；本次I×W八轮控制未完成。继续补真实触发与长时负载，记录前台迟到和身份等待，不以少触发任务或事后挑一轮作为优胜。'
text = main.read_text(encoding='utf-8')
assert text.count(old) == 1
main.write_text(text.replace(old, new, 1), encoding='utf-8')
text = paper.read_text(encoding='utf-8')
old_paper = '上述结果支持“此配置尚未达到稳定5FPS及可靠自动找回”'
new_paper = '上述结果表明该配置未达稳定5FPS，可靠自动找回仍未获验证'
assert text.count(old_paper) == 1
paper.write_text(text.replace(old_paper, new_paper, 1), encoding='utf-8')
diff = []
for row in entry['previous_files_and_snapshots']:
    path, snapshot = Path(row['path']), Path(row['snapshot'])
    assert sha(snapshot) == row['sha256']
    diff.extend(difflib.unified_diff(snapshot.read_text(encoding='utf-8').splitlines(), path.read_text(encoding='utf-8').splitlines(),
                                    fromfile=str(path.relative_to(PROJECT)) + ' v22', tofile=str(path.relative_to(PROJECT)) + ' v23', n=2))
diff_path = ROOT / 'results/overview_diff_20261031_v23_workload_v2.txt'
with diff_path.open('x', encoding='utf-8') as stream:
    stream.write('\n'.join(diff) + '\n')
entry.update({'created_UTC': datetime.now(timezone.utc).isoformat(),
              'pre_review_revision_of': {'path': str(prior), 'sha256': sha(prior)},
              'scope_corrections': [new, new_paper],
              'current_entrypoints': [{'path': row['path'], 'sha256': sha(Path(row['path']))} for row in entry['current_entrypoints']],
              'new_documents': [{'path': str(paper), 'sha256': sha(paper)}],
              'diff': {'path': str(diff_path), 'sha256': sha(diff_path)}})
with (ROOT / 'results/entrypoint_update_20261031_v23_workload_v2.json').open('x', encoding='utf-8') as stream:
    json.dump(entry, stream, ensure_ascii=False, indent=2)
    stream.write('\n')
print(json.dumps({'status': 'TWO_PROSE_SCOPE_AMBIGUITIES_CORRECTED_BEFORE_V23_REVIEW', 'corrections': entry['scope_corrections']}))
