from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
source=ROOT/'tools/board_stream_replay.py';text=source.read_text()
text=text.replace("out=ROOT/'stream_replay'","out=ROOT/'framebank_replay'").replace("ROOT/'stream_protocol.json'","ROOT/'framebank_protocol.json'")
anchor="boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot==parent['recovered_boot_id']"
assert text.count(anchor)==1
text=text.replace(anchor,anchor+'''
    for runtime in parent['runtime_files']:assert sha(runtime['path'])==runtime['sha256']
    framebank={}
    for source in inputs:
        image=cv2.imread(str(old/source['file']),cv2.IMREAD_REDUCED_COLOR_8);assert image.shape==(180,320,3)
        framebank[source['query_id']]=image
    bankfile=out/'actual_lowres_inputs.npz';np.savez_compressed(bankfile,**framebank)
    framebank_record={'actual_lowres_inputs_file':bankfile.name,'file_sha256':sha(bankfile),'total_BGR_bytes':sum(im.nbytes for im in framebank.values()),
                     'native_BGR_pixel_sha256':{name:hashlib.sha256(im.tobytes()).hexdigest() for name,im in framebank.items()}}
''')
anchor="'protocol_sha256':sha(ROOT/'framebank_protocol.json'),'cases':[]"
assert anchor in text;text=text.replace(anchor,"'protocol_sha256':sha(ROOT/'framebank_protocol.json'),'framebank':framebank_record,'cases':[]")
anchor="first=cv2.imread(str(old/inputs[0]['file']),cv2.IMREAD_REDUCED_COLOR_8);assert first.shape==(180,320,3)"
assert text.count(anchor)==1;text=text.replace(anchor,"first=framebank[inputs[0]['query_id']].copy();assert first.shape==(180,320,3)")
anchor="image=cv2.imread(str(old/source['file']),cv2.IMREAD_REDUCED_COLOR_8);read_end=time.monotonic_ns();assert image.shape==(180,320,3)"
assert text.count(anchor)==1;text=text.replace(anchor,"image=framebank[source['query_id']].copy();read_end=time.monotonic_ns();assert image.shape==(180,320,3)")
text=text.replace("'photo_read_ms'","'lowres_input_copy_ms'").replace('frontend_read_rotation_detector_ms','frontend_copy_rotation_detector_ms').replace('input_native_BRG_dimensions_WH','input_native_BGR_dimensions_WH')
target=ROOT/'tools/board_framebank_replay.py';assert not target.exists();target.write_text(text,newline='\n')
p=json.loads((ROOT/'protocol/stream_v1.json').read_text());p.update({'status':'FROZEN_AFTER_JPEG_STREAM_DIAGNOSIS_BEFORE_SAME_PIXEL_FRAMEBANK_CONTROL',
 'created_host_UTC':datetime.now(timezone.utc).isoformat(),'parent_stream_protocol_sha256':sha(ROOT/'protocol/stream_v1.json'),
 'source_stream_archive_sha256':sha(ROOT/'stream_replay_complete.tar.gz'),
 'decode':'Decodeall12sourcephotosonceonboardwithsameIMREAD_REDUCED_COLOR_8beforeclock;withinclockcopylowresBGR,cv2rotate,actualnetworkanddecode.',
 'new_input_condition':'SamepixelsaspreviousreducedJPEGcase;storagefrontendreplacedwith2MBinputframebank;eachprocessedslotstillactualNNforward,notcachedoutputs.',
 'timing_start':'BeforecopyofalreadyavailablelowresolutionBGRframe','timing_end':'AfteractualFPGA/ARMnetwork,copyrawanddecode',
 'match_gate':'AllframebankrotatedBGRhashesandrawoutputsforcommonqueryIDscomparedtopreviousactualJPEGstream;exactrequired.',
 'physical_camera_validation':False,'frontend_image_acquisition_or_JPEG_decoder_time_included':False,'background_identity_active':False,
 'script_sha256':sha(target),'whole_goal_complete':False})
file=ROOT/'protocol/framebank_v1.json';assert not file.exists();file.write_text(json.dumps(p,indent=2)+'\n')
template=(ROOT/'tools/launch_stream_replay.sh').read_text()
template=template.replace("terminal=json.loads((root/'input_probe/terminal.json').read_text());assert terminal['status']=='BOARD_INPUT12_NATIVE_AND36_LETTERBOX_CONDITIONS_COMPLETE'",
                          "terminal=json.loads((root/'stream_replay/terminal.json').read_text());assert terminal['status']=='ALL3_REAL_BOARD_PERIODIC_LOWRES_REPLAYS_COMPLETED'")
template=template.replace("'stream_replay'","'framebank_replay'").replace('launch_stream_replay','launch_framebank_replay').replace('stream_replay.log','framebank_replay.log').replace('board_stream_replay.py','board_framebank_replay.py')
template=template.replace("root/'stream_protocol.json'","root/'framebank_protocol.json'").replace('b339710040e4f20e1813f50e0c611660f4928c973c7e9115e8f12503e0ce6415',sha(file))
launch=ROOT/'tools/launch_framebank_replay.sh';assert not launch.exists();launch.write_text(template,newline='\n')
status=ROOT/'tools/status_framebank_replay.sh';assert not status.exists();status.write_text((ROOT/'tools/status_stream_replay.sh').read_text().replace('stream_replay','framebank_replay'),newline='\n')
print(json.dumps({'protocol_sha256':sha(file),'script_sha256':sha(target),'same_NN_inference_math':True,'same_lowres_input_pixels_required':True}))
