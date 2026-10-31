"""Freeze a zero-model-forward CPU association replay of all eight schedules."""
from pathlib import Path
from datetime import datetime, timezone
import argparse, gzip, hashlib, json, re, tarfile

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
parser = argparse.ArgumentParser()
parser.add_argument('--partition', required=True, help='Use the freshly inspected live CPU partition')
args = parser.parse_args()
assert re.fullmatch(r'[A-Za-z0-9_-]+', args.partition)
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
load = lambda path: json.loads(path.read_text(encoding='utf-8'))
verification = load(ROOT / 'results/independent_verification.json')
assert verification['fixed_photo_tensor_raw_feature_score_jobs_verified'] == 40
plan = load(ROOT / 'protocol/run_v1.json')
stage = ROOT / 'tracker_input'
stage.mkdir(exist_ok=False)
(stage / 'workload_summary.json').write_bytes((ROOT / 'results/independent_verification.json').read_bytes())
source = PROJECT / 'pynq_frontend_port_20261029'
for row in plan['runtime_files']:
    marker = '/cow_research_numpy_tracker_20261029/'
    if marker in row['file']:
        name = row['file'].split(marker, 1)[1]
        path = source / name
        assert sha(path) == row['sha256']
        output = stage / 'source' / name
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(path.read_bytes())
history = json.loads(gzip.decompress((PROJECT / 'pynq_mosaic192_eval_20261030/board_delivery/results/original/raw_predictions.json.gz').read_bytes()))
history = [row for row in history if row['frame0'] < 8915]
assert len(history) == 1783
with gzip.GzipFile(filename=str(stage / 'history.json.gz'), mode='wb', mtime=0) as stream:
    stream.write(json.dumps(history, separators=(',', ':')).encode())
cases = []
for spec in plan['runs']:
    folder = stage / spec['run']
    folder.mkdir()
    original = ROOT / 'delivery/results' / spec['run']
    for name in ['actual_raw.npz', 'counter_trace.json.gz']:
        (folder / name).write_bytes((original / name).read_bytes())
    cases.append({'run': spec['run'], 'raw': 'tracker_input/' + spec['run'] + '/actual_raw.npz',
                  'trace': 'tracker_input/' + spec['run'] + '/counter_trace.json.gz'})
assert len(cases) == 8
replay_source = (PROJECT / 'identity_joint_pair_20261030/tools/replay_tracker.py').read_text(encoding='utf-8')
assert 'assert len(reports)==4' in replay_source and "'counter_paths':8" in replay_source
replay_source = replay_source.replace('assert len(reports)==4', 'assert len(reports)==8')
replay_source = replay_source.replace('ALL4_FULL_TRACKER', 'ALL8_FULL_TRACKER').replace("'counter_paths':8", "'counter_paths':16")
replay = ROOT / 'tools/replay_tracker.py'
with replay.open('xb') as stream:
    stream.write(replay_source.encode())
remote = '/share/home/renly/projects/idcoo_research_20261026/pynq_parent_only_workload_20261031'
slurm = f'''#!/bin/bash
#SBATCH --job-name=cow-parent-track
#SBATCH --partition={args.partition}
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output={remote}/logs/tracker-%j.out
#SBATCH --error={remote}/logs/tracker-%j.err
set -euo pipefail
export OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 PYTHONDONTWRITEBYTECODE=1
cd {remote}
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -B -u tools/replay_tracker.py
srun /share/home/renly/projects/idcoo_research_20261026/env/bin/python -B -u tools/plot_results.py
'''
script = ROOT / 'tools/tracker_replay.slurm'
with script.open('xb') as stream:
    stream.write(slurm.encode())
files = sorted([path for path in stage.rglob('*') if path.is_file()] + [replay, script, ROOT / 'tools/plot_results.py'])
protocol = {'status': 'FROZEN_FULL_ASSOCIATION_REPLAY_OF_ACTUAL8_INPUT_SCHEDULES',
            'created_UTC': datetime.now(timezone.utc).isoformat(),
            'source_board_protocol_sha256': sha(ROOT / 'protocol/run_v1.json'),
            'video': plan['video'], 'tracker_config': plan['tracker_config'], 'counter_kwargs': plan['counter_kwargs'],
            'cases': cases, 'box_tolerance_pixels': .002, 'axis_tolerance': 2e-6,
            'IDs_and_events_exact_required': True, 'model_forwards': 0,
            'files': [{'file': path.relative_to(ROOT).as_posix(), 'sha256': sha(path)} for path in files]}
(stage / 'protocol.json').write_bytes((json.dumps(protocol, indent=2) + '\n').encode())
archive = ROOT / 'tracker_input_v1.tar.gz'
assert not archive.exists()
with tarfile.open(archive, 'w:gz') as tar:
    for path in files + [stage / 'protocol.json']:
        tar.add(path, arcname=path.relative_to(ROOT).as_posix(), recursive=False)
result = {'archive': str(archive), 'bytes': archive.stat().st_size, 'sha256': sha(archive),
          'members': len(files) + 1, 'new_model_forwards': 0}
with (ROOT / 'evidence/tracker_input_bundle.json').open('x', encoding='utf-8') as stream:
    json.dump(result, stream, indent=2)
    stream.write('\n')
print(json.dumps(result))
