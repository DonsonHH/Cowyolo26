from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=(ROOT/'tools/replay.py').read_text(encoding='utf-8')
assert source.count('t.tlbr')==1
source=source.replace('from ultralytics.trackers.byte_tracker import BYTETracker','from ultralytics.trackers.byte_tracker import BYTETracker,STrack')
source=source.replace("sys.path.insert(0,str(ROOT/'input'))","OUT=ROOT/'results/replay_v2'\nsys.path.insert(0,str(ROOT/'input'))")
source=source.replace("dest=ROOT/f'results/seed{seed}'","dest=OUT/f'seed{seed}'").replace('t.tlbr','t.xyxy')
source=source.replace("torch.set_num_threads(2)\n    p=", "torch.set_num_threads(2)\n    OUT.mkdir(exist_ok=False)\n    probe=STrack(np.asarray([100.,100.,40.,50.,0.],np.float32),.9,0)\n    assert np.array_equal(probe.xyxy,np.array([80.,75.,120.,125.]))\n    p=")
source=source.replace("ROOT/'results/behavior_server_green.txt'","OUT/'behavior_server_green.txt'").replace("ROOT/'results/summary.json'","OUT/'summary.json'")
target=ROOT/'tools/replay_v2.py';assert not target.exists();target.write_text(source,encoding='utf-8')
source=(ROOT/'tools/replay.slurm').read_text(encoding='utf-8').replace('cow-confirmation-handoff','cow-confirmation-handoff-v2').replace('logs/replay-%j','logs/replay_v2-%j').replace('tools/replay.py','tools/replay_v2.py')
target=ROOT/'tools/replay_v2.slurm';assert not target.exists();target.write_text(source,encoding='utf-8',newline='\n')
r={'previous_failed_job':130241,'prior_replay_sha256':sha(ROOT/'tools/replay.py'),'corrected_replay_sha256':sha(ROOT/'tools/replay_v2.py'),
   'correction':'Read installed STrack.xyxy instead of legacy tlbr; add real STrack coordinate smoke; separate output folder',
   'counter_module_sha256':sha(ROOT/'tools/confirmation_counter.py'),'handoff_rule_or_parameters_changed':False}
target=ROOT/'protocol/replay_implementation_v2.json';assert not target.exists();target.write_text(json.dumps(r,indent=2),encoding='utf-8');print(json.dumps(r))
