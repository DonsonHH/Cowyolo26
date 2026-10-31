from pathlib import Path
from datetime import datetime,timezone
import ast,hashlib,json,shutil,tarfile

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parent
STUDY=PROJECT/'cows2021_adaptation_20261027'


def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    base=json.loads((STUDY/'protocol/detector_v1.json').read_text(encoding='utf-8'))
    freeze_path=STUDY/'delivery/results/training/all_checkpoints_frozen_before_video.json'
    freeze=json.loads(freeze_path.read_text(encoding='utf-8'))
    assert freeze['source_Toros_or_candidate_final_forward_before_freeze'] is False
    prior=STUDY/'delivery/results/inference'
    summary=json.loads((prior/'summary.json').read_text(encoding='utf-8'))
    assert summary['training_freeze_sha256']==sha(freeze_path)
    protocol={'name':'Frozen detector0/90 input video replay in native tracker coordinates v1',
              'created_UTC':datetime.now(timezone.utc).isoformat(),
              'scope':'Diagnostic on previously used development videos and6event Toros reference; no new independent accuracy claim or model selection',
              'seeds':[26,27,28],'epochs':10,'library':base['library'],'source_replay':base['source_replay'],
              'source_weights_freeze_sha256':sha(freeze_path),
              'prior_Cows_training_protocol_sha256':sha(STUDY/'protocol/detector_v1.json'),
              'prior_inference_summary_sha256':sha(prior/'summary.json'),
              'orientations':['original','clockwise90'],
              'image_change':'exact90degree pixel permutation; original source frame remains rendering/counter coordinate system',
              'restore_seam':'on_predict_postprocess_end custom callback before native ByteTrack callback; inverse boxes and Results.orig_img/orig_shape before association',
              'forward_box_transform':'[x1,y1,x2,y2] -> [H-y2,x1,H-y1,x2]',
              'inverse_box_transform':'[u1,v1,u2,v2] -> [v1,H-u2,v2,H-u1]',
              'tracker':'same bytetrack.yaml in original camera coordinates and original native image',
              'required_gates':['explicit coordinate/pixel inverse controls','actual callback ordering and native Results dimensions verified',
                                'all six conditions report source and Toros','original orientation reproduces all prior event and track traces',
                                'weights unchanged before/after run','independent event and inverse-coordinate reconciliation','media full decode and self review'],
              'new_training_updates':0,'candidate_final_or_new_annotated_videos_allowed':False,
              'source_identity_or_independent_count_accuracy':None,'whole_goal_complete':False}
    inputs=ROOT/'input';inputs.mkdir(exist_ok=True)
    shutil.copyfile(freeze_path,inputs/'checkpoint_freeze.json')
    shutil.copyfile(prior/'summary.json',inputs/'prior_inference_summary.json')
    shutil.copyfile(STUDY/'results/counter_source_snapshot.json',inputs/'counter_source_snapshot.json')
    shutil.copyfile(PROJECT/'orientation_validation_20261027/results/tracker_callback_contract.json',inputs/'tracker_callback_contract.json')
    for seed in [26,27,28]:
        folder=inputs/'baseline'/f'seed{seed}';folder.mkdir(parents=True)
        for name in ['source_events.json','source_tracks.csv','source_warmup_tracks.csv','source_summary.json',
                     'Toros_events.json','Toros_tracks.csv','Toros_posttracker_boxes.csv','Toros_summary.json']:
            shutil.copyfile(prior/f'seed{seed}'/name,folder/name)
    protocol_path=ROOT/'protocol/video_rotation_v1.json';assert not protocol_path.exists()
    protocol_path.parent.mkdir(parents=True,exist_ok=True);protocol_path.write_text(json.dumps(protocol,indent=2),encoding='utf-8')
    for p in (ROOT/'tools').glob('*.py'):ast.parse(p.read_text(encoding='utf-8'))
    files=sorted(p for folder in ['input','protocol','tools'] for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    entries=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]
    index=inputs/'staging_manifest.json';assert not index.exists();index.write_text(json.dumps(entries,indent=2),encoding='utf-8')
    archive=ROOT/'staging.tar.gz';assert not archive.exists()
    with tarfile.open(archive,'w:gz') as tar:
        for p in files+[index]:tar.add(p,arcname=p.relative_to(ROOT).as_posix(),recursive=False)
    out=ROOT/'results';out.mkdir(exist_ok=True)
    result={'bytes':archive.stat().st_size,'sha256':sha(archive),'files':len(entries),
            'protocol_sha256':sha(protocol_path),'weights_freeze_sha256':sha(freeze_path),
            'conditions':6,'new_training_or_replay_performed':False}
    (out/'staging_record.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps(result),flush=True)


if __name__=='__main__':main()
