from pathlib import Path
import os,json,hashlib,shutil,subprocess,tarfile,cv2
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/phase2');OUT=ROOT/'results/delivery';OUT.mkdir(exist_ok=True)
for name in ('evidence','annotations','media','code'): (OUT/name).mkdir(exist_ok=True)
files={
 'results/evaluation/metrics.json':'evidence/metrics.json',
 'results/evaluation/external_event_metrics.csv':'evidence/external_event_metrics.csv',
 'results/author_gt_audit/summary.json':'evidence/author_gt_summary.json',
 'results/author_gt_audit/reference_events.csv':'annotations/publisher_derived_reference_events.csv',
 'results/mendeley_source/audit.json':'evidence/external_dataset_audit.json',
 'results/external_counting/all_summaries.json':'evidence/external_inference_summaries.json',
 'results/author_gt_audit/author_gt_overlay.jpg':'media/author_gt_overlay.jpg',
 'results/reference_review/six_reference_passages.jpg':'media/six_reference_passages.jpg',
 'catalog/mendeley_endpoint_0.txt':'evidence/publisher_file_metadata.json',
 'catalog/mendeley_zip_members.json':'evidence/zip_member_index.json',
 'data/mendeley_counting/extracted/Ground Truth/gt.txt':'annotations/publisher_gt_original.txt',
 'results/slurm_status_before_package.txt':'evidence/slurm_status_before_package.txt'
}
for src,dest in files.items():shutil.copy2(ROOT/src,OUT/dest)
for p in (ROOT/'annotations').glob('*'):
 if p.is_file():shutil.copy2(p,OUT/'annotations'/p.name)
for name in ['zone_counter.py','test_zone_counter.py','event_metrics.py','test_event_metrics.py','author_gt_audit.py','external_counting_inference.py','score_counting.py']:
 shutil.copy2(ROOT/'tools'/name,OUT/'code'/name)
specs=[('generic','Toros','reverse_generic'),('pilot','Toros','reverse_pilot'),('generic','Toros6','forward_generic'),('pilot','Toros6','forward_pilot')];readability=[]
for model,video,label in specs:
 src=ROOT/'results/external_counting'/model/video/'annotated.mp4';dest=OUT/'media'/(label+'.mp4')
 if dest.exists():
  # Preserve incomplete export attempts. Never overwrite source videos or evaluation artifacts.
  backup=dest.with_name(dest.name+'.failed_openh264')
  if backup.exists():raise FileExistsError(backup)
  dest.rename(backup)
 c=cv2.VideoCapture(str(src));fps=c.get(5);w=int(c.get(3));h=int(c.get(4));height=round(h*640/w/2)*2
 writer=cv2.VideoWriter(str(dest),cv2.VideoWriter_fourcc(*'mp4v'),fps,(640,height))
 if not writer.isOpened():raise ValueError('MPEG4 preview writer unavailable')
 import csv
 events=list(csv.DictReader((ROOT/'results/external_counting'/model/video/'events.csv').open()));frame=0
 while True:
  ok,im=c.read()
  if not ok:break
  im=cv2.resize(im,(640,height));completed=[e for e in events if int(e['frame'])<=frame]
  a=sum(e['direction']=='A->B' for e in completed);b=len(completed)-a
  cv2.rectangle(im,(0,height-30),(640,height),(0,0,0),-1)
  cv2.putText(im,f'{model} | A->B {a} | B->A {b} | {frame/fps:.2f}s',(8,height-9),cv2.FONT_HERSHEY_SIMPLEX,.58,(0,255,0),1,cv2.LINE_AA)
  writer.write(im);frame+=1
 c.release();writer.release()
 c=cv2.VideoCapture(str(dest));n=int(c.get(7));fps=c.get(5);ok,_=c.read();c.set(cv2.CAP_PROP_POS_FRAMES,n-1);last,_=c.read();c.release()
 if not(ok and last and n>0):raise ValueError('Encoded preview unreadable')
 readability.append({'file':dest.name,'frame_count':n,'fps':fps,'first_frame_decodes':ok,'last_frame_decodes':last,'format':'MPEG4 part2 transfer preview; H264 conversion will be performed locally after checksum verification','source':str(src)})
 shutil.copy2(ROOT/'results/external_counting'/model/video/'contact.jpg',OUT/'media'/(label+'_contact.jpg'))
(OUT/'evidence/preview_video_checks.json').write_text(json.dumps({'job_id':os.environ['SLURM_JOB_ID'],'videos':readability},indent=2))
manifest=[{'path':str(p.relative_to(OUT)),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in sorted(OUT.rglob('*')) if p.is_file() and not p.name.endswith('.failed_openh264')]
(OUT/'evidence/delivery_manifest.json').write_text(json.dumps(manifest,indent=2))
bundle=ROOT/'results/counting_evaluation_delivery.tar.gz'
with tarfile.open(bundle,'w:gz') as tf:tf.add(OUT,arcname='counting_evaluation',filter=lambda ti: None if ti.name.endswith('.failed_openh264') else ti)
summary={'job_id':os.environ['SLURM_JOB_ID'],'bundle_path':str(bundle),'bytes':bundle.stat().st_size,'sha256':hashlib.sha256(bundle.read_bytes()).hexdigest(),'file_count':len(manifest)+1}
(ROOT/'results/bundle_record.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary),flush=True)
