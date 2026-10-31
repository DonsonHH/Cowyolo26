from pathlib import Path,PurePosixPath
import hashlib,json,tarfile
ROOT=Path(__file__).resolve().parents[1]
p=ROOT/'decode_diagnosis_delivery.tar.gz';assert p.stat().st_size==559697 and hashlib.sha256(p.read_bytes()).hexdigest()=='5d51c47fb864ef305abb462f4b75848a4a0c39a85ec40c026e0a80e23ea0f87d'
out=ROOT/'decode_diagnosis_delivery'
if not out.exists():
    out.mkdir()
    with tarfile.open(p) as t:
        for m in t.getmembers():
            n=PurePosixPath(m.name);assert m.isfile() and not n.is_absolute() and '..' not in n.parts
        t.extractall(out,filter='data')
folder=out/'results/decode_diagnosis';s=json.loads((folder/'summary.json').read_text(encoding='utf-8'));log=folder/'strict_ffmpeg.log'
assert hashlib.sha256(log.read_bytes()).hexdigest()==s['log_sha256']
assert s['strict_decode_passed'] is False and s['ffmpeg_exit_code']!=0
pts=json.loads((ROOT/'evidence/source_packet_clock.json').read_text(encoding='utf-8'))['packets']
keys=[i for i,r in enumerate(pts) if 'K' in r['flags']]
first=next(r for r in s['decoder_error_records'] if 'error while decoding' in r['message'].lower() and r['latest_prior_showinfo'] is not None)
near=first['latest_prior_showinfo']['output_frame0']
prior=max(k for k in keys if k<=near);following=next((k for k in keys if k>near),len(pts))
result={'status':'STRICT_SOURCE_FAILURE_RETAINED_AND_PACKET_CONTEXT_BOUND','strict_ffmpeg_exit':s['ffmpeg_exit_code'],
        'showinfo_frames_before_stop':s['showinfo_frames_before_stop'],'first_error':first,
        'source_packets':len(pts),'preceding_key_packet_index0':prior,'following_key_packet_index0':following,
        'last_key_packet_index0':keys[-1],'last_packet_end_byte':int(pts[-1]['pos'])+int(pts[-1]['size']),
        'conservative_quarantine_frames0_inclusive':[prior,len(pts)-1],
        'quarantine_reason':'Strict error occurs at the terminal packet group; conservatively retain from the prior keyframe through EOF. This bound is not exact damaged-frame ground truth.',
        'exact_corrupt_frame_certified':False,'full_video_clean_bitstream':False,'new_model_predictions':0,'whole_goal_complete':False}
dest=ROOT/'evidence/source_decode_limit.json';assert not dest.exists();dest.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps({k:v for k,v in result.items() if k!='first_error'}));print(json.dumps(first))
