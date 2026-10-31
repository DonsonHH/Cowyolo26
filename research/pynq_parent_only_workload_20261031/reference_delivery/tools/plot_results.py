"""A chronological scientific figure, preserving both repeats and all failures."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, os, socket
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
assert os.environ.get('SLURM_JOB_ID') and socket.gethostname() != 'mu01'
source = ROOT / 'tracker_input/workload_summary.json'
data = json.loads(source.read_text())
cases = data['cases']
assert len(cases) == 8 and ''.join(case['condition'] for case in cases) == 'ABCDDCBA'
out = ROOT / 'results/figures'
out.mkdir(exist_ok=False)
colors = {'A': '#355e91', 'B': '#238274', 'C': '#aa6c24', 'D': '#a34d67'}
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                     'axes.spines.top': False, 'axes.spines.right': False, 'svg.fonttype': 'none'})
fig, axes = plt.subplots(3, 1, figsize=(10, 10), sharex=True)
x = list(range(1, 9))
axes[0].plot(x, [case['processed_per_second_over_offered_duration'] for case in cases], color='#9b9b9b', lw=1)
for index, case in zip(x, cases):
    fps = case['processed_per_second_over_offered_duration']
    axes[0].scatter(index, fps, color=colors[case['condition']], s=55, zorder=3)
    axes[0].annotate(f'{fps:.3f}', (index, fps), xytext=(0, 9), textcoords='offset points', ha='center', fontsize=9)
axes[0].axhline(5, color='#393939', lw=1, ls='--', label='5 FPS offer rate')
axes[0].set(ylabel='Processed frames / 78.4 s (FPS)', title='Throughput in frozen execution order')
axes[0].set_ylim(min(case['processed_per_second_over_offered_duration'] for case in cases) - .15, 5.13)
axes[0].legend(frameon=False, loc='lower left', fontsize=9)
axes[1].bar(x, [case['deadline_misses'] for case in cases], color=[colors[case['condition']] for case in cases], alpha=.82, width=.55, label='Processed frames finishing after 200 ms')
axes[1].plot(x, [case['skipped_slots'] for case in cases], color='#262626', marker='x', lw=1, label='Unprocessed offer slots')
axes[1].set(ylabel='Frames or slots', ylim=(0, 410), title='Deadline misses and skipped slots have different denominators')
axes[1].legend(frameon=False, loc='upper right', fontsize=9)
axes[2].plot(x, [case['foreground_VmSwap_kB_at_end'] / 1024 for case in cases], color='#6d5784', marker='o', lw=1.5)
axes[2].set(ylabel='Parent VmSwap at run end (MiB)', xlabel='Chronological run: condition (I=JPEG producer, W=fixed 10 jobs)',
            title='Observed memory state; this is not a causal swap experiment')
axes[2].set_xticks(x, [f'{index}: {case["condition"]}\nI={int(case["input_producer"])}, W={int(case["identity_workload"])}' for index, case in zip(x, cases)])
for axis in axes:
    axis.grid(axis='y', color='#dce0e5', lw=.6)
    axis.set_axisbelow(True)
fig.suptitle('PYNQ-Z2: 2x2 workload ablation on one boot', fontsize=15, y=.98)
fig.text(.5, .025, 'Ready 192-input replay; same resident old encoder; mirrored order; two runs per condition.\nNo live camera/RFID, independent event labels, or permanent event identity labels.', ha='center', fontsize=9)
fig.subplots_adjust(left=.11, right=.97, top=.92, bottom=.12, hspace=.42)
paths = []
for extension in ['png', 'svg']:
    path = out / ('chronological_workload.' + extension)
    fig.savefig(path, dpi=170, facecolor='white')
    paths.append({'file': path.relative_to(ROOT).as_posix(), 'bytes': path.stat().st_size,
                  'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
plt.close(fig)
manifest = {'status': 'FROZEN_VERIFIED_EIGHT_RUN_SUMMARY_RENDERED',
            'created_UTC': datetime.now(timezone.utc).isoformat(), 'Slurm_job_id': os.environ['SLURM_JOB_ID'],
            'matplotlib_version': matplotlib.__version__, 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'files': paths, 'new_model_forwards': 0, 'rendering_visually_reviewed': False}
with (ROOT / 'results/figure_manifest.json').open('x') as stream:
    json.dump(manifest, stream, indent=2)
    stream.write('\n')
print(json.dumps(manifest), flush=True)
