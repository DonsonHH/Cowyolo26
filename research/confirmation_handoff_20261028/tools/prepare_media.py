from pathlib import Path
import concurrent.futures,hashlib,json,shutil,subprocess
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
OUT=ROOT/'previews';WORK=PROJECT/'phase3_diagnosis_20261026/annotation_workbench';EXPOSED=WORK.parent/'inputs'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def execute(command,log):
    r=subprocess.run(command,capture_output=True);Path(log).write_bytes(r.stderr);assert r.returncode==0,r.stderr[-800:];return r.stdout
def encode(row):
    seed=row['seed'];folder=ROOT/f'delivery/results/replay_v2/seed{seed}';stem=f'confirmation_handoff_seed{seed}_f8912-10873';items=[]
    for ext in ['mp4','webm']:
        target=OUT/f'{stem}.{ext}';assert not target.exists()
        if ext=='mp4':shutil.copyfile(folder/'view.mp4',target)
        else:execute([shutil.which('ffmpeg'),'-hide_banner','-nostdin','-n','-i',str(folder/'view.mp4'),'-an','-threads','2','-c:v','libvpx-vp9','-deadline','realtime','-cpu-used','7','-crf','36','-b:v','0','-row-mt','1','-pix_fmt','yuv420p',str(target)],ROOT/f'results/seed{seed}_{ext}_encode.log')
        info=json.loads(execute([shutil.which('ffprobe'),'-v','error','-count_frames','-show_entries','stream=width,height,avg_frame_rate,nb_read_frames:format=duration','-of','json',str(target)],ROOT/f'results/seed{seed}_{ext}_probe.log'))
        s=info['streams'][0];assert (s['width'],s['height'],s['avg_frame_rate'],s['nb_read_frames'])==(1280,720,'25/1','1962')
        assert abs(float(info['format']['duration'])-78.48)<.01
        execute([shutil.which('ffmpeg'),'-v','error','-nostdin','-xerror','-i',str(target),'-f','null','-'],ROOT/f'results/seed{seed}_{ext}_decode.log')
        destination=EXPOSED/target.name;assert not destination.exists();shutil.copyfile(target,destination);assert sha(destination)==sha(target)
        items.append({'seed':seed,'file':target.name,'bytes':target.stat().st_size,'sha256':sha(target),'frames':1962,'fps':25,'duration_s':78.48,'strict_full_decode':'PASS'})
    return {'name':f'handoff_seed{seed}','seed':seed,'stem':stem,'label':f'入口观察交接 · seed{seed}',
       'predicted_down':row['handoff_down'],'predicted_up':row['handoff_up'],'events':load(folder/'handoff_events.json')},items
def main():
    assert load(ROOT/'results/local_verification.json')['counter_paths']==9
    rows=load(ROOT/'delivery/results/replay_v2/summary.json')['conditions'];OUT.mkdir(exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(encode,rows))
    conditions=[r[0] for r in results];media=[x for r in results for x in r[1]]
    previous=load(PROJECT/'counting_recovery_20261028/results/media_verification.json');assert previous['browser_verified']
    baselines=[];reused=[]
    for row in rows:
        seed=row['seed'];stem=f'counting_recovery_full640_5hz_seed{seed}_f8912-10873'
        baselines.append({'seed':seed,'stem':stem,'down':row['baseline_down'],'up':row['baseline_up']})
        for ext in ['mp4','webm']:
            r=next(r for r in previous['media'] if r['file']==f'{stem}.{ext}');assert sha(EXPOSED/r['file'])==r['sha256'];reused.append(r)
    data={'default_condition':'handoff_seed26','conditions':conditions,'baselines':baselines,'comparisons':rows,
      'source_frame_range':[8912,10873],'media':media,'reused_baselines':reused,'independent_source_accuracy':None,
      'protocol_sha256':sha(ROOT/'protocol/handoff_v1.json'),'new_detector_forwards':0,'training_updates':0,'board_execution':False}
    page=WORK/'confirmation_handoff_preview.html';dpath=WORK/'confirmation_handoff_preview_data.json';assert not page.exists() and not dpath.exists()
    shutil.copyfile(ROOT/'templates/preview.html',page);dpath.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
    sheet=Image.new('RGB',(1920,772),'white');draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    for j,row in enumerate(rows):
        seed=row['seed'];prior=PROJECT/f'counting_recovery_20261028/delivery/results/replay_v2/full640_5hz_seed{seed}'
        if not prior.exists():prior=PROJECT/f'counting_recovery_20261028/delivery/results/full640_confirmation/full640_5hz_seed{seed}'
        new=ROOT/f'delivery/results/replay_v2/seed{seed}'
        for i,folder in enumerate([prior,new]):
            with Image.open(folder/'f9345.jpg') as image:image.load();sheet.paste(image.resize((640,360)),(j*640,i*386))
            draw.text((j*640+8,i*386+363),f'{"Baseline" if i==0 else "Handoff"} | seed{seed} | source9345',font=font,fill='black')
    contact=OUT/'source9345_paired_all_seeds.jpg';sheet.save(contact,quality=93)
    record={'status':'SIX_HANDOFF_MEDIA_FULLY_DECODED_BROWSER_QA_PENDING','media':media,'reused_baselines':reused,
      'page_sha256':sha(page),'data_sha256':sha(dpath),'contact_sha256':sha(contact),
      'browser_verified':False,'source_accuracy_verified':False,'board_execution':False,'whole_goal_complete':False}
    path=ROOT/'results/media_verification.json';assert not path.exists();path.write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps({'status':record['status'],'media':len(media)}))
if __name__=='__main__':main()
