from pathlib import Path
import hashlib, json
ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT.parent
path = PROJECT/'counting_eval_20261026/delivery/counting_evaluation/evidence/zip_member_index.json'
members = json.loads(path.read_text(encoding='utf-8'))
videos = [r for r in members if r['name'].startswith('Videos/') and r['name'].lower().endswith('.mp4')]
GT = [r for r in members if r['name'].startswith('Ground Truth/') and r['name'].lower().endswith(('.csv','.txt','.json','.xml'))]
assert len(videos) == 10 and [r['name'] for r in GT] == ['Ground Truth/gt.txt']
result = {'status':'EXISTING_VERSION1_ARCHIVE_REFERENCE_INVENTORY_RECHECKED',
          'index_path':str(path),'index_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
          'Videos_members':len(videos),'trajectory_annotation_members':[r['name'] for r in GT],
          'paired_GT_video':'Ground Truth/Toros.mp4',
          'scope':'Alreadyobtainedversion1 ZIPindex, not aclaimaboutallcurrentinternetresources.',
          'remaining_videos_not_assigned_new_independent_passage_truth':True,
          'no_new_download_inference_or_labels':True}
target = ROOT/'results/existing_public_annotation_inventory.json'
assert not target.exists()
target.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
