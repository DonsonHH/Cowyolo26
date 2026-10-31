"""Check parsed packet boundaries/timing against ffprobe on a local known MP4."""
from pathlib import Path
import hashlib,json,struct,subprocess
from sample_index import index

ROOT=Path(__file__).resolve().parents[1]
video=ROOT.parent/'counting_eval_20261026/previews/forward_generic.mp4'
with video.open('rb') as f:
    while True:
        at=f.tell();head=f.read(8);assert len(head)==8
        size,kind=struct.unpack('>I4s',head);hs=8
        if size==1:size=struct.unpack('>Q',f.read(8))[0];hs=16
        if kind==b'moov':f.seek(at);moov=f.read(size);break
        assert size>=hs;f.seek(at+size)
parsed=index(moov)
probe=subprocess.run(['ffprobe','-v','error','-select_streams','v:0','-show_packets','-show_streams','-of','json',str(video)],capture_output=True,check=True)
observed=json.loads(probe.stdout);packets=observed['packets'];assert len(packets)==len(parsed['samples'])
differences=set()
for packet,s in zip(packets,parsed['samples']):
    assert int(packet['pos'])==s['offset'] and int(packet['size'])==s['size']
    assert int(packet['duration'])==s['duration_ticks']
    differences.add((int(packet['pts'])-s['pts_ticks'],int(packet['dts'])-s['dts_ticks']))
    assert ('K' in packet['flags'])==s['sync']
assert len(differences)==1
stream=observed['streams'][0]
assert (stream['width'],stream['height'])==(parsed['width'],parsed['height'])
assert stream['time_base']==f"1/{parsed['timescale']}"
result={'status':'ALL_VIDEO_PACKET_BOUNDARIES_TIMESTAMPS_DURATIONS_AND_SYNC_FLAGS_MATCH_FFPROBE',
        'control_video':str(video),'sha256':hashlib.sha256(video.read_bytes()).hexdigest(),
        'samples_checked':len(packets),'dimensions':[parsed['width'],parsed['height']],
        'timestamp_differences_ffprobe_minus_raw_table_ticks':sorted(differences),
        'constant_shift_can_include_edit_list':'No absolute wall clock asserted; sample display order and packet spans checked.',
        'ffprobe_version':subprocess.run(['ffprobe','-version'],capture_output=True,check=True).stdout.decode().splitlines()[0]}
out=ROOT/'results/index_control.json';assert not out.exists();out.write_text(json.dumps(result,indent=2),encoding='utf-8')
print(json.dumps(result))
