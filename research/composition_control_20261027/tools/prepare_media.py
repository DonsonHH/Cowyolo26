"""All six paired-condition previews, exact same source interval and public metadata."""
from pathlib import Path
import concurrent.futures,hashlib,json,shutil,subprocess
from PIL import Image,ImageDraw
ROOT=Path(__file__).resolve().parents[1];BASE=ROOT.parent
SOURCE=ROOT/'delivery/results/inference';OUT=ROOT/'previews'
FFMPEG=shutil.which('ffmpeg');FFPROBE=shutil.which('ffprobe')
assert FFMPEG and FFPROBE


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(command,log):
    r=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE);Path(log).write_bytes(r.stderr)
    assert r.returncode==0,(command,r.stderr.decode(errors='replace')[-2000:]);return r.stdout


def prepare(name):
    source=SOURCE/name/'source_transfer.mp4';media=[]
    for extension in ['mp4','webm']:
        dest=OUT/f'composition_{name}_f8912-10873.{extension}';assert not dest.exists()
        codec=(['-c:v','libx264','-preset','veryfast','-crf','25','-pix_fmt','yuv420p','-movflags','+faststart'] if extension=='mp4'
               else ['-c:v','libvpx-vp9','-deadline','realtime','-cpu-used','7','-crf','36','-b:v','0','-row-mt','1','-pix_fmt','yuv420p'])
        run([FFMPEG,'-hide_banner','-nostdin','-n','-i',str(source),'-an','-threads','2',*codec,str(dest)],ROOT/'results'/f'{name}_{extension}_encode.log')
        p=json.loads(run([FFPROBE,'-v','error','-count_frames','-show_entries','stream=codec_name,width,height,avg_frame_rate,nb_read_frames:format=duration','-of','json',str(dest)],ROOT/'results'/f'{name}_{extension}_probe.log'))
        stream=p['streams'][0];assert (stream['width'],stream['height'],stream['nb_read_frames'],stream['avg_frame_rate'])==(1280,720,'1962','25/1')
        assert abs(float(p['format']['duration'])-78.48)<.01
        run([FFMPEG,'-v','error','-nostdin','-xerror','-i',str(dest),'-f','null','-'],ROOT/'results'/f'{name}_{extension}_decode.log')
        target=BASE/'phase3_diagnosis_20261026/inputs'/dest.name;assert not target.exists();shutil.copyfile(dest,target)
        assert sha(dest)==sha(target)
        media.append({'condition':name,'format':extension,'path':str(dest),'file':dest.name,'bytes':dest.stat().st_size,'sha256':sha(dest),
                      'frames':1962,'fps':25,'duration_s':78.48,'strict_full_decode':'PASS'})
    return media


def main():
    OUT.mkdir(exist_ok=True)
    frozen=json.loads((ROOT/'delivery/results/all_models_frozen.json').read_text(encoding='utf-8'))
    inference=json.loads((SOURCE/'summary.json').read_text(encoding='utf-8'))
    names=[c['name'] for c in inference['conditions']];assert len(names)==6
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        media=[r for group in pool.map(prepare,names) for r in group]
    rows=[]
    for condition in inference['conditions']:
        name=condition['name'];training=next(r for r in frozen['conditions'] if r['condition']['name']==name)
        src=next(r for r in condition['scenes'] if r['scene']=='source')
        rows.append({'name':name,'arm':condition['arm'],'seed':condition['seed'],'source_down':src['A_to_B'],'source_up':src['B_to_A'],
                     'AP50':training['last_epoch_validation']['metrics/mAP50(B)'],'AP50_95':training['last_epoch_validation']['metrics/mAP50-95(B)'],
                     'Toros_TP':condition['Toros_event_metrics']['TP'],'Toros_FP':condition['Toros_event_metrics']['FP'],'Toros_FN':condition['Toros_event_metrics']['FN'],
                     'checkpoint_sha256':condition['checkpoint_sha256'],'optimizer_steps':training['optimizer_steps'],
                     'stem':f'composition_{name}_f8912-10873'})
    data={'status':'SIX_CONTROLLED_CONDITIONS_WITH_VERIFIED_MEDIA','conditions':rows,'media':media,
          'paired_controls':frozen['paired_controls'],'source_frame_range':[8912,10873],'source_fps':25,'default_seed':26,
          'box_extent':'Torso, same public-label convention; Toros box extent mismatch retained','source_independent_accuracy':None}
    (BASE/'phase3_diagnosis_20261026/annotation_workbench/composition_preview_data.json').write_text(json.dumps(data,indent=2),encoding='utf-8')
    sheet=Image.new('RGB',(3*640,2*410),(20,26,30));draw=ImageDraw.Draw(sheet)
    for i,seed in enumerate([26,27,28]):
        for j,arm in enumerate(['mixed','real_repeated']):
            with Image.open(SOURCE/f'{arm}_seed{seed}'/'source_f9420.jpg') as im:
                sheet.paste(im.convert('RGB').resize((640,360)),(i*640,j*410+40))
            draw.text((i*640+12,j*410+12),f'{arm} seed{seed}, source9420',fill='white')
    sheet.save(OUT/'paired_source9420.jpg',quality=94)
    (ROOT/'results/media_verification.json').write_text(json.dumps({'status':'TWELVE_MEDIA_FULL_DECODE_PASS','media':media,'conditions':rows},indent=2),encoding='utf-8')
    print(json.dumps({'status':'TWELVE_MEDIA_FULL_DECODE_PASS','conditions':rows}),flush=True)


if __name__=='__main__':main()
