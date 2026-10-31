from pathlib import Path
import concurrent.futures,csv,hashlib,json,shutil,subprocess

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parent
SOURCE=ROOT/'delivery/results/inference'
WORKBENCH=PROJECT/'phase3_diagnosis_20261026/annotation_workbench'
OUT=ROOT/'previews'
FFMPEG=shutil.which('ffmpeg');FFPROBE=shutil.which('ffprobe')
assert FFMPEG and FFPROBE


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def execute(command,log):
    r=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE);log.write_bytes(r.stderr)
    assert r.returncode==0,(command,r.stderr.decode(errors='replace')[-2000:])
    return r.stdout


def encode(seed):
    source=SOURCE/f'clockwise90_seed{seed}/source_transfer.mp4';assert source.is_file()
    result=[]
    for ext in ['mp4','webm']:
        filename=f'video_rotate90_seed{seed}_f8912-10873.{ext}';target=OUT/filename;assert not target.exists()
        codec=(['-c:v','libx264','-preset','veryfast','-crf','25','-pix_fmt','yuv420p','-movflags','+faststart'] if ext=='mp4'
               else ['-c:v','libvpx-vp9','-deadline','realtime','-cpu-used','7','-crf','36','-b:v','0','-row-mt','1','-pix_fmt','yuv420p'])
        execute([FFMPEG,'-hide_banner','-nostdin','-n','-i',str(source),'-an','-threads','2',*codec,str(target)],ROOT/'results'/f'media_seed{seed}_{ext}_encode.log')
        info=json.loads(execute([FFPROBE,'-v','error','-count_frames','-show_entries',
                                'stream=codec_name,width,height,avg_frame_rate,nb_read_frames:format=duration',
                                '-of','json',str(target)],ROOT/'results'/f'media_seed{seed}_{ext}_probe.log'))
        stream=info['streams'][0]
        assert (stream['width'],stream['height'],stream['nb_read_frames'],stream['avg_frame_rate'])==(1280,720,'1962','25/1')
        assert abs(float(info['format']['duration'])-78.48)<.01
        execute([FFMPEG,'-v','error','-nostdin','-xerror','-i',str(target),'-f','null','-'],ROOT/'results'/f'media_seed{seed}_{ext}_decode.log')
        exposed=PROJECT/'phase3_diagnosis_20261026/inputs'/filename;assert not exposed.exists()
        shutil.copyfile(target,exposed);assert sha(target)==sha(exposed)
        result.append({'seed':seed,'orientation':'clockwise90','file':filename,'bytes':target.stat().st_size,
                       'sha256':sha(target),'frames':1962,'fps':25,'duration_s':78.48,'strict_full_decode':'PASS'})
    return result


def main():
    check=json.loads((ROOT/'results/independent_verification.json').read_text(encoding='utf-8'))
    assert check['status']=='INVERSE_COORDINATES_ORIGINAL_REGRESSIONS_AND_12_EVENT_REPLAYS_INDEPENDENTLY_VERIFIED'
    assert check['all_original_event_and_track_regressions_passed']==6
    summary=json.loads((SOURCE/'summary.json').read_text(encoding='utf-8'))
    prior_path=WORKBENCH/'cows2021_preview_data.json';prior=json.loads(prior_path.read_text(encoding='utf-8'))
    old_media=json.loads((PROJECT/'cows2021_adaptation_20261027/results/media_verification.json').read_text(encoding='utf-8'))
    assert old_media['browser_verified'] is True
    OUT.mkdir(exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        media=[r for group in pool.map(encode,[26,27,28]) for r in group]
    conditions=[];reused=[]
    for item in summary['conditions']:
        seed,orientation=item['seed'],item['orientation'];folder=SOURCE/item['name']
        scene=next(r for r in item['scenes'] if r['scene']=='source')
        if orientation=='original':
            old=next(r for r in prior['models'] if r['name']==f'seed{seed}')
            assert old['checkpoint_sha256']==item['checkpoint_sha256']
            assert (old['predicted_down'],old['predicted_up'])==(scene['A_to_B'],scene['B_to_A'])
            stem=old['stem']
            for ext in ['mp4','webm']:
                old_record=next(r for r in old_media['media'] if r['file']==f'{stem}.{ext}')
                exposed=PROJECT/'phase3_diagnosis_20261026/inputs'/f'{stem}.{ext}'
                assert exposed.stat().st_size==old_record['bytes'] and sha(exposed)==old_record['sha256']
                reused.append({'seed':seed,'orientation':orientation,'file':exposed.name,'sha256':sha(exposed),
                               'old_media_fully_decoded_and_browser_verified':True,'exact_new_track_regression_passed':True})
        else:stem=f'video_rotate90_seed{seed}_f8912-10873'
        pre=list(csv.DictReader((folder/'source_pretracker_boxes.csv').open(encoding='utf-8',newline='')))
        pre_roi=[r for r in pre if 8912<=int(r['frame'])<=10873 and .34<(float(r['x1'])+float(r['x2']))/5120<.75]
        tracked=list(csv.DictReader((folder/'source_tracks.csv').open(encoding='utf-8',newline='')))
        conditions.append({'name':item['name'],'arm':orientation,'seed':seed,'checkpoint_sha256':item['checkpoint_sha256'],
                           'source_down':scene['A_to_B'],'source_up':scene['B_to_A'],
                           'source_pretracker_ROI_frames':len({r['frame'] for r in pre_roi}),
                           'source_tracked_ROI_frames':len({r['source_frame'] for r in tracked}),
                           'Toros_TP':item['Toros_event_metrics']['TP'],'Toros_FP':item['Toros_event_metrics']['FP'],
                           'Toros_FN':item['Toros_event_metrics']['FN'],'stem':stem})
    data={'status':'PAIRED_NATIVE_COORDINATE_VIDEO_REPLAYS_WITH_VERIFIED_MEDIA','source_first':8912,'source_last':10873,
          'source_fps':25,'clip_seconds':78.48,'source_sample_frames_in_requested_interval':392,
          'conditions':conditions,'new_media':media,'reused_original_media':reused,'default_seed':26,
          'prior_media_metadata_sha256':sha(prior_path),'independent_verification_sha256':sha(ROOT/'results/independent_verification.json'),
          'source_independent_count_accuracy':None,'training_updates':0}
    data_path=WORKBENCH/'video_rotation_preview_data.json';page=WORKBENCH/'video_rotation_preview.html'
    assert not data_path.exists() and not page.exists()
    data_path.write_text(json.dumps(data,indent=2),encoding='utf-8')
    shutil.copyfile(ROOT/'templates/video_rotation_preview.html',page)
    record={'status':'SIX_NEW_MEDIA_STRICT_DECODE_AND_SIX_ORIGINAL_MEDIA_HASHES_PASS_BROWSER_QA_PENDING',
            'media':media,'reused_original_media':reused,'conditions':conditions,'page_sha256':sha(page),
            'data_sha256':sha(data_path),'browser_verified':False,'source_accuracy_verified':False,'whole_goal_complete':False}
    target=ROOT/'results/media_verification.json';assert not target.exists();target.write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in record.items() if k not in ['media','reused_original_media']}),flush=True)


if __name__=='__main__':main()
