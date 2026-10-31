from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,tarfile,re,subprocess,xml.etree.ElementTree as ET
from PIL import Image
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
meta=load(ROOT/'evidence/media_transfer.json');archive=ROOT/'media_delivery.tar.gz'
assert archive.stat().st_size==meta['bytes'] and sha(archive)==meta['sha256']
out=ROOT/'media_delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    members=tar.getmembers();assert len(members)==meta['members']
    for entry in members:
        assert entry.isfile() and not entry.name.startswith('/') and '..' not in Path(entry.name).parts
        file=(out/entry.name).resolve();assert file.is_relative_to(out.resolve()) and not file.exists()
        file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(tar.extractfile(entry).read())
for row in load(out/'results/media/manifest.json'):
    f=out/row['relative_file'];assert f.stat().st_size==row['bytes'] and sha(f)==row['sha256']
data=load(out/'results/media/plot_data.json');summary=load(ROOT/'delivery/results/baseline/summary.json');namespace={'s':'http://www.w3.org/2000/svg'}
xml=ET.parse(out/'results/media/lowres_baseline_counts.svg');max_delta=0.;bars=0
for panel in range(4):
    axis=xml.find('.//s:g[@id="axes_'+str(panel+1)+'"]',namespace);paths=[]
    for element in axis:
        if element.attrib.get('id','').startswith('patch_'):
            path=element.find('s:path',namespace)
            if path is not None and 'clip-path' in path.attrib:paths.append(path)
    expected=[r for r in data['bars'] if r['panel']==panel];assert len(paths)==len(expected)==12
    for path,r in zip(paths,expected):
        cname=r['model']+'_s'+str(r['size'])
        if panel==0:value=next(x for x in summary['validation_metrics'] if x['condition']==cname)['matched']
        else:
            scene='original' if panel==1 else 'toros';stride=5 if panel==1 else 6 if panel==2 else 1
            record=next(x for x in summary['video_metrics'] if x['condition']==cname and x['scene']==scene and x['sample_stride']==stride and x['counter']=='handoff_events')
            value=record['down'] if panel==1 else record['formal_event_metrics']['TP']
        assert value==r['value']
        clipid=re.search(r'#([^\)]+)',path.attrib['clip-path']).group(1);rect=xml.find('.//s:clipPath[@id="'+clipid+'"]/s:rect',namespace)
        values=[float(v) for v in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',path.attrib['d'])]
        pts=np.asarray(values).reshape(-1,2);assert len(pts) in [4,5]
        actual_height=(max(pts[:,1])-min(pts[:,1]))/float(rect.attrib['height'])*r['ymax']
        actual_x=(pts[0,0]-float(rect.attrib['x']))/float(rect.attrib['width'])*4.2-.6
        error=max(abs(actual_height-value),abs(actual_x-r['bar_x']));assert error<2e-5
        max_delta=max(max_delta,error);bars+=1
metadata=load(out/'results/media/media_metadata.json');assert metadata['export_interval_inclusive']==[8912,10873] and metadata['source_decode_frames']==10874
decoded=[];frame_checks=[];framefolder=ROOT/'results/video_frame_verification';framefolder.mkdir(exist_ok=False)
for row in metadata['movies']:
    file=out/row['path'];assert sha(file)==row['sha256'];assert row['frames']==1962 and row['fps']==25 and row['dimensions']==[1280,720]
    probe=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,avg_frame_rate,nb_read_frames','-of','json',str(file)],capture_output=True,text=True,check=True)
    stream=json.loads(probe.stdout)['streams'][0];assert [stream['width'],stream['height']]==[1280,720] and stream['avg_frame_rate']=='25/1' and int(stream['nb_read_frames'])==1962
    process=subprocess.run(['ffmpeg','-v','error','-xerror','-err_detect','explode','-i',str(file),'-f','null','-'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=True)
    assert not process.stderr
    for sample in metadata['preview_frames'][str(row['size'])]:
        frame0=sample['source_frame0'];index=frame0-8912;output=framefolder/('s'+str(row['size'])+'_f'+str(frame0)+'.png')
        subprocess.run(['ffmpeg','-v','error','-i',str(file),'-vf','select=eq(n\\,'+str(index)+')','-frames:v','1','-fps_mode','vfr',str(output)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
        prior=out/sample['path'];assert sha(prior)==sample['sha256']
        with Image.open(prior) as image:a=np.asarray(image.convert('RGB'),dtype=np.int16)
        with Image.open(output) as image:image.load();b=np.asarray(image.convert('RGB'),dtype=np.int16)
        assert a.shape==b.shape==(720,1280,3)
        delta=np.abs(a-b);mean=float(delta.mean());p95=float(np.quantile(delta,.95));assert mean<6 and p95<20
        frame_checks.append({'source_frame0':frame0,'video_frame_index0':index,'size':row['size'],'decoded_frame':str(output.resolve()),'sha256':sha(output),
            'mean_RGB_difference_vs_lossy_preview':mean,'p95_RGB_difference_vs_lossy_preview':p95,'panels':4})
    decoded.append({'file':str(file.resolve()),'sha256':sha(file),'strict_decode_frames':1962,'size':row['size'],'width':1280,'height':720,'rate':'25/1'})
report={'status':'48_SVG_BARS_THREE_FULL_DECODE_MOVIES_AND12_FRAME_ALIGNMENT_CHECKS_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),
'archive_sha256':sha(archive),'archive_bytes':archive.stat().st_size,'members':len(members),'SVG_bar_segments':bars,'maximum_bar_data_error':max_delta,
'full_strict_decoded_video_frames':1962*3,'movies':decoded,'actual_video_frame_checks':frame_checks,'preview_image_panels':48,
'science_figure_panels':4,'new_model_forwards':0,'board_FPS_proven':False}
file=ROOT/'results/media_verification.json';assert not file.exists();file.write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps({k:v for k,v in report.items() if k not in ['movies','actual_video_frame_checks']}))
