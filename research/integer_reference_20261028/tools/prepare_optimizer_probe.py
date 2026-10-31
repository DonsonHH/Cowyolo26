from pathlib import Path
from datetime import datetime, timezone
import hashlib, json
ROOT = Path(__file__).resolve().parents[1]
REMOTE = '/share/home/renly/projects/idcoo_research_20261026/integer_reference_20261028'
files = ['results/reference/integer_accumulator_candidate.onnx',
         'results/reference/whole_model_vectors.npz', 'results/reference/summary.json']
path = ROOT / 'protocol/optimizer_probe_v1.json'
assert not path.exists()
protocol = {
    'name': 'Serialized actual ORT optimizer graph replay and first-divergence probe v1',
    'created_UTC': datetime.now(timezone.utc).isoformat(),
    'ORT_version': '1.23.2', 'provider': 'CPUExecutionProvider', 'threads': [2, 1],
    'inputs': [{'remote_path': REMOTE + '/' + p, 'local_path': str(ROOT / 'delivery' / p),
                'sha256': hashlib.sha256((ROOT / 'delivery' / p).read_bytes()).hexdigest()} for p in files],
    'levels': ['OFF', 'BASIC', 'EXTENDED', 'ALL'],
    'trace_vectors': [2, 5], 'all_baseline_vectors': list(range(8)),
    'method': ['Reproduce all8 priorOFF/ALL outputs without added graph outputs',
               'Save actualALLoptimized graph, reload with optimizationOFF, require exactALL output replay',
               'Only then add common typed tensor outputs to frozenOFF/serializedALL graphs, optimizationOFF',
               'Require augmented embeddings bit-identical before interpreting firstdifferences',
               'Report earliest common float and integer divergences, preserve graphs and actual tensors'],
    'gate': {'maximum_absolute_embedding_error': .001, 'minimum_cosine': .9999},
    'no_claim': 'No newtraining, accuracy, newdata orFPGA result; firstcommon difference need not identify a unique causal optimizer without controlled isolation.',
    'whole_goal_complete': False}
path.write_text(json.dumps(protocol, indent=2), encoding='utf-8')
print(json.dumps({'protocol_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'frozen_inputs': len(files)}))
