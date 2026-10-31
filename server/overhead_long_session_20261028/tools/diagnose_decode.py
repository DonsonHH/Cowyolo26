"""Slurm-only strict decoding; preserve the expected failure and localize its packet context."""
from pathlib import Path
import hashlib,json,os,re,socket,subprocess
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/overhead_long_session_20261028')
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    p=json.loads((ROOT/'protocol/selection_v1.json').read_text());src=ROOT/'input'/p['selected']['filename']
    manifest=json.loads((ROOT/'input/video_manifest.json').read_text());assert hashlib.sha256(src.read_bytes()).hexdigest()==manifest['source_sha256']
    out=ROOT/'results/decode_diagnosis';out.mkdir(parents=True,exist_ok=False)
    ffmpeg='/share/home/renly/miniconda3/envs/pid310_gpu/bin/ffmpeg'
    command=[ffmpeg,'-hide_banner','-loglevel','info','-threads','1','-err_detect','explode','-i',str(src),'-an','-vf','showinfo','-xerror','-f','null','-']
    log=out/'strict_ffmpeg.log'
    with log.open('wb') as f:proc=subprocess.run(command,stdout=subprocess.DEVNULL,stderr=f)
    text=log.read_text(errors='replace');lines=text.splitlines();errors=[];latest=None;all_frames=[]
    for index,line in enumerate(lines):
        frame=re.search(r'Parsed_showinfo[^\]]*\]\s+n:\s*(\d+)\s+pts:\s*(-?\d+)\s+pts_time:([^\s]+)',line)
        if frame:
            latest={'output_frame0':int(frame[1]),'pts':int(frame[2]),'relative_pts_time_s':float(frame[3])};all_frames.append(latest)
        if re.search(r'error while decoding|corrupt|invalid NAL|Error while decoding|Invalid data found',line,re.I):
            errors.append({'log_line1':index+1,'message':line,'latest_prior_showinfo':latest,'context_lines':lines[max(0,index-2):min(len(lines),index+4)]})
    result={'status':'STRICT_DECODE_DIAGNOSIS_COMPLETE','job_id':os.environ['SLURM_JOB_ID'],'source_sha256':manifest['source_sha256'],
            'ffmpeg_exit_code':proc.returncode,'command':command,'strict_decode_passed':proc.returncode==0,
            'showinfo_frames_before_stop':len(all_frames),'last_showinfo':all_frames[-1] if all_frames else None,
            'decoder_error_records':errors,'log_bytes':log.stat().st_size,'log_sha256':hashlib.sha256(log.read_bytes()).hexdigest(),
            'temporal_location_is_decoder_context_not_guaranteed_exact_damaged_packet':True,
            'new_model_predictions':0,'GT_available':False,'whole_goal_complete':False}
    (out/'summary.json').write_text(json.dumps(result,indent=2))
    import tarfile
    archive=ROOT/'decode_diagnosis_delivery.tar.gz'
    with tarfile.open(archive,'w:gz') as t:
        for f in out.iterdir():t.add(f,arcname=f.relative_to(ROOT))
    print(json.dumps({k:v for k,v in result.items() if k not in ['command','decoder_error_records']}),flush=True)
    print(json.dumps({'errors':errors[:8],'archive_bytes':archive.stat().st_size,'archive_sha256':hashlib.sha256(archive.read_bytes()).hexdigest()}),flush=True)
    assert errors or proc.returncode==0,'Strict decoder failed for a reason other than observed source corruption'
if __name__=='__main__':main()
