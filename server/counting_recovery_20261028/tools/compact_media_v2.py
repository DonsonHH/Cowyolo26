from pathlib import Path
import hashlib,json,os,subprocess,tarfile
import cv2
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/counting_recovery_20261028')
assert os.environ.get('SLURM_JOB_ID') and __import__('socket').gethostname()!='mu01'
codec='/share/home/renly/miniconda3/envs/pid310_gpu/bin/ffmpeg'
version=subprocess.run([codec,'-version'],capture_output=True,text=True,check=True).stdout.splitlines()[0]
original=json.loads((ROOT/'results/delivery_manifest.json').read_text())
records=[];replacements={}
for row in original:
    if not row['path'].endswith('/transfer.mp4'):continue
    source=ROOT/row['path'];target=source.with_name('transfer_h264.mp4');assert not target.exists()
    command=[codec,'-hide_banner','-nostdin','-n','-i',str(source),'-an','-threads','2','-c:v','libx264','-preset','veryfast','-crf','28','-pix_fmt','yuv420p','-movflags','+faststart',str(target)]
    result=subprocess.run(command,capture_output=True)
    (ROOT/'logs'/f'compact_v2-{source.parent.name}.log').write_bytes(result.stderr);assert result.returncode==0,result.stderr[-500:]
    result=subprocess.run([codec,'-v','error','-nostdin','-xerror','-i',str(target),'-f','null','-'],capture_output=True)
    assert result.returncode==0,result.stderr[-500:]
    cap=cv2.VideoCapture(str(target));assert (cap.get(5),int(cap.get(7)),int(cap.get(3)),int(cap.get(4)))==(25.,1962,1280,720);cap.release()
    record={'source_path':row['path'],'source_sha256':row['sha256'],'path':target.relative_to(ROOT).as_posix(),
            'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'bytes':target.stat().st_size,
            'frames':1962,'fps':25,'duration_s':78.48,'strict_decode':'PASS','new_inference':False}
    records.append(record);replacements[row['path']]=target
assert len(records)==4
mediarecord={'ffmpeg_version':version,'existing_runtime_used':codec,'existing_environment_modified':False,
             'transcoded_previews':records,'native_prediction_traces_or_counts_changed':False}
mr=ROOT/'results/compact_media_record.json';mr.write_text(json.dumps(mediarecord,indent=2))
paths=[replacements.get(r['path'],ROOT/r['path']) for r in original]+[mr]
manifest=[{'path':p.relative_to(ROOT).as_posix(),'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in paths]
mp=ROOT/'results/compact_manifest.json';mp.write_text(json.dumps(manifest,indent=2))
archive=ROOT/'results/compact_delivery.tar.gz';assert not archive.exists()
with tarfile.open(archive,'w:gz') as tf:
    for path in paths:tf.add(path,arcname=path.relative_to(ROOT).as_posix())
    tf.add(mp,arcname='delivery_manifest.json')
r={'manifest_files':len(manifest),'archive_members':len(manifest)+1,'bytes':archive.stat().st_size,
   'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),'manifest_sha256':hashlib.sha256(mp.read_bytes()).hexdigest(),
   'original337MBbundle_and_raw_videos_retained_remote':True,'no_prediction_values_changed':True}
(ROOT/'results/compact_delivery_record.json').write_text(json.dumps(r,indent=2));print(json.dumps(r),flush=True)
