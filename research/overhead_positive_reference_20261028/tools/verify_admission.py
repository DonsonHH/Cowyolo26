"""Verify source-bound native review and strict failure records without generating labels."""
from pathlib import Path,PurePosixPath
import hashlib,json,subprocess,tarfile
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def unpack(name,size,digest):
    p=ROOT/(name+'.tar.gz');assert p.stat().st_size==size and sha(p)==digest
    out=ROOT/name;out.mkdir(exist_ok=False)
    with tarfile.open(p) as t:
        members=t.getmembers()
        for m in members:
            n=PurePosixPath(m.name);assert m.isfile() and not n.is_absolute() and '..' not in n.parts
        t.extractall(out,filter='data')
    return out,len(members)
def main():
    out,native_files=unpack('native_review_delivery',148940508,'f0da60352b067badf80dc6dc3b6f7f85790fc63e0c79880afd21380e24ab733d')
    dec,strict_files=unpack('decode_diagnosis_delivery',502601,'ac1b78427d114bacba12664622a417b5c188fa5b0189b50e37dc6e3d3e023df6')
    native=out/'results/native_review';s=load(native/'summary.json');d=load(dec/'results/decode_diagnosis/summary.json');m=load(ROOT/'input/video_manifest.json')
    assert s['source_sha256']==d['source_sha256']==m['source_sha256']=='8210a5bf206dd7f2356bc3d4653b439ab6de12ccfdc8209fe301ac7f02807058'
    src=Path(m['local_path']);assert sha(src)==m['source_sha256'] and src.stat().st_size==s['source_bytes']==260358184
    assert s['source_frames']==14107 and s['source_fps']==25 and s['duration_s']==564.28
    assert s['protocol_sha256']==sha(ROOT/'protocol/selection_v1.json') and s['new_model_predictions']==0
    assert sha(dec/'results/decode_diagnosis/strict_ffmpeg.log')==d['log_sha256'] and d['ffmpeg_exit_code']==183 and not d['strict_decode_passed']
    packets=load(ROOT/'evidence/source_packet_clock.json')['packets'];assert len(packets)==14107
    error=next(r for r in d['decoder_error_records'] if 'error while decoding' in r['message'] and r['latest_prior_showinfo'] is not None)
    near=error['latest_prior_showinfo']['output_frame0'];keys=[i for i,r in enumerate(packets) if 'K' in r['flags']]
    quarantine=[max(i for i in keys if i<=near),len(packets)-1]
    images=[]
    for row in [*s['overview_snapshots'],*s['native_30s_anchors'],*s['overview_pages']]:
        f=native/row['file'];assert sha(f)==row['sha256']
        with Image.open(f) as im:im.load();size=im.size
        if 'image_size' in row:assert list(size)==row['image_size']
        images.append({'path':str(f),'sha256':sha(f),'size':size})
    movie=native/s['review_movie'];assert sha(movie)==s['review_movie_sha256']
    p=subprocess.run(['ffprobe','-v','error','-count_frames','-select_streams','v:0','-show_entries','stream=width,height,nb_read_frames,r_frame_rate','-of','json',str(movie)],capture_output=True,check=True)
    assert not p.stderr;probe=json.loads(p.stdout)['streams'][0]
    assert (probe['width'],probe['height'],probe['r_frame_rate'])==(480,700,'5/1')
    assert int(probe['nb_read_frames'])==s['review_movie_frames']==s['review_movie_complete_decode_frames']==2822
    result={'status':'POSITIVE_LONG_SOURCE_NATIVE_REVIEW_AND_STRICT_FAILURE_VERIFIED','source_sha256':m['source_sha256'],'source_bytes':260358184,
            'native_frames_counted':14107,'native_duration_s':564.28,'overview_anchor_images':len(s['overview_snapshots']),
            'native_30s_images':len(s['native_30s_anchors']),'overview_pages':len(s['overview_pages']),'all_images_decoded':len(images),
            'native_archive_files':native_files,'strict_archive_files':strict_files,'strict_decoder_exit':183,
            'strict_showinfo_frames':d['showinfo_frames_before_stop'],'conservative_quarantine_frames0_inclusive':quarantine,
            'decoder_failure_is_not_task_failure':True,'new_reference_or_prediction_claimed':False,
            'review_movie_decoded_frames':2822,'review_movie_sha256':sha(movie),'images':images,
            'visual_review_pending':True,'whole_goal_complete':False}
    target=ROOT/'results/admission_verification.json';target.parent.mkdir(exist_ok=True);assert not target.exists();target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='images'}),flush=True)
if __name__=='__main__':main()
