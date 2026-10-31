from pathlib import Path
from datetime import datetime,timezone
from PIL import Image
import json,hashlib,tarfile,re,subprocess,xml.etree.ElementTree as ET
import numpy as np
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'media_delivery'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
transfer=load(ROOT/'evidence/media_transfer.json');archive=ROOT/'media_delivery.tar.gz'
assert archive.stat().st_size==transfer['bytes'] and sha(archive)==transfer['sha256']
OUT.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    members=tar.getmembers();assert len(members)==transfer['members']
    for member in members:
        assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
        file=(OUT/member.name).resolve();assert file.is_relative_to(OUT.resolve()) and not file.exists()
        file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(tar.extractfile(member).read())
for row in load(OUT/'results/media/manifest.json'):
    file=OUT/row['relative_file'];assert file.stat().st_size==row['bytes'] and sha(file)==row['sha256']
for relative in ['protocol/media_render_v1.json','tools/render_media.py','tools/media.slurm']:
    assert sha(OUT/relative)==sha(ROOT/relative)
s=load(ROOT/'delivery/results/roi/summary.json');data=load(OUT/'results/media/plot_data.json');ns={'s':'http://www.w3.org/2000/svg'}
xml=ET.parse(OUT/'results/media/full_vs_roi_all_models.svg');bars=0;maximum=0.
for panel in range(9):
    axis=xml.find('.//s:g[@id="axes_'+str(panel+1)+'"]',ns);assert axis is not None
    paths=[]
    for element in axis:
        if element.attrib.get('id','').startswith('patch_'):
            path=element.find('s:path',ns)
            if path is not None and 'clip-path' in path.attrib:paths.append(path)
    rows=[r for r in data['bars'] if r['panel']==panel];assert len(paths)==len(rows)==8
    for path,row in zip(paths,rows):
        paired=next(x for x in s['paired_full_vs_roi'] if x['scene']==row['scene'] and x['condition']==row['model']+'_s'+str(row['size']) and x['sample_stride']==row['stride'] and x['counter']=='handoff_events')
        value=paired[row['mode']+'_down'] if row['scene']=='original' else paired[row['mode']+'_TP_FP_FN'][0]
        assert row['value']==value
        clipid=re.search(r'#([^\)]+)',path.attrib['clip-path']).group(1);rect=xml.find('.//s:clipPath[@id="'+clipid+'"]/s:rect',ns)
        values=[float(x) for x in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',path.attrib['d'])]
        points=np.asarray(values).reshape(-1,2);assert len(points) in [4,5]
        height=np.ptp(points[:,1])/float(rect.attrib['height'])*row['ymax']
        xpos=(points[0,0]-float(rect.attrib['x']))/float(rect.attrib['width'])*4.2-.6
        delta=max(abs(height-value),abs(xpos-row['bar_x']));assert delta<2e-5;maximum=max(maximum,delta);bars+=1
meta=load(OUT/'results/media/media_metadata.json');gate=load(ROOT/'protocol/media_render_v1.json')
assert meta['primary_model']==gate['primary_model']=='seed26' and meta['scope_frame0_inclusive']==[8912,10873]
assert meta['source_decode_frames']==10874 and meta['detection_sampling_Hz']==5 and meta['fps']==25 and meta['dimensions']==[1280,1120]
assert meta['science_bar_count']==bars==72 and len(meta['input_sheets'])==8 and len(meta['preview_frames'])==4
pixels=0
for row in meta['input_sheets']:
    file=OUT/row['path'];assert sha(file)==row['sha256']
    with Image.open(file) as image:rgb=np.asarray(image.convert('RGB'))
    assert rgb.shape==(900,1600,3) and row['actual_inputs_rescaled_for_display'] is False
    for i,size in enumerate([192,256,320]):
        path=ROOT/'delivery/results/roi/pixel_controls'/(row['scene']+'_f'+str(row['source_frame0'])+'_s'+str(size)+'_NN.npz')
        with np.load(path) as archive:expected=np.rint(archive['actual_input'].transpose(1,2,0)*255).astype(np.uint8)
        x=i*533+(533-size)//2;y=560+(320-size)//2;assert np.array_equal(rgb[y:y+size,x:x+size],expected);pixels+=1
movie=OUT/meta['movie']['path'];assert sha(movie)==meta['movie']['sha256'] and meta['movie']['frames']==1962
probe=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,avg_frame_rate,nb_read_frames','-of','json',str(movie)],capture_output=True,text=True,check=True)
stream=json.loads(probe.stdout)['streams'][0];assert [stream['width'],stream['height']]==[1280,1120] and stream['avg_frame_rate']=='25/1' and int(stream['nb_read_frames'])==1962
decoded=subprocess.run(['ffmpeg','-v','error','-xerror','-err_detect','explode','-i',str(movie),'-f','null','-'],stdout=subprocess.DEVNULL,stderr=subprocess.PIPE,check=True);assert not decoded.stderr
frames=ROOT/'results/decoded_video_anchors';frames.mkdir(exist_ok=False);checks=[]
for row in meta['preview_frames']:
    index=row['source_frame0']-8912;assert index==row['video_frame_index0'];file=frames/('source_f'+str(row['source_frame0'])+'.png')
    subprocess.run(['ffmpeg','-v','error','-i',str(movie),'-vf','select=eq(n\\,'+str(index)+')','-frames:v','1','-fps_mode','vfr',str(file)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    preview=OUT/row['path'];assert sha(preview)==row['sha256']
    with Image.open(file) as image:a=np.asarray(image.convert('RGB'),dtype=np.int16)
    with Image.open(preview) as image:b=np.asarray(image.convert('RGB'),dtype=np.int16)
    assert a.shape==b.shape==(1120,1280,3);delta=np.abs(a-b);mean=float(delta.mean());p95=float(np.quantile(delta,.95))
    assert mean<gate['movie_vs_PNG_anchor_mean_RGB_delta_less_than'] and p95<gate['movie_vs_PNG_anchor_p95_RGB_delta_less_than']
    for panel in row['panels']:
        summary=next(x for x in s['video_metrics'] if x['scene']=='original' and x['condition']=='seed26_s'+str(panel['size']) and x['counter']=='handoff_events') if panel['mode']=='crop' else next(x for x in load(ROOT.parent/'lowres_baseline_20261029/delivery/results/baseline/video_metrics.json') if x['scene']=='original' and x['condition']=='seed26_s'+str(panel['size']) and x['counter']=='handoff_events')
        assert panel['down']==sum(e['direction']=='A->B' and e['frame0']<=row['source_frame0'] for e in summary['events'])
        assert panel['up']==sum(e['direction']=='B->A' and e['frame0']<=row['source_frame0'] for e in summary['events']) and panel['held_frame0']==row['source_frame0']-row['source_frame0']%5
    checks.append({'source_frame0':row['source_frame0'],'video_frame_index0':index,'path':str(file.resolve()),'sha256':sha(file),
                   'mean_RGB_delta':mean,'p95_RGB_delta':p95,'panels':6})
record={'status':'72_SVG_BARS24_INPUT_PIXEL_PANELS1962_VIDEO_FRAMES_AND4_ANCHORS_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),
        'archive_sha256':sha(ROOT/'media_delivery.tar.gz'),'archive_bytes':transfer['bytes'],'archive_members':len(members),
        'SVG_bars':bars,'maximum_SVG_bar_data_error':maximum,'input_tensor_panels_exact':pixels,'strict_decoded_video_frames':1962,
        'video_file':str(movie.resolve()),'video_sha256':sha(movie),'actual_decoded_video_anchor_checks':checks,
        'scientific_figure_panels':9,'source_NN_sheet_panels':40,'movie_anchor_panels':24,
        'expected_visual_figure_count':13,'expected_visual_panel_count':73,'manual_visual_review_separate':True,
        'new_network_forwards':0,'new_training_updates':0,'PYNQ5FPS_proven':False,'whole_goal_complete':False}
file=ROOT/'results/media_verification.json';assert not file.exists();file.write_text(json.dumps(record,indent=2)+'\n')
print(json.dumps({k:v for k,v in record.items() if k not in ['actual_decoded_video_anchor_checks']}))
