"""Bounded board test of existing frozen detector engines on the12 public source captures."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import os,sys,json,hashlib,time,fcntl,resource,traceback
os.environ['OMP_NUM_THREADS']='2';sys.dont_write_bytecode=True
import cv2,numpy as np
from pynq import Overlay,PL,Clocks
ROOT=Path(__file__).resolve().parent;O8=Path('/home/xilinx/jupyter_notebooks/yolo26_optimization_8');O6=Path('/home/xilinx/jupyter_notebooks/yolo26_optimization_6')
sys.path[:0]=[str(O8),str(O8/'runtime_fast')]
from native_graph import NativeGraph
from device_initialize import initialize
from verify_release import verify
from board_runtime import preprocess,decode
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,v):p.write_text(json.dumps(v,indent=2)+'\n')
def mem():
    data={}
    for line in Path('/proc/meminfo').read_text().splitlines():
        k=line.split(':')[0]
        if k in ['MemAvailable','CmaFree','SwapFree']:data[k]=int(line.split()[1])
    return data
def stat(values):
    a=np.asarray(values,float)
    return {'samples':len(a),'mean_ms':float(a.mean()),'p50_ms':float(np.median(a)),'p95_ms':float(np.percentile(a,95)),
    'maximum_ms':float(a.max()),'throughput_fps_from_mean':float(1000/a.mean()),'frames_above200ms':int((a>200).sum())}
def main():
    output=ROOT/'results';output.mkdir(exist_ok=False);progress=output/'progress.json'
    protocol=json.loads((ROOT/'protocol.json').read_text());inputs=protocol['source_images'];assert len(inputs)==12
    for row in inputs:assert sha(ROOT/row['file'])==row['sha256']
    for row in protocol['runtime_files']:assert sha(Path(row['path']))==row['sha256']
    release=verify(O8)
    lockpath=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock');lock=lockpath.open('a')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    record={'status':'RUNNING','created_UTC':datetime.now(timezone.utc).isoformat(),'PID':os.getpid(),
        'protocol_sha256':sha(ROOT/'protocol.json'),'PL_before_bitfile':PL.bitfile_name,'PL_before_IP_names':list(PL.ip_dict),
        'memory_before_kib':mem(),'existing_model_family':'COCO80classYOLO26nquantizeddeploymentassets;notcurrentcowfinetunedcheckpoint',
        'phases':[],'new_training_updates':0,'current_cow12_counting_accuracy_test':False,'background_identity_inference_active':False,
        'camera_capture_active':False,'hardware_lock_acquired':True,'source_frames_independent':False,
        'scope':'Photo replay;FPGA+ARMdetectorpreprocess,inference,decode;capture/read/rotationandserializationreportedseparately.'}
    g=None;backend=None;executor=None;loadedO8=False
    try:
        firmware=json.loads((O8/'hardware/accepted/firmware_manifest.json').read_text())
        for ext in ['bit','hwh']:
            file=O8/'hardware/accepted'/('optimization_8_resident.'+ext);assert sha(file)==firmware[ext]['sha256']
        if not PL.bitfile_name or sha(Path(PL.bitfile_name))!=firmware['bit']['sha256']:
            Overlay(str(O8/'hardware/accepted/optimization_8_resident.bit'));loadedO8=True
        priming=initialize(O8);record['O8_initialization']=priming;record['O8_programmed_for_task']=loadedO8
        for size in [192,256,320]:
            phase_started=time.perf_counter();data=[];raw_rows=[]
            if size in [192,256]:
                selected=json.loads((O8/'selected_candidates.json').read_text())[str(size)]
                g=NativeGraph(size,options=selected['options'],plan=selected['plan'],firmware_manifest='hardware/accepted/firmware_manifest.json')
                engine='O8resident';modelmeta=O8/('program_r'+str(size))/'program.json';graph=O8/('program_r'+str(size))/'graph.bin'
                def infer(image):
                    begin=time.perf_counter();raw=g.run_image(image).copy();boxes=decode(raw,image.shape,threshold=.2,size=size);end=time.perf_counter()
                    return raw,boxes,(end-begin)*1000,g.status(),{'python_preprocess_ms':g.last_python_preprocess_ms,'native_timers':g.timers.tolist()}
            else:
                # The only existing320profile usesO6/O5firmware, kept as a separate engine condition.
                for module in ['queue_conv','queue_device','native_ops','hybrid_executor','integer_graph','fixed_point']:
                    sys.modules.pop(module,None)
                sys.path.insert(0,str(O6/'runtime'));from native_ops import NativeOps
                from hybrid_executor import YOLOHybridExecutor
                from queue_conv import QueueConv
                fm=json.loads((O6/'runtime/queue_overlay_manifest.json').read_text())
                for ext in ['bit','hwh']:assert sha(O6/'runtime'/('optimization_5_exact.'+ext))==fm[ext]['sha256']
                Overlay(str(O6/'runtime/optimization_5_exact.bit'))
                native=NativeOps(O6/'runtime/native_queue.so');model=O6/'r320/model'
                backend=QueueConv(model,native);executor=YOLOHybridExecutor(model,backend,native,quantization_mode='fixed',fuse_activation=True,integer_routes=True);executor.enable_optimization('combined')
                engine='O6legacy';modelmeta=model/'graph.json';graph=model/'packed_weights.npz'
                def infer(image):
                    begin=time.perf_counter();x=preprocess(image,size);raw=executor.run(x).copy();boxes=decode(raw,image.shape,threshold=.2,size=size);end=time.perf_counter()
                    return raw,boxes,(end-begin)*1000,backend.core.status(),{}
            first=cv2.imread(str(ROOT/inputs[0]['file']));assert first is not None;first=np.rot90(first,k=-1).copy()
            for warm in range(2):infer(first)
            first_raw=None;maximum_repeat_delta=0.
            for i in range(32):
                # First12different source events, then20repetitions of the same E010image.
                source=inputs[i] if i<12 else inputs[9]
                read_start=time.perf_counter();image=cv2.imread(str(ROOT/source['file']));assert image.shape==(1440,2560,3)
                read_ms=(time.perf_counter()-read_start)*1000
                rotation_start=time.perf_counter();image=np.rot90(image,k=-1).copy();rotation_ms=(time.perf_counter()-rotation_start)*1000
                raw,boxes,elapsed,status,detail=infer(image);assert raw.shape==(1,300,6) and np.isfinite(raw).all()
                assert status['error']=='0x0' and all(int(status[k],16)&2 for k in ['MM2S','S2MM'])
                cow=boxes[boxes[:,5]==19] if len(boxes) else boxes
                result={'index':i,'query_id':source['query_id'],'repeat_of_E010':i>=12,'photo_read_ms':read_ms,'native_rotation_ms':rotation_ms,
                    'detector_e2e_ms':elapsed,'read_rotation_detector_ms':read_ms+rotation_ms+elapsed,'raw_sha256':hashlib.sha256(raw.tobytes()).hexdigest(),
                    'detected_all_classes':int(len(boxes)),'cow_boxes_on_rotated_source':cow.tolist(),'hardware_status':status,**detail}
                if i>=12:
                    if first_raw is None:first_raw=raw.copy()
                    else:maximum_repeat_delta=max(maximum_repeat_delta,float(np.max(np.abs(first_raw-raw))));assert np.array_equal(first_raw,raw)
                if i<12:np.save(output/(str(size)+'_'+source['query_id']+'_raw.npy'),raw)
                data.append(result)
                save(progress,{'status':'RUNNING','PID':os.getpid(),'size':size,'sample':i+1,'completed_sizes':[r['size'] for r in record['phases']]})
            phase={'size':size,'engine':engine,'measured_samples':len(data),'warmups':2,'model_metadata_path':str(modelmeta),'model_metadata_sha256':sha(modelmeta),
                'graph_or_weight_artifact_path':str(graph),'graph_or_weight_sha256':sha(graph),'source_event_photos':12,'fixed_repeat_images':20,
                'detector_e2e_statistics':stat([r['detector_e2e_ms'] for r in data]),
                'photo_read_rotation_detector_statistics':stat([r['read_rotation_detector_ms'] for r in data]),
                'fixed_E010_detector_statistics':stat([r['detector_e2e_ms'] for r in data if r['repeat_of_E010']]),
                'repeat_raw_maximum_delta':maximum_repeat_delta,'rows':data,
                'source_events_with_atleast_one_cow_prediction':sum(bool(r['cow_boxes_on_rotated_source']) for r in data[:12]),
                'memory_kib':mem(),'phase_wall_s':time.perf_counter()-phase_started}
            record['phases'].append(phase);save(output/('size'+str(size)+'.json'),phase)
            if g:g.close();g=None
            if executor:executor.close();executor=None
            if backend:backend.close();backend=None
            print(json.dumps({'completed_size':size,'engine':engine,'detector':phase['detector_e2e_statistics'],'cow_present_photos':phase['source_events_with_atleast_one_cow_prediction']}),flush=True)
        record['status']='THREE_EXISTING_ENGINE_PROFILES_MEASURED_ON12_COW_CAPTURES_WITH20_FIXED_REPEATS'
    except BaseException as e:
        record['status']='FAILED';record['error_type']=type(e).__name__;record['error']=str(e)[:800];record['traceback']=traceback.format_exc()
        raise
    finally:
        close_error=None
        try:
            if g:g.close()
            if executor:executor.close()
            if backend:backend.close()
        except Exception as e:close_error=repr(e)
        record['close_error']=close_error
        if close_error is None:
            # Restore the newer accepted detector firmware after the legacy320profile.
            try:
                if not PL.bitfile_name or sha(Path(PL.bitfile_name))!=firmware['bit']['sha256']:
                    Overlay(str(O8/'hardware/accepted/optimization_8_resident.bit'))
                record['O8_final_priming']=initialize(O8)
                record['PL_after_bitfile']=PL.bitfile_name;record['PL_after_IP_names']=list(PL.ip_dict);record['final_O8_firmware_sha256']=sha(Path(PL.bitfile_name))
                record['final_firmware_restored_to_O8_not_claimed_equal_unknown_original']=True
            except Exception as e:record['final_firmware_error']=repr(e)
        record['memory_after_kib']=mem();record['peak_process_RSS_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        record['finished_UTC']=datetime.now(timezone.utc).isoformat();save(output/'summary.json',record)
        fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
        save(progress,{'status':record['status'],'PID':os.getpid(),'completed_sizes':[r['size'] for r in record['phases']]})
if __name__=='__main__':main()
