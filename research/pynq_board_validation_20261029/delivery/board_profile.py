"""One bounded profile/process, durable stage and per-sample evidence."""
from pathlib import Path
from datetime import datetime,timezone
import argparse,json,os,sys,time,hashlib,fcntl,traceback,resource
os.environ['XILINX_XRT']='/usr';os.environ['OMP_NUM_THREADS']='2';os.environ['OPENBLAS_NUM_THREADS']='2';sys.dont_write_bytecode=True
import cv2,numpy as np
from pynq import Overlay,PL,Clocks
ROOT=Path(__file__).resolve().parent
O8=Path('/home/xilinx/jupyter_notebooks/yolo26_optimization_8');O6=Path('/home/xilinx/jupyter_notebooks/yolo26_optimization_6')
sys.path[:0]=[str(O8),str(O8/'runtime_fast')]
from native_graph import NativeGraph
from device_initialize import initialize
from verify_release import verify
from board_runtime import preprocess,decode
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,value):
    p=Path(p);partial=p.with_name(p.name+'.partial')
    with partial.open('w') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    partial.replace(p);fd=os.open(str(p.parent),os.O_DIRECTORY);os.fsync(fd);os.close(fd)
def mem():
    return {line.split(':')[0]:int(line.split()[1]) for line in Path('/proc/meminfo').read_text().splitlines() if line.split(':')[0] in ['MemAvailable','CmaFree','SwapFree']}
def stats(a):
    a=np.asarray(a,float);return {'samples':len(a),'mean_ms':float(a.mean()),'p50_ms':float(np.median(a)),
    'p95_ms':float(np.percentile(a,95)),'maximum_ms':float(a.max()),'fps_from_mean':float(1000/a.mean()),'above200ms':int((a>200).sum())}
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--size',type=int,choices=[192,256,320],required=True)
    parser.add_argument('--run',required=True);parser.add_argument('--probe',action='store_true');args=parser.parse_args()
    assert args.run.replace('_','').isalnum();out=ROOT/args.run;out.mkdir(exist_ok=False);cv2.setNumThreads(1)
    p=json.loads((ROOT/'protocol.json').read_text());original=Path(p['source_root']);inputs=p['source_images']
    assert len(inputs)==12 and p['sizes']==[192,256,320] and args.size in p['sizes']
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip();assert boot==p['recovered_boot_id']
    record={'status':'STARTING','board_UTC_may_be_wrong':datetime.now(timezone.utc).isoformat(),'boot_id':boot,'PID':os.getpid(),
       'process_start_ticks':Path('/proc/self/stat').read_text().split()[21],'protocol_sha256':sha(ROOT/'protocol.json'),
       'size':args.size,'probe_only':args.probe,'engine':'O8resident' if args.size in [192,256] else 'O6legacy',
       'pre_memory_kib':mem(),'PL_before':PL.bitfile_name,'stages':[],'rows':[],'warmups':[],
       'current_cow_finetuned_checkpoint_loaded':False,'background_identity_active':False,'camera_active':False,
       'count_or_identity_accuracy_claimed':False,'source_photos_from_single_development_clip':True,'new_training_updates':0}
    g=executor=backend=None;locked=None;failure=None
    def stage(name,**extra):
        record['stages'].append({'stage':name,'monotonic_ns':time.monotonic_ns(),'memory_kib':mem(),**extra})
        write(out/'progress.json',{'status':'RUNNING','stage':name,'PID':os.getpid(),'boot_id':boot,'completed_samples':len(record['rows']),'memory_kib':mem()})
        write(out/'record.json',record);print(json.dumps({'stage':name,'size':args.size,'completed_samples':len(record['rows'])}),flush=True)
    write(out/'started.json',record);stage('before_input_hashes')
    try:
        for row in inputs:assert sha(original/row['file'])==row['sha256']
        for row in p['runtime_files']:assert sha(row['path'])==row['sha256']
        assert sha(O8/'hardware/accepted/optimization_8_resident.bit')==p['O8_bit_sha256']
        assert sha(O8/'hardware/accepted/optimization_8_resident.hwh')==p['O8_hwh_sha256']
        stage('before_release_verification');record['release_check']=verify(O8)
        locked=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('a')
        fcntl.flock(locked,fcntl.LOCK_EX|fcntl.LOCK_NB);stage('exclusive_accelerator_lock_acquired')
        size=args.size
        if size in [192,256]:
            bit=O8/'hardware/accepted/optimization_8_resident.bit';stage('before_O8_firmware_load_or_attach')
            if not PL.bitfile_name or sha(PL.bitfile_name)!=p['O8_bit_sha256']:Overlay(str(bit));record['firmware_programmed']=True
            else:record['firmware_programmed']=False
            stage('O8_loaded_before_DMA_initialization',PL_bitfile=PL.bitfile_name)
            record['device_initialization']=initialize(O8);stage('DMA_initialization_complete_before_graph')
            selected=json.loads((O8/'selected_candidates.json').read_text())[str(size)]
            g=NativeGraph(size,options=selected['options'],plan=selected['plan'],firmware_manifest='hardware/accepted/firmware_manifest.json')
            record['selected_candidate']=selected;record['graph_sha256']=sha(O8/('program_r'+str(size))/'graph.bin')
            record['graph_metadata_sha256']=sha(O8/('program_r'+str(size))/'program.json');record['engine_memory']=g.memory()
            def infer(image):
                begin=time.perf_counter_ns();raw=g.run_image(image).copy();middle=time.perf_counter_ns();boxes=decode(raw,image.shape,threshold=.2,size=size);end=time.perf_counter_ns()
                return raw,boxes,{'detector_e2e_ms':(end-begin)/1e6,'graph_and_preprocess_copy_ms':(middle-begin)/1e6,
                'decode_ms':(end-middle)/1e6,'python_preprocess_ms':g.last_python_preprocess_ms,'native_timers':g.timers.tolist(),'hardware_status':g.status()}
        else:
            for name in ['queue_conv','queue_device','native_ops','hybrid_executor','integer_graph','fixed_point']:sys.modules.pop(name,None)
            sys.path.insert(0,str(O6/'runtime'));from native_ops import NativeOps
            from hybrid_executor import YOLOHybridExecutor
            from queue_conv import QueueConv
            fm=json.loads((O6/'runtime/queue_overlay_manifest.json').read_text())
            for ext in ['bit','hwh']:assert sha(O6/'runtime'/('optimization_5_exact.'+ext))==fm[ext]['sha256']
            stage('before_O6_legacy_firmware_load');Overlay(str(O6/'runtime/optimization_5_exact.bit'));record['firmware_programmed']=True
            stage('O6_loaded_before_graph');native=NativeOps(O6/'runtime/native_queue.so');model=O6/'r320/model'
            backend=QueueConv(model,native);executor=YOLOHybridExecutor(model,backend,native,quantization_mode='fixed',fuse_activation=True,integer_routes=True)
            executor.enable_optimization('combined');record['graph_sha256']=sha(model/'packed_weights.npz');record['graph_metadata_sha256']=sha(model/'graph.json')
            def infer(image):
                begin=time.perf_counter_ns();x=preprocess(image,size);first=time.perf_counter_ns();raw=executor.run(x).copy();middle=time.perf_counter_ns();boxes=decode(raw,image.shape,threshold=.2,size=size);end=time.perf_counter_ns()
                return raw,boxes,{'detector_e2e_ms':(end-begin)/1e6,'graph_and_preprocess_copy_ms':(middle-begin)/1e6,
                'decode_ms':(end-middle)/1e6,'python_preprocess_ms':(first-begin)/1e6,'native_timers':None,'hardware_status':backend.core.status()}
        stage('graph_created_before_first_inference')
        warm=0 if args.probe else p['warmups'];total=1 if args.probe else 32
        first=cv2.imread(str(original/inputs[0]['file']));assert first is not None;first=np.rot90(first,k=-1).copy()
        for i in range(warm):
            stage('before_warmup_'+str(i));raw,boxes,detail=infer(first);assert raw.shape==(1,300,6) and np.isfinite(raw).all()
            record['warmups'].append(detail);stage('warmup_'+str(i)+'_complete')
        repeated=None;repeat_delta=0.
        for index in range(total):
            source=inputs[index] if index<12 else inputs[9];stage('before_sample_'+str(index))
            start=time.perf_counter_ns();image=cv2.imread(str(original/source['file']));read_end=time.perf_counter_ns();assert image.shape==(1440,2560,3)
            image=np.rot90(image,k=-1).copy();rotate_end=time.perf_counter_ns();raw,boxes,detail=infer(image)
            assert raw.shape==(1,300,6) and raw.dtype==np.float32 and np.isfinite(raw).all()
            status=detail['hardware_status'];assert status['error']=='0x0' and all(int(status[k],16)&2 for k in ['MM2S','S2MM'])
            if index>=12:
                if repeated is None:repeated=raw.copy()
                else:repeat_delta=max(repeat_delta,float(np.max(np.abs(raw-repeated))));assert np.array_equal(raw,repeated)
            file=out/('raw_'+str(index).zfill(2)+'.npy')
            with file.open('xb') as f:np.save(f,raw);f.flush();os.fsync(f.fileno())
            row={'index':index,'query_id':source['query_id'],'source_frame0':source['source_frame0'],'source_photo_sha256':source['sha256'],
                'fixed_E010_repeat':index>=12,'photo_read_ms':(read_end-start)/1e6,'native_CW_rotation_ms':(rotate_end-read_end)/1e6,
                'photo_rotation_detector_ms':(rotate_end-start)/1e6+detail['detector_e2e_ms'],'raw_file':file.name,'raw_file_sha256':sha(file),
                'raw_array_sha256':hashlib.sha256(raw.tobytes()).hexdigest(),'cow_boxes_rotated_native':boxes[boxes[:,5]==19].tolist(),
                'all_class_detections':len(boxes),**detail}
            record['rows'].append(row);write(out/('row_'+str(index).zfill(2)+'.json'),row);stage('sample_'+str(index)+'_saved')
        record['repeat_raw_maximum_absolute_delta']=repeat_delta
        record['detector_e2e_statistics']=stats([r['detector_e2e_ms'] for r in record['rows']])
        record['photo_rotation_detector_statistics']=stats([r['photo_rotation_detector_ms'] for r in record['rows']])
        if not args.probe:record['fixed_E010_detector_statistics']=stats([r['detector_e2e_ms'] for r in record['rows'] if r['fixed_E010_repeat']])
        record['status']='PROBE_COMPLETED' if args.probe else 'PROFILE_COMPLETED'
    except BaseException as e:
        failure=e;record.update({'status':'FAILED','error_type':type(e).__name__,'detail':str(e),'traceback':traceback.format_exc()})
    finally:
        close_error=None
        try:
            stage('before_safe_graph_close')
            if g:g.close();g=None
            if executor:executor.close();executor=None
            if backend:backend.close();backend=None
            stage('safe_graph_close_complete')
        except Exception as e:close_error=repr(e);record['status']='CLOSE_FAILED_DEVICE_STATE_UNCERTAIN'
        record['close_error']=close_error;record['memory_after_kib']=mem();record['PL_after']=PL.bitfile_name
        record['peak_process_RSS_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        record['finished_monotonic_ns']=time.monotonic_ns();write(out/'record.json',record)
        if locked:fcntl.flock(locked,fcntl.LOCK_UN);locked.close()
        write(out/'terminal.json',{'status':record['status'],'PID':os.getpid(),'boot_id':boot,'samples':len(record['rows']),
                                  'record_sha256':sha(out/'record.json'),'close_error':close_error})
        print(json.dumps({'terminal':record['status'],'size':args.size,'samples':len(record['rows']),
                          'statistics':record.get('detector_e2e_statistics'),'close_error':close_error}),flush=True)
    if failure or close_error:raise SystemExit(1)
if __name__=='__main__':main()
