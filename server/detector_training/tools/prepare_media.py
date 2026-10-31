"""Compact browser derivatives and checked copies, without touching previous models."""
from pathlib import Path
import concurrent.futures,hashlib,json,shutil,subprocess
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent
SOURCE=ROOT/'delivery/results/inference'
OUT=ROOT/'previews'
FFMPEG=shutil.which('ffmpeg');FFPROBE=shutil.which('ffprobe')
assert FFMPEG and FFPROBE


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(args,log):
    result=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    Path(log).write_bytes(result.stderr)
    assert result.returncode==0,(args,result.stderr.decode(errors='replace')[-2000:])
    return result.stdout


def one(seed):
    name=f'epoch20_seed{seed}';source=SOURCE/name/'source_transfer.mp4'
    assert source.is_file()
    media=[]
    for extension in ['mp4','webm']:
        dest=OUT/f'{name}_f8912-10873.{extension}';assert not dest.exists()
        encoding=(['-c:v','libx264','-preset','veryfast','-crf','25','-pix_fmt','yuv420p','-movflags','+faststart'] if extension=='mp4'
                  else ['-c:v','libvpx-vp9','-deadline','realtime','-cpu-used','7','-crf','36','-b:v','0','-row-mt','1','-pix_fmt','yuv420p'])
        run([FFMPEG,'-hide_banner','-nostdin','-n','-i',str(source),'-an','-threads','2',*encoding,str(dest)],ROOT/'results'/f'{name}_{extension}_encode.log')
        info=json.loads(run([FFPROBE,'-v','error','-count_frames','-show_entries','stream=width,height,avg_frame_rate,nb_read_frames,codec_name:format=duration','-of','json',str(dest)],ROOT/'results'/f'{name}_{extension}_probe.log'))
        stream=info['streams'][0]
        assert (stream['width'],stream['height'],stream['nb_read_frames'],stream['avg_frame_rate'])==(1280,720,'1962','25/1')
        assert abs(float(info['format']['duration'])-78.48)<.01
        run([FFMPEG,'-v','error','-nostdin','-xerror','-i',str(dest),'-f','null','-'],ROOT/'results'/f'{name}_{extension}_decode.log')
        target=BASE/'phase3_diagnosis_20261026/inputs'/dest.name
        assert not target.exists();shutil.copyfile(dest,target);assert sha(dest)==sha(target)
        media.append({'name':name,'format':extension,'path':str(dest),'file':dest.name,'bytes':dest.stat().st_size,'sha256':sha(dest),
                      'frames':1962,'fps':25,'duration_s':78.48,'strict_full_decode':'PASS'})
    return media


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    summary=json.loads((SOURCE/'summary.json').read_text())
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        media=[r for group in pool.map(one,[26,27,28]) for r in group]
    models=[]
    for r in summary['conditions']:
        source=next(x for x in r['scenes'] if x['scene']=='source')
        models.append({'name':r['name'],'title':r['title'],'seed':r['seed'],'checkpoint_sha256':r['checkpoint_sha256'],
                       'predicted_down':source['A_to_B'],'predicted_up':source['B_to_A'],
                       'Toros_TP':r['Toros_event_metrics']['TP'],'Toros_FP':r['Toros_event_metrics']['FP'],'Toros_FN':r['Toros_event_metrics']['FN'],
                       'stem':f'{r["name"]}_f8912-10873' if r['name'].startswith('epoch20_') else f'{r["name"]}_f8912-10873'})
    data={'source_first':8912,'source_last':10873,'source_fps':25,'clip_seconds':78.48,'default_seed':26,
          'models':models,'media':media,'source_accuracy':None,'source_scope':'Observed development clip; predictions not independent truth'}
    dest=BASE/'phase3_diagnosis_20261026/annotation_workbench/training_preview_data.json'
    dest.write_text(json.dumps(data,indent=2),encoding='utf-8')
    sheet=Image.new('RGB',(3*640,420),(20,26,30));draw=ImageDraw.Draw(sheet)
    for i,seed in enumerate([26,27,28]):
        image=Image.open(SOURCE/f'epoch20_seed{seed}'/'source_f9420.jpg').convert('RGB').resize((640,360))
        sheet.paste(image,(i*640,50));draw.text((i*640+12,15),f'20epochs seed{seed} source9420',fill='white')
    sheet.save(OUT/'three_seeds_source9420.jpg',quality=94)
    (ROOT/'results/media_verification.json').write_text(json.dumps({'status':'ALL_SIX_MEDIA_FULL_DECODE_PASS','media':media,'models':models},indent=2),encoding='utf-8')
    print(json.dumps({'status':'ALL_SIX_MEDIA_FULL_DECODE_PASS','media':[(r['name'],r['format'],r['bytes']) for r in media]}),flush=True)


if __name__=='__main__':main()
