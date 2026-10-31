from pathlib import Path
from datetime import datetime,timezone
import json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p={'status':'FROZEN_BEFORE_LOWRES_BOARD_STREAM_REPLAY','created_host_UTC':datetime.now(timezone.utc).isoformat(),
 'parent_profile_protocol_sha256':sha(ROOT/'protocol/board_v2.json'),'profile_verification_sha256':sha(ROOT/'results/independent_profile_verification.json'),
 'sizes':[192,256,320],'engines':{'192':'O8resident','256':'O8resident','320':'O6legacy'},
 'source_photos':12,'source_order':'Cycle12fixedpubliceventphotosbyofferedslotmod12;notnewindependentanimals.',
 'decode':'OpenCVIMREAD_REDUCED_COLOR_8;actualJPEGdecoderproduces320x180BGRfrom2560x1440photo,thenOpenCVnativeCW90.',
 'new_input_condition':'DifferentfromfullJPEGdecode;noexactinputoraccuracytransferclaim;fullresolution32samplecontrolkept.',
 'offered_Hz':5,'period_ns':200000000,'offered_slots':100,'policy':'Latestavailableframe;skipstaleofferedslotswhenprocessingfallsbehind;nosyntheticpredictionfortheskippedslots.',
 'warmups':2,'timing_start':'BeforelowresolutionJPEGread','timing_end':'AfteractualFPGA/ARMnetwork,copyrawanddecode',
 'save_rule':'Keepalltimesandrawarrays;durablecheckpointaftereach10processedframes;arrivalclockcontinuesduringlogging.',
 'foreground_tracking_active':False,'background_identity_active':False,'camera_hardware_active':False,
 'report':['processed','skipped','processed_frames_above200ms','deadline_misses','p50','p95','maximum','observation_window_fps'],
 'pass_statement':'Onlythislowresphotoreplayfrontendconditioncanbemeasured;wholepipeline5FPSremainstoverify.',
 'count_or_identity_accuracy_admitted':False,'whole_goal_complete':False}
file=ROOT/'protocol/stream_v1.json';assert not file.exists();file.write_text(json.dumps(p,indent=2)+'\n');print(sha(file))
