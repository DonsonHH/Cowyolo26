"""Read packet timestamps only; distinguish clip-relative frame time from container origin."""
from pathlib import Path
from collections import Counter
import hashlib,json,subprocess
ROOT=Path(__file__).resolve().parents[1]
def main():
    manifest=json.loads((ROOT/'input/video_manifest.json').read_text(encoding='utf-8'));src=Path(manifest['local_path'])
    assert hashlib.sha256(src.read_bytes()).hexdigest()==manifest['source_sha256']
    command=['ffprobe','-v','error','-select_streams','v:0','-show_packets','-show_entries','packet=pts,dts,duration,pos,size,flags',
             '-show_entries','stream=time_base,r_frame_rate,avg_frame_rate,start_pts,start_time,duration','-of','json',str(src)]
    proc=subprocess.run(command,capture_output=True,check=True);assert not proc.stderr
    out=ROOT/'evidence';raw=out/'source_packet_clock.json';assert not raw.exists();raw.write_bytes(proc.stdout)
    data=json.loads(proc.stdout);packets=data['packets'];stream=data['streams'][0];scale=int(stream['time_base'].split('/')[1]);assert stream['time_base']==f'1/{scale}'
    pts=[int(r['pts']) for r in packets];dts=[int(r['dts']) for r in packets];dur=[int(r['duration']) for r in packets if 'duration' in r]
    display=sorted(pts);assert len(display)==len(set(display));delta=Counter(b-a for a,b in zip(display,display[1:]))
    expected=scale//25;assert expected*25==scale
    maximum=max(abs((value-display[0])/scale-i/25) for i,value in enumerate(display))
    result={'status':'NATIVE_VIDEO_PACKET_CLOCK_AUDITED_WITHOUT_MODEL_OR_PIXEL_DECODE','packets':len(packets),'time_base':stream['time_base'],
            'container_start_pts':min(pts),'container_start_time_s':min(pts)/scale,'first_relative_frame_time_s':0,
            'display_tick_delta_histogram':dict(sorted(delta.items())),'packet_duration_histogram':dict(Counter(dur)),
            'expected_25fps_delta_ticks':expected,'maximum_relative_frame_clock_deviation_s':maximum,
            'uniform_25fps_display_clock':set(delta)=={expected},'PTS_order_equals_decode_order':pts==display,
            'first_last_display_span_s':(display[-1]-display[0])/scale,'raw_packet_metadata_sha256':hashlib.sha256(proc.stdout).hexdigest(),
            'time_reference':'Frame0/25 is clip-relative. Container PTS origin is not treated as farm wall-clock.',
            'new_model_predictions':0,'whole_goal_complete':False}
    target=out/'source_packet_clock_summary.json';assert not target.exists();target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)
if __name__=='__main__':main()
