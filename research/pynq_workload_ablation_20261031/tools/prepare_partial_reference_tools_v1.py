"""Preserve unused full-plan tools; produce clearly scoped failed-plan tools."""
from pathlib import Path
import ast

root = Path(__file__).resolve().parents[1]


def derive(original, destination, replacements):
    source = (root / 'tools' / original).read_text(encoding='utf-8')
    for old, new in replacements:
        assert source.count(old) == 1, (original, old, source.count(old))
        source = source.replace(old, new)
    ast.parse(source)
    with (root / 'tools' / destination).open('x', encoding='utf-8') as stream:
        stream.write(source)


derive('prepare_tracker_replay.py', 'prepare_partial_tracker_replay_v1.py', [
    ("assert verification['fixed_photo_tensor_raw_feature_score_jobs_verified'] == 40", "assert verification['fixed_photo_tensor_raw_feature_score_jobs_verified'] == 30\nassert verification['task_status'] == 'FAILED' and verification['completed_timed_cases'] == 5"),
    ("for spec in plan['runs']:", "for spec in plan['runs'][:5]:"),
    ('assert len(cases) == 8', 'assert len(cases) == 5'),
    ("replay_source.replace('assert len(reports)==4', 'assert len(reports)==8')", "replay_source.replace('assert len(reports)==4', 'assert len(reports)==5')"),
    ("'ALL8_FULL_TRACKER'", "'ALL5_FULL_TRACKER'"),
    ('"\'counter_paths\':16"', '"\'counter_paths\':10"'),
    ('-B -u tools/plot_results.py', '-B -u tools/plot_partial_results_v1.py'),
    ("ROOT / 'tools/plot_results.py'", "ROOT / 'tools/plot_partial_results_v1.py'"),
    ('FROZEN_FULL_ASSOCIATION_REPLAY_OF_ACTUAL8_INPUT_SCHEDULES', 'FROZEN_FULL_ASSOCIATION_REPLAY_OF_ACTUAL5_COMPLETED_PERIODS_FROM_FAILED_EIGHT_RUN_PLAN'),
])
derive('verify_tracker_reference.py', 'verify_partial_tracker_reference_v1.py', [
    ('ALL8_FULL_TRACKER_ASSOCIATION_AND_EVENT_REPLAYS_MATCH_ACTUAL_ARM_WITH_FROZEN_TOLERANCES', 'ALL5_FULL_TRACKER_ASSOCIATION_AND_EVENT_REPLAYS_MATCH_ACTUAL_ARM_WITH_FROZEN_TOLERANCES'),
    ("assert len(reports) == len(summary['reports']) == 8", "assert len(reports) == len(summary['reports']) == 5"),
    ("assert summary['counter_paths'] == 16", "assert summary['counter_paths'] == 10"),
    ('ALL8_FULL_ASSOCIATIONS_AND16_EVENT_PATHS_CPU_REPLAY_INDEPENDENTLY_VERIFIED', 'FAILED_EIGHT_RUN_PLAN_ALL5_COMPLETED_ASSOCIATIONS_AND10_EVENT_PATHS_CPU_REPLAY_VERIFIED'),
    ("'counter_paths': 16", "'counter_paths': 10"),
])
derive('plot_results.py', 'plot_partial_results_v1.py', [
    ("assert len(cases) == 8 and ''.join(case['condition'] for case in cases) == 'ABCDDCBA'", "assert data['task_status'] == 'FAILED'\nassert len(cases) == 5 and ''.join(case['condition'] for case in cases) == 'ABCDD'"),
    ('x = list(range(1, 9))', 'x = list(range(1, 6))'),
    ("axes[2].set_xticks(x, [f'{index}: {case[\"condition\"]}\\nI={int(case[\"input_producer\"])}, W={int(case[\"identity_workload\"])}' for index, case in zip(x, cases)])",
     "axes[2].set_xticks(range(1, 9), ['1: A\\nI=0,W=0', '2: B\\nI=1,W=0', '3: C\\nI=0,W=1', '4: D\\nI=1,W=1', '5: D\\nI=1,W=1', '6: C\\nnot started', '7: B\\nnot started', '8: A\\nnot started'])\naxes[0].text(7, .55, 'r6 READY timeout\\nr7/r8 not started', transform=axes[0].get_xaxis_transform(), ha='center', fontsize=10)"),
    ("for axis in axes:\n    axis.grid", "for axis in axes:\n    axis.set_xlim(.5, 8.5)\n    axis.axvspan(5.5, 8.5, color='#eeeeee', zorder=0)\n    axis.grid"),
    ('PYNQ-Z2: 2x2 workload ablation on one boot', 'PYNQ-Z2: failed eight-run plan, five timed periods'),
    ('Ready 192-input replay; same resident old encoder; mirrored order; two runs per condition.\\nNo live camera/RFID, independent event labels, or permanent event identity labels.', 'Only A/B/C/D/D completed. Missing timed periods are not zero-throughput observations.\\nReady 192-input replay; same boot; no live camera/RFID or independent event/identity labels.'),
    ('FROZEN_VERIFIED_EIGHT_RUN_SUMMARY_RENDERED', 'VERIFIED_FIVE_TIMED_PERIODS_FROM_FAILED_EIGHT_RUN_PLAN_RENDERED'),
])
print('Failed-plan CPU replay and figure tools prepared; unused eight-run tools preserved.')
