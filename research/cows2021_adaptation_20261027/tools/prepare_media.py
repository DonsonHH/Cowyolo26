"""Publish previews only after complete replay and independent arithmetic checks."""
from pathlib import Path
import concurrent.futures,hashlib,json,shutil,subprocess
from PIL import Image,ImageDraw

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parent
SOURCE=ROOT/'delivery/results/inference'
OUT=ROOT/'previews'
WORKBENCH=PROJECT/'phase3_diagnosis_20261026/annotation_workbench'
FFMPEG=shutil.which('ffmpeg');FFPROBE=shutil.which('ffprobe')
assert FFMPEG and FFPROBE


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def run(args,log):
    response=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    log.write_bytes(response.stderr)
    assert response.returncode==0,(args,response.stderr.decode(errors='replace')[-2000:])
    return response.stdout


def one(seed):
    source=SOURCE/f'seed{seed}/source_transfer.mp4'
    assert source.is_file();records=[]
    for extension in ['mp4','webm']:
        name=f'cows2021_seed{seed}_f8912-10873';dest=OUT/f'{name}.{extension}'
        assert not dest.exists()
        codec=(['-c:v','libx264','-preset','veryfast','-crf','25','-pix_fmt','yuv420p','-movflags','+faststart']
               if extension=='mp4' else ['-c:v','libvpx-vp9','-deadline','realtime','-cpu-used','7',
                                          '-crf','36','-b:v','0','-row-mt','1','-pix_fmt','yuv420p'])
        run([FFMPEG,'-hide_banner','-nostdin','-n','-i',str(source),'-an','-threads','2',*codec,str(dest)],
            ROOT/'results'/f'media_seed{seed}_{extension}_encode.log')
        info=json.loads(run([FFPROBE,'-v','error','-count_frames','-show_entries',
                            'stream=width,height,avg_frame_rate,nb_read_frames,codec_name:format=duration',
                            '-of','json',str(dest)],ROOT/'results'/f'media_seed{seed}_{extension}_probe.log'))
        stream=info['streams'][0]
        assert (stream['width'],stream['height'],stream['nb_read_frames'],stream['avg_frame_rate'])==(1280,720,'1962','25/1')
        assert abs(float(info['format']['duration'])-78.48)<.01
        run([FFMPEG,'-v','error','-nostdin','-xerror','-i',str(dest),'-f','null','-'],
            ROOT/'results'/f'media_seed{seed}_{extension}_decode.log')
        target=PROJECT/'phase3_diagnosis_20261026/inputs'/dest.name
        assert not target.exists();shutil.copyfile(dest,target);assert sha(dest)==sha(target)
        records.append({'seed':seed,'format':extension,'file':dest.name,'path':str(dest),
                        'bytes':dest.stat().st_size,'sha256':sha(dest),'strict_full_decode':'PASS',
                        'frames':1962,'fps':25,'duration_s':78.48})
    return records


def main():
    audit=json.loads((ROOT/'results/independent_verification.json').read_text(encoding='utf-8'))
    assert audit['status']=='DATA_TRAINING_FREEZE_AND_SIX_EVENT_REPLAYS_INDEPENDENTLY_VERIFIED'
    inference=json.loads((SOURCE/'summary.json').read_text(encoding='utf-8'))
    assert inference['status']=='THREE_COWS2021_MODELS_SOURCE_AND_KNOWN_DIAGNOSTIC_COMPLETE'
    assert [r['seed'] for r in inference['conditions']]==[26,27,28]
    training=json.loads((ROOT/'delivery/results/training/summary.json').read_text(encoding='utf-8'))
    baseline_path=WORKBENCH/'training_preview_data.json'
    previous=json.loads(baseline_path.read_text(encoding='utf-8'))
    assert (previous['source_first'],previous['source_last'],previous['source_fps'],previous['clip_seconds'])==(8912,10873,25,78.48)
    originals=[r for r in previous['models'] if r['name'] in ['generic','pilot']]
    assert {r['name'] for r in originals}=={'generic','pilot'}
    for model in originals:
        for extension in ['webm','mp4']:
            assert (PROJECT/'phase3_diagnosis_20261026/inputs'/f"{model['stem']}.{extension}").is_file()
    OUT.mkdir(exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        media=[row for group in pool.map(one,[26,27,28]) for row in group]
    models=[]
    for result in inference['conditions']:
        scene=next(r for r in result['scenes'] if r['scene']=='source')
        trained=next(r for r in training['conditions'] if r['seed']==result['seed'])
        assert result['checkpoint_sha256']==trained['checkpoint_sha256']
        models.append({'name':result['name'],'title':result['title'],'seed':result['seed'],
                       'checkpoint_sha256':result['checkpoint_sha256'],
                       'predicted_down':scene['A_to_B'],'predicted_up':scene['B_to_A'],
                       'Toros_TP':result['Toros_event_metrics']['TP'],'Toros_FP':result['Toros_event_metrics']['FP'],
                       'Toros_FN':result['Toros_event_metrics']['FN'],'stem':f"cows2021_seed{result['seed']}_f8912-10873",
                       'development_AP50_95':trained['last_epoch_validation']['metrics/mAP50-95(B)'],
                       'validation_scope':'Cows2021 date-grouped development, not same validation as earlier OpenCows models'})
    metadata={'source_first':8912,'source_last':10873,'source_fps':25,'clip_seconds':78.48,
              'models':originals+models,'media':media,'default_seed':26,'source_accuracy':None,
              'baseline_origin':'previous independently verified same-interval replay',
              'baseline_metadata_sha256':sha(baseline_path),
              'independent_verification_sha256':sha(ROOT/'results/independent_verification.json'),
              'source_scope':'Development predictions; independent event reference pending'}
    data_path=WORKBENCH/'cows2021_preview_data.json';page=WORKBENCH/'cows2021_preview.html'
    assert not data_path.exists() and not page.exists()
    data_path.write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    shutil.copyfile(ROOT/'templates/cows2021_preview.html',page)
    result={'status':'SIX_MEDIA_FULL_DECODED_PREVIEW_PAGE_CREATED_BROWSER_QA_PENDING',
            'media':media,'models':originals+models,'page_sha256':sha(page),'data_sha256':sha(data_path),
            'browser_verified':False,'whole_goal_complete':False}
    (ROOT/'results/media_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['media','models']}),flush=True)


if __name__=='__main__':main()
