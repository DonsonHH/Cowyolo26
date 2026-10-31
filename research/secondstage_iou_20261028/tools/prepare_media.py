from pathlib import Path
import concurrent.futures,hashlib,json,shutil,subprocess
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
OUT=ROOT/'previews';WORK=PROJECT/'phase3_diagnosis_20261026/annotation_workbench';EXPOSED=WORK.parent/'inputs'
load=lambda p:json.loads(Path(p).read_text(encoding='utf-8'))
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def execute(cmd,log):
    r=subprocess.run(cmd,capture_output=True);Path(log).write_bytes(r.stderr);assert r.returncode==0,r.stderr[-1000:];return r.stdout
def encode(row):
    seed=row['seed'];folder=ROOT/f'media_delivery/results/{row["name"]}';stem=f'secondstage_iou_seed{seed}_f8912-10873';files=[]
    for ext in ['mp4','webm']:
        target=OUT/f'{stem}.{ext}';assert not target.exists()
        if ext=='mp4':shutil.copyfile(folder/'view.mp4',target)
        else:execute([shutil.which('ffmpeg'),'-hide_banner','-nostdin','-n','-i',str(folder/'view.mp4'),'-an','-threads','2','-c:v','libvpx-vp9','-deadline','realtime','-cpu-used','7','-crf','36','-b:v','0','-row-mt','1','-pix_fmt','yuv420p',str(target)],ROOT/f'results/seed{seed}_{ext}_encode.log')
        info=json.loads(execute([shutil.which('ffprobe'),'-v','error','-count_frames','-show_entries','stream=width,height,avg_frame_rate,nb_read_frames:format=duration','-of','json',str(target)],ROOT/f'results/seed{seed}_{ext}_probe.log'))
        s=info['streams'][0];assert (s['width'],s['height'],s['avg_frame_rate'],s['nb_read_frames'])==(1280,720,'25/1','1962')
        assert abs(float(info['format']['duration'])-78.48)<.01
        execute([shutil.which('ffmpeg'),'-v','error','-nostdin','-xerror','-i',str(target),'-f','null','-'],ROOT/f'results/seed{seed}_{ext}_decode.log')
        destination=EXPOSED/target.name;assert not destination.exists();shutil.copyfile(target,destination);assert sha(destination)==sha(target)
        files.append({'seed':seed,'file':target.name,'bytes':target.stat().st_size,'sha256':sha(target),'frames':1962,'fps':25,'duration_s':78.48,'strict_full_decode':'PASS'})
    return {'name':row['name'],'seed':seed,'stem':stem,'label':f'第二阶段纯IoU · seed{seed}',
      'predicted_down':row['predicted_down'],'predicted_up':row['predicted_up'],
      'events':load(ROOT/f'delivery/results/{row["name"]}/handoff_events.json')},files
def main():
    assert load(ROOT/'results/media_archive_verification.json')['files']==25
    summary=load(ROOT/'delivery/results/summary.json');selected=[r for r in summary['conditions'] if r['variant']=='secondstage_iou'];assert len(selected)==3
    OUT.mkdir(exist_ok=True)
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:results=list(pool.map(encode,selected))
    conditions=[r[0] for r in results];media=[x for r in results for x in r[1]]
    old=load(PROJECT/'confirmation_handoff_20261028/results/media_verification.json');assert old['browser_verified']
    baselines=[];reused=[];comparisons=[];check=load(ROOT/'results/local_verification.json')
    for c in selected:
        seed=c['seed'];stem=f'confirmation_handoff_seed{seed}_f8912-10873';b=next(r for r in summary['conditions'] if r['seed']==seed and r['variant']=='installed_baseline')
        baselines.append({'seed':seed,'stem':stem,'down':b['predicted_down'],'up':b['predicted_up']})
        for ext in ['mp4','webm']:
            r=next(x for x in old['media'] if x['file']==f'{stem}.{ext}');assert sha(EXPOSED/r['file'])==r['sha256'];reused.append(r)
        comparisons.append({'seed':seed,'baseline_down':b['predicted_down'],'baseline_up':b['predicted_up'],
            'candidate_down':c['predicted_down'],'candidate_up':c['predicted_up'],'low_matches_in_scope':c['applied_low_stage_matches_in_scope'],
            'ROI_rows_before':b['ROI_track_rows'],'ROI_rows_after':c['ROI_track_rows'],
            'event_times_directions_equal':next(r for r in check['comparisons'] if r['seed']==seed)['event_times_and_directions_exact_without_ID']})
    data={'default_condition':'secondstage_iou_seed26','conditions':conditions,'baselines':baselines,'comparisons':comparisons,
          'source_frame_range':[8912,10873],'protocol_sha256':sha(ROOT/'protocol/secondstage_v1.json'),
          'media':media,'new_detector_forwards':0,'training_updates':0,'independent_source_accuracy':None,'board_execution':False}
    page=WORK/'secondstage_iou_preview.html';dpath=WORK/'secondstage_iou_preview_data.json';assert not page.exists() and not dpath.exists()
    shutil.copyfile(ROOT/'templates/preview.html',page);dpath.write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
    sheet=Image.new('RGB',(1920,772),'white');draw=ImageDraw.Draw(sheet);font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',18)
    for j,c in enumerate(selected):
        seed=c['seed'];folders=[PROJECT/f'confirmation_handoff_20261028/delivery/results/replay_v2/seed{seed}',ROOT/f'media_delivery/results/{c["name"]}']
        for i,folder in enumerate(folders):
            with Image.open(folder/'f9420.jpg') as image:image.load();sheet.paste(image.resize((640,360)),(j*640,i*386))
            draw.text((j*640+8,i*386+363),f'{"Baseline" if i==0 else "Secondstage IoU"} | seed{seed} | source9420',font=font,fill='black')
    contact=OUT/'source9420_paired_all_seeds.jpg';sheet.save(contact,quality=93)
    record={'status':'SIX_CONTROL_MEDIA_STRICT_DECODED_BROWSER_QA_PENDING','media':media,'reused_baselines':reused,
        'page_sha256':sha(page),'data_sha256':sha(dpath),'contact_sha256':sha(contact),'browser_verified':False,
        'source_accuracy_verified':False,'board_execution':False,'whole_goal_complete':False}
    path=ROOT/'results/media_verification.json';assert not path.exists();path.write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps({'status':record['status'],'media':len(media)}))
if __name__=='__main__':main()
