from pathlib import Path
import json,hashlib,re,tarfile,csv,ast

ROOT=Path(__file__).resolve().parent.parent
def sha(p):
 h=hashlib.sha256()
 with p.open('rb') as f:
  for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
 return h.hexdigest()

expected_bundle='bb7c4f1c8f0220a17f2d73d5e32e07df028af73e0c2634557c691be144052feb'
bundle=ROOT/'server_results/idcoo_audit_delivery.tar.gz'
errors=[]
if not bundle.exists() or sha(bundle)!=expected_bundle:raise SystemExit('Evidence bundle not fully transferred or checksum mismatch; do not mark complete')
dest=ROOT/'server_results/delivery';dest.mkdir(exist_ok=True)
with tarfile.open(bundle,'r:gz') as tf:
 for m in tf.getmembers():
  if not (m.isfile() or m.isdir()):raise ValueError('Unexpected archive link/type')
  target=(dest/m.name).resolve()
  if not target.is_relative_to(dest.resolve()):raise ValueError('Unsafe archive member')
 tf.extractall(dest,filter='data')

model=ROOT/'models/yolo26n_opencows_5epoch_dev.pt'
model_expected='9b38f145a01585908fa9f1c44f3b00e4fb43f3cdf7f1fe2c8c387252ce47e81b'
if not model.exists() or sha(model)!=model_expected:errors.append('Trained weight checksum')
evidence=dest/'evidence'
req=['media_audit.json','cleaning_summary.json','training_record.json','multicam_finetuned_summary.json','cows21_finetuned_summaries.json','slurm_jobs_final.txt','server_inventory.json']
for n in req:
 if not (evidence/n).is_file() or (evidence/n).stat().st_size==0:errors.append('Missing evidence '+n)
audit=json.loads((ROOT/'local_opencows/full_audit.json').read_text())
if audit['unreadable_or_crc_errors'] or audit['missing_yolo'] or audit['orphan_yolo']:errors.append('Raw archive integrity/pairing')
media=json.loads((evidence/'media_audit.json').read_text())
if len(media['videos'])!=3 or not all(x['open'] and x['decode_count_matches_header'] for x in media['videos']):errors.append('Downloaded media readability')
training=json.loads((evidence/'training_record.json').read_text())
if training['best_sha256']!=model_expected or training['epochs_requested']!=5:errors.append('Training record mismatch')
mc=json.loads((evidence/'multicam_finetuned_summary.json').read_text())
if mc['sampled_frames']!=2802 or mc['model_sha256']!=model_expected:errors.append('Replay evidence mismatch')
jobs=list(csv.DictReader((evidence/'slurm_jobs_final.txt').open(),delimiter='|'))
required_jobs=['129649','129655','129657','129658','129659','129660','129661','129662','129663','129664']
for jid in required_jobs:
 row=next((r for r in jobs if r['JobID']==jid),None)
 if not row or row['State']!='COMPLETED' or row['ExitCode']!='0:0':errors.append('Required job not successful '+jid)
state=(ROOT/'remote_final_state.txt').read_text()
if '129666|idcoo-collect-evidence|COMPLETED|0:0' not in state:errors.append('Collection completion')
exported=json.loads((ROOT/'server_results/exported_video_readability.json').read_text())
if len(exported['videos'])!=2 or not all(v['first_frame_decodes'] and v['last_frame_decodes'] for v in exported['videos']):errors.append('Exported video readability')
state2=(ROOT/'remote_final_state_after_media.txt').read_text()
if not any(line.startswith('129667|') and '|COMPLETED|0:0|' in line for line in state2.splitlines()) or 'isolated_task_proxy_listener_active": false' not in state2:errors.append('Final media job/proxy state')
documents=[]
for p in sorted(ROOT.glob('*.md')):
 s=p.read_text(encoding='utf8')
 if '\ufffd' in s:errors.append('Replacement glyph in '+p.name)
 if len(re.findall(r'^```',s,re.M))%2:errors.append('Unclosed code fence in '+p.name)
 width=None
 for i,line in enumerate(s.splitlines(),1):
  if line.startswith('|'):
   n=line.count('|')
   if width is not None and n!=width:errors.append(f'Table width {p.name}:{i}')
   width=n
  else:width=None
 for u in re.findall(r'\]\((<[^>]+>|[^\s)]+)\)',s):
  u=u.strip('<>')
  if re.match(r'^[A-Za-z]:/',u) and not Path(u).exists() and Path(u)!=(ROOT/'Final_QA.json'):errors.append('Missing local link '+u)
 documents.append({'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)})
for p in (ROOT/'tools').glob('*.py'):
 try:ast.parse(p.read_text(encoding='utf8'))
 except SyntaxError as e:errors.append('Python syntax '+p.name+':'+str(e))
for p in dest.rglob('*'):
 if p.is_file() and not p.stat().st_size:errors.append('Empty delivered artifact '+str(p))
out={'status':'PASS' if not errors else 'FAIL','scope':'data audit, downloaded sample integrity, terminal Slurm jobs, weights, replay artifacts, document/code structure; not an independent accuracy or FPGA deployment certificate','errors':errors,'raw_archive_sha256':audit['archive_sha256'],'bundle_sha256':sha(bundle),'model_sha256':sha(model),'required_successful_job_ids':required_jobs+['129666','129667'],'exported_video_readability':exported,'recorded_failed_attempts':['129650 dependency missing, repaired','129665 compute-node accounting lookup, repaired'],'downloaded_video_samples':media['videos'],'source_video_decode_warning':'H.264 macroblock warning retained; matching decoded count is not a bitstream corruption guarantee','counting_status':'development predictions, independent event ground truth not yet completed','identity_model_status':'not trained in this phase','pynq_board_status':'not deployed in this phase','documents':documents}
(ROOT/'Final_QA.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf8')
print(json.dumps({'status':out['status'],'errors':errors,'bundle_sha256':out['bundle_sha256'],'model_sha256':out['model_sha256'],'videos':len(media['videos']),'documents':len(documents),'jobs':required_jobs+['129666']},ensure_ascii=False,indent=2))
if errors:raise SystemExit(1)
