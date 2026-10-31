"""Actual hardware under periodic5Hz replay; camera/identity/tracking absent."""
from pathlib import Path
from datetime import datetime,timezone
import json,os,sys,time,hashlib,fcntl,traceback
os.environ['XILINX_XRT']='/usr';os.environ['OMP_NUM_THREADS']='2';os.environ['OPENBLAS_NUM_THREADS']='2'
sys.dont_write_bytecode=True
import cv2,numpy as np
from pynq import Overlay,PL,Clocks
ROOT=Path(__file__).resolve().parent;O8=Path('/home/xilinx/jupyter_notebooks/yolo26_optimization_8');O6=Path('/home/xilinx/jupyter_notebooks/yolo26_optimization_6')
sys.path[:0]=[str(O8),str(O8/'runtime_fast')]
from native_graph import NativeGraph
from device_initialize import initialize
from board_runtime import preprocess,decode
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,value):
    temp=p.with_name(p.name+'.partial')
    with temp.open('w') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    temp.replace(p)
def stats(a):
    a=np.asarray(a,float);return {'samples':len(a),'mean_ms':float(a.mean()),'p50_ms':float(np.median(a)),
     'p95_ms':float(np.percentile(a,95)),'maximum_ms':float(a.max()),'above200ms':int((a>200).sum())}
def main():
    out=ROOT/'stream_replay';out.mkdir(exist_ok=False);cv2.setNumThreads(1)
    p=json.loads((ROOT/'stream_protocol.json').read_text());parent=json.loads((ROOT/'protocol.json').read_text())
    assert sha(ROOT/'protocol.json')==p['parent_profile_protocol_sha256'] and p['offered_slots']==100 and p['period_ns']==200000000
    assert p['sizes']==[192,256,320] and p['warmups']==2
    old=Path(parent['source_root']);inputs=parent['source_images']
    for row in inputs:assert sha(old/row['file'])==row['sha256']
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot==parent['recovered_boot_id']
    record={'status':'RUNNING','PID':os.getpid(),'boot_id':boot,'board_UTC_may_be_wrong':datetime.now(timezone.utc).isoformat(),
      'protocol_sha256':sha(ROOT/'stream_protocol.json'),'cases':[],'new_training_updates':0,'current_cow_finetuned_weights_loaded':False,
      'background_identity_active':False,'foreground_tracking_active':False,'camera_hardware_active':False,'whole_goal_complete':False}
    g=executor=backend=None;lock=None;failure=None;close_error=None;totalforwards=0
    def progress(stage,**extra):
        write(out/'progress.json',{'status':record['status'],'stage':stage,'PID':os.getpid(),'boot_id':boot,'total_image_forwards':totalforwards,**extra})
        write(out/'record.json',record);print(json.dumps({'stage':stage,'image_forwards':totalforwards,**extra}),flush=True)
    try:
        lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        for size in p['sizes']:
            folder=out/('s'+str(size));folder.mkdir(exist_ok=False)
            case={'size':size,'engine':p['engines'][str(size)],'rows':[],'warmups':[],'skipped_slots':[]};record['cases'].append(case)
            progress('before_graph',size=size)
            if size in [192,256]:
                bit=O8/'hardware/accepted/optimization_8_resident.bit';assert sha(bit)==parent['O8_bit_sha256']
                if not PL.bitfile_name or sha(PL.bitfile_name)!=parent['O8_bit_sha256']:Overlay(str(bit))
                case['initialization']=initialize(O8);selected=json.loads((O8/'selected_candidates.json').read_text())[str(size)]
                g=NativeGraph(size,options=selected['options'],plan=selected['plan'],firmware_manifest='hardware/accepted/firmware_manifest.json')
                def infer(image):
                    start=time.perf_counter_ns();raw=g.run_image(image).copy();middle=time.perf_counter_ns();boxes=decode(raw,image.shape,threshold=.2,size=size);end=time.perf_counter_ns()
                    return raw,boxes,{'graph_and_preprocess_copy_ms':(middle-start)/1e6,'decode_ms':(end-middle)/1e6,'hardware_status':g.status()}
            else:
                for name in ['queue_conv','queue_device','native_ops','hybrid_executor','integer_graph','fixed_point']:sys.modules.pop(name,None)
                sys.path.insert(0,str(O6/'runtime'));from native_ops import NativeOps
                from hybrid_executor import YOLOHybridExecutor
                from queue_conv import QueueConv
                manifest=json.loads((O6/'runtime/queue_overlay_manifest.json').read_text())
                bit=O6/'runtime/optimization_5_exact.bit';assert sha(bit)==manifest['bit']['sha256']
                Overlay(str(bit));native=NativeOps(O6/'runtime/native_queue.so');model=O6/'r320/model'
                backend=QueueConv(model,native);executor=YOLOHybridExecutor(model,backend,native,quantization_mode='fixed',fuse_activation=True,integer_routes=True);executor.enable_optimization('combined')
                def infer(image):
                    start=time.perf_counter_ns();x=preprocess(image,size);raw=executor.run(x).copy();middle=time.perf_counter_ns();boxes=decode(raw,image.shape,threshold=.2,size=size);end=time.perf_counter_ns()
                    return raw,boxes,{'graph_and_preprocess_copy_ms':(middle-start)/1e6,'decode_ms':(end-middle)/1e6,'hardware_status':backend.core.status()}
            first=cv2.imread(str(old/inputs[0]['file']),cv2.IMREAD_REDUCED_COLOR_8);assert first.shape==(180,320,3)
            first=cv2.rotate(first,cv2.ROTATE_90_CLOCKWISE)
            for i in range(p['warmups']):
                begin=time.perf_counter_ns();raw,boxes,detail=infer(first);totalforwards+=1
                assert raw.shape==(1,300,6) and np.isfinite(raw).all();case['warmups'].append({'elapsed_ms':(time.perf_counter_ns()-begin)/1e6,**detail})
            progress('before_periodic_clock',size=size)
            epoch=time.monotonic_ns();slot=0;period=p['period_ns'];offered=p['offered_slots']
            while slot<offered:
                now=time.monotonic_ns();latest=(now-epoch)//period
                if latest>=offered:case['skipped_slots'].extend(range(slot,offered));break
                if latest>slot:case['skipped_slots'].extend(range(slot,int(latest)));slot=int(latest)
                release=epoch+slot*period
                if now<release:time.sleep((release-now)/1e9)
                source=inputs[slot%12];begin=time.monotonic_ns()
                image=cv2.imread(str(old/source['file']),cv2.IMREAD_REDUCED_COLOR_8);read_end=time.monotonic_ns();assert image.shape==(180,320,3)
                image=cv2.rotate(image,cv2.ROTATE_90_CLOCKWISE);rotate_end=time.monotonic_ns();raw,boxes,detail=infer(image);finish=time.monotonic_ns();totalforwards+=1
                assert raw.shape==(1,300,6) and np.isfinite(raw).all();status=detail['hardware_status']
                assert status['error']=='0x0' and all(int(status[k],16)&2 for k in ['MM2S','S2MM'])
                filename='slot'+str(slot).zfill(3)+'_raw.npy';np.save(folder/filename,raw)
                row={'offered_slot':slot,'query_id':source['query_id'],'source_frame0':source['source_frame0'],'source_photo_sha256':source['sha256'],
                    'input_native_BRG_dimensions_WH':[320,180],'release_ns':release,'start_ns':begin,'finish_ns':finish,'deadline_ns':release+period,
                    'start_delay_ms':(begin-release)/1e6,'capture_age_since_offered_release_ms':(finish-release)/1e6,
                    'deadline_miss':finish>release+period,'photo_read_ms':(read_end-begin)/1e6,'native_CW_rotation_ms':(rotate_end-read_end)/1e6,
                    'frontend_read_rotation_detector_ms':(finish-begin)/1e6,'actual_input_rotated_BGR_sha256':hashlib.sha256(image.tobytes()).hexdigest(),
                    'raw_file':filename,'raw_file_sha256':sha(folder/filename),'raw_array_sha256':hashlib.sha256(raw.tobytes()).hexdigest(),
                    'cow_boxes_rotated_reduced':boxes[boxes[:,5]==19].tolist(),'all_class_detections':len(boxes),**detail}
                case['rows'].append(row);slot+=1
                if len(case['rows'])%10==0:progress('periodic_progress',size=size,processed=len(case['rows']),skipped=len(case['skipped_slots']))
            case['epoch_monotonic_ns']=epoch;case['observed_end_monotonic_ns']=time.monotonic_ns()
            case['observation_window_s']=max(offered*period,case['observed_end_monotonic_ns']-epoch)/1e9
            case['processed']=len(case['rows']);case['skipped']=len(case['skipped_slots']);case['offered']=offered
            assert sorted([r['offered_slot'] for r in case['rows']]+case['skipped_slots'])==list(range(offered))
            case['deadline_misses']=sum(r['deadline_miss'] for r in case['rows']);case['on_time']=case['processed']-case['deadline_misses']
            case['observed_processed_fps']=case['processed']/case['observation_window_s']
            case['frontend_statistics']=stats([r['frontend_read_rotation_detector_ms'] for r in case['rows']])
            case['age_statistics']=stats([r['capture_age_since_offered_release_ms'] for r in case['rows']])
            if g:g.close();g=None
            if executor:executor.close();executor=None
            if backend:backend.close();backend=None
            case['safe_close_complete']=True;write(folder/'summary.json',case);progress('case_complete',size=size,processed=case['processed'],skipped=case['skipped'],deadline_misses=case['deadline_misses'])
        record['status']='ALL3_REAL_BOARD_PERIODIC_LOWRES_REPLAYS_COMPLETED'
    except BaseException as e:
        failure=e;record.update({'status':'FAILED','error_type':type(e).__name__,'detail':str(e),'traceback':traceback.format_exc()})
    finally:
        try:
            if g:g.close();g=None
            if executor:executor.close();executor=None
            if backend:backend.close();backend=None
        except Exception as e:close_error=repr(e);record['status']='CLOSE_FAILED_DEVICE_STATE_UNCERTAIN'
        record['close_error']=close_error
        if not close_error:
            try:
                bit=O8/'hardware/accepted/optimization_8_resident.bit'
                if not PL.bitfile_name or sha(PL.bitfile_name)!=parent['O8_bit_sha256']:Overlay(str(bit))
                record['final_known_O8_bit_sha256']=sha(PL.bitfile_name);record['final_PL_bitfile']=PL.bitfile_name
            except Exception as e:record['final_firmware_error']=repr(e);record['status']='FINAL_FIRMWARE_STATE_UNCERTAIN'
        record['total_actual_image_forwards']=totalforwards;record['memory_final']=Path('/proc/meminfo').read_text();progress('terminal')
        os.sync();write(out/'terminal.json',{'status':record['status'],'PID':os.getpid(),'record_sha256':sha(out/'record.json'),'total_actual_image_forwards':totalforwards,'close_error':close_error})
        if lock:fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
    if failure or close_error:raise SystemExit(1)
if __name__=='__main__':main()
