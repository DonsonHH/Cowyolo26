from pathlib import Path
import concurrent.futures,hashlib,json,shutil,subprocess
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
SOURCE=ROOT/'delivery/results/replay_v2';OUT=ROOT/'previews'
WORK=PROJECT/'phase3_diagnosis_20261026/annotation_workbench';EXPOSED=WORK.parent/'inputs'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def folder_for(condition):
    folder=SOURCE/condition['name']
    return folder if folder.exists() else ROOT/'delivery/results/full640_confirmation'/condition['name']
def execute(cmd,log):
    r=subprocess.run(cmd,capture_output=True);Path(log).write_bytes(r.stderr)
    assert r.returncode==0,(cmd,r.stderr.decode(errors='replace')[-1000:])
    return r.stdout
def encode(condition):
    source=folder_for(condition)/'transfer_h264.mp4';seed=condition['seed'];stem=f'counting_recovery_{condition["name"]}_f8912-10873';media=[]
    for ext in ['mp4','webm']:
        target=OUT/f'{stem}.{ext}';assert not target.exists()
        codec=['-c:v','libx264','-preset','veryfast','-crf','25','-pix_fmt','yuv420p','-movflags','+faststart'] if ext=='mp4' else ['-c:v','libvpx-vp9','-deadline','realtime','-cpu-used','7','-crf','36','-b:v','0','-row-mt','1','-pix_fmt','yuv420p']
        if ext=='mp4':
            shutil.copyfile(source,target)
        else:
            execute([shutil.which('ffmpeg'),'-hide_banner','-nostdin','-n','-i',str(source),'-an','-threads','2',*codec,str(target)],ROOT/f'results/{condition["name"]}_{ext}_encode.log')
        info=json.loads(execute([shutil.which('ffprobe'),'-v','error','-count_frames','-show_entries','stream=width,height,avg_frame_rate,nb_read_frames:format=duration','-of','json',str(target)],ROOT/f'results/{condition["name"]}_{ext}_probe.log'))
        v=info['streams'][0];assert (v['width'],v['height'],v['avg_frame_rate'],v['nb_read_frames'])==(1280,720,'25/1','1962')
        assert abs(float(info['format']['duration'])-78.48)<.01
        execute([shutil.which('ffmpeg'),'-v','error','-nostdin','-xerror','-i',str(target),'-f','null','-'],ROOT/f'results/{condition["name"]}_{ext}_decode.log')
        destination=EXPOSED/target.name;assert not destination.exists();shutil.copyfile(target,destination);assert sha(destination)==sha(target)
        media.append({'seed':seed,'file':target.name,'bytes':target.stat().st_size,'sha256':sha(target),'frames':1962,'fps':25,'duration_s':78.48,'strict_full_decode':'PASS'})
    return {**condition,'stem':stem,'events':load(folder_for(condition)/'source_events.json'),
        'label':f'{condition["arm"]["name"]} · seed{seed}'},media
def main():
    check=load(ROOT/'results/local_verification.json');assert check['baseline_regression'] is True
    summary=load(SOURCE/'summary.json');extension=load(ROOT/'delivery/results/full640_confirmation/summary.json')
    all_conditions=summary['conditions']+extension['conditions']
    selected=[r for seed in [26,27,28] for r in all_conditions if r['seed']==seed and r['arm']['name']=='full640_5hz']
    selected += [r for r in all_conditions if r['arm']['name']=='channel320_25hz']
    assert len(selected)==4
    OUT.mkdir(exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        encoded=list(pool.map(encode,selected))
    conditions=[r[0] for r in encoded];media=[m for r in encoded for m in r[1]]
    previous=load(PROJECT/'orientation_video_20261027/results/media_verification.json');assert previous['browser_verified'] is True
    baselines=[];reused=[]
    for seed,down in [(26,8),(27,6),(28,8)]:
        stem=f'video_rotate90_seed{seed}_f8912-10873'
        for ext in ['mp4','webm']:
            item=next(r for r in previous['media'] if r['file']==f'{stem}.{ext}')
            assert sha(EXPOSED/item['file'])==item['sha256'];reused.append(item)
        baselines.append({'seed':seed,'down':down,'up':0,'stem':stem})
    data={'status':'THREE_SEED_DEVELOPMENT_RECOVERY_WITH_VERIFIED_MEDIA','default_condition':conditions[0]['name'],
        'conditions':conditions,'baselines':baselines,'all_results':all_conditions,'media':media,
        'reused_baseline_media':reused,'source_frame_range':[8912,10873],'independent_source_accuracy':None,
        'protocol_sha256':summary['protocol_sha256'],'new_training_updates':0,'board_execution':False,
        'compressed_video_is_for_viewing_only':True}
    page=WORK/'counting_recovery_preview.html';data_path=WORK/'counting_recovery_preview_data.json';assert not page.exists() and not data_path.exists()
    shutil.copyfile(ROOT/'templates/preview.html',page);data_path.write_text(json.dumps(data,indent=2),encoding='utf-8')
    # Samepreselected missedpassage frame, allseeds/old/new, noaddedboxes.
    sheet=Image.new('RGB',(3*640,2*386),'white');draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    for j,(condition,seed) in enumerate(zip(conditions,[26,27,28])):
        old=PROJECT/f'orientation_video_20261027/delivery/results/inference/clockwise90_seed{seed}/source_f9420.jpg'
        new=folder_for(condition)/'f9420.jpg'
        for i,path in enumerate([old,new]):
            with Image.open(path) as im:im.load();picture=im.resize((640,360))
            sheet.paste(picture,(j*640,i*386));draw.text((j*640+8,i*386+363),f'{"Previous" if i==0 else "Recovery"} | seed{seed} | source9420',font=font,fill='black')
    contact=OUT/'source9420_old_new_all_seeds.jpg';sheet.save(contact,quality=92)
    record={'status':'EIGHT_NEW_MEDIA_DECODED_OLD_HASHES_BOUND_BROWSER_QA_PENDING','media':media,'reused_baselines':reused,
        'page_sha256':sha(page),'data_sha256':sha(data_path),'contact_sha256':sha(contact),'browser_verified':False,
        'independent_source_accuracy_verified':False,'board_execution':False,'whole_goal_complete':False}
    path=ROOT/'results/media_verification.json';assert not path.exists();path.write_text(json.dumps(record,indent=2),encoding='utf-8')
    print(json.dumps({'status':record['status'],'conditions':[(r['seed'],r['predicted_down']) for r in conditions]}),flush=True)
if __name__=='__main__':main()
