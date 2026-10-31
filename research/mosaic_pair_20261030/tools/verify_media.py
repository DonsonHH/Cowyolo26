from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,gzip,re,xml.etree.ElementTree as ET,subprocess
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];MEDIA=ROOT/'delivery/results/media';OUT=ROOT/'delivery/results/evaluation_v2'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def gz(p):return json.loads(gzip.decompress(Path(p).read_bytes()))
for r in load(MEDIA/'manifest.json'):
    f=MEDIA/r['file'];assert f.stat().st_size==r['bytes'] and sha(f)==r['sha256']
data=load(MEDIA/'media_values.json');s=load(OUT/'summary.json');xml=ET.parse(MEDIA/'all_six_mosaic_controls.svg');ns={'s':'http://www.w3.org/2000/svg'}
def map_ticks(axis,kind):
    ticks=[]
    for g in axis.findall('.//s:g',ns):
        if not g.attrib.get('id','').startswith(kind+'tick_'):continue
        text=g.find('.//s:text',ns);mark=g.find('.//s:use',ns)
        if text is None or mark is None:continue
        label=''.join(text.itertext()).strip().replace('\u2212','-')
        if kind=='x' and label in ['seed26','seed27','seed28']:value=float({'seed26':0,'seed27':1,'seed28':2}[label])
        else:
            try:value=float(label)
            except ValueError:continue
        ticks.append((value,float(mark.attrib[kind])))
    assert len(ticks)>1;a,b=next((a,b) for a in ticks for b in ticks if a[0]!=b[0]);scale=(b[1]-a[1])/(b[0]-a[0]);offset=a[1]-scale*a[0]
    return scale,offset
count=0;maxerror=0.
for panel in range(4):
    axis=xml.find('.//s:g[@id="axes_'+str(panel+1)+'"]',ns);sy,oy=map_ticks(axis,'y');sx,ox=map_ticks(axis,'x');paths=[]
    for g in axis:
        if g.attrib.get('id','').startswith('patch_'):
            p=g.find('s:path',ns)
            if p is not None and 'clip-path' in p.attrib:paths.append(p)
    rows=[r for r in data['bars'] if r['panel']==panel];assert len(rows)==len(paths)==(12 if panel==3 else 6)
    for row,path in zip(rows,paths):
        name=row['arm']+'_seed'+str(row['seed'])
        if panel<2:value=next(r[row['kind']] for r in s['validation_metrics'] if r['condition']==name)
        else:
            metric=next(r for r in s['video_metrics'] if r['condition']==name and r['scene']==('original' if panel==2 else 'toros') and r['counter']=='handoff_events' and r['stride']==(5 if panel==2 else row['stride']))
            value=metric['down'] if panel==2 else metric['formal_event_metrics']['TP']
        assert row['value']==value
        points=np.array([float(v) for v in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?',path.attrib['d'])]).reshape(-1,2)
        error=max(abs(np.ptp(points[:,1])/abs(sy)-value),abs(points[:,0].min()-(row['x']*sx+ox)))
        assert error<2e-4;maxerror=max(maxerror,error);count+=1
movie=MEDIA/data['movie_file'];assert sha(movie)==data['movie_sha256']
probe=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-count_frames','-show_entries','stream=width,height,nb_read_frames,r_frame_rate','-of','json',str(movie)],text=True,encoding='utf-8',capture_output=True,check=True)
stream=json.loads(probe.stdout)['streams'][0];assert [stream[k] for k in ['width','height','nb_read_frames','r_frame_rate']]==[1152,560,'1962','25/1']
strict=subprocess.run(['ffmpeg','-v','error','-err_detect','explode','-i',str(movie),'-f','null','-'],capture_output=True,text=True,encoding='utf-8');assert strict.returncode==0 and not strict.stderr.strip(),strict.stderr
dest=ROOT/'results/decoded_anchors_v2';dest.mkdir(exist_ok=False)
frames=[r['video_index0'] for r in data['previews']];expression='+'.join('eq(n\\,'+str(i)+')' for i in frames)
# FFmpeg filter escaping is one literal backslash, passed as an argv element.
expression=expression.replace('\\\\','\\')
subprocess.run(['ffmpeg','-v','error','-i',str(movie),'-vf','select='+expression,'-fps_mode','passthrough','-frames:v','4',str(dest/'anchor_%02d.png')],check=True,capture_output=True)
checks=[];panelcount=0
for index,row in enumerate(data['previews'],1):
    expected=MEDIA/row['file'];assert sha(expected)==row['sha256']
    actual=dest/('anchor_'+str(index).zfill(2)+'.png')
    a=np.array(Image.open(expected).convert('RGB'),dtype=np.int16);b=np.array(Image.open(actual).convert('RGB'),dtype=np.int16)
    assert a.shape==b.shape==(560,1152,3)
    difference=np.abs(a-b);mean=float(difference.mean());p99=float(np.percentile(difference,99));assert mean<7 and p99<35,(mean,p99)
    for p in row['panels']:
        trace=gz(OUT/p['condition']/'original/stride5_counter_trace.json.gz');events=[r for r in trace['handoff_events'] if 8912<=r['frame0']<=row['source_frame0']]
        assert p['down']==sum(r['direction']=='A->B' for r in events) and p['up']==sum(r['direction']=='B->A' for r in events)
        assert p['sample_frame0']==row['source_frame0']-row['source_frame0']%5
        assert p['post_tracker_boxes']==sum(r['frame0']==p['sample_frame0'] for r in trace['post_tracker']);panelcount+=1
    checks.append({'source_frame0':row['source_frame0'],'actual_decoded_file':str(actual.resolve()),'mean_absolute_RGB_error':mean,'P99_absolute_RGB_error':p99})
assert count==30 and panelcount==8 and len(checks)==4
result={'status':'30_SVG_BARS1962_STRICT_DECODED_FRAMES_AND8_SOURCE_ANCHOR_COUNT_PANELS_VERIFIED','created_UTC':datetime.now(timezone.utc).isoformat(),
    'SVG_bars':30,'maximum_bar_geometry_error':maxerror,'strict_decoded_video_frames':1962,'actual_video_anchors':4,'source_count_panels_checked':8,
    'encoded_anchor_checks':checks,'expected_figures_to_actually_view':5,'expected_panels_to_actually_view':12,
    'new_model_forwards':0,'actual_board_actions':0,'whole_goal_complete':False}
target=ROOT/'results/media_verification.json';assert not target.exists();target.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8');print(json.dumps(result))
