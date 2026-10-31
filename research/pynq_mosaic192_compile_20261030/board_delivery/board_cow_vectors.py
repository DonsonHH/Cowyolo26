"""Actual O8 FPGA/ARM parity on8 train-only vectors; no model or class shortcut."""
from pathlib import Path
from datetime import datetime,timezone
import os,sys,json,time,hashlib,fcntl,traceback
os.environ['XILINX_XRT']='/usr';os.environ['OMP_NUM_THREADS']='2';os.environ['OPENBLAS_NUM_THREADS']='2';sys.dont_write_bytecode=True
import numpy as np,cv2
from pynq import PL
ROOT=Path(__file__).resolve().parent;O8=Path('/home/xilinx/jupyter_notebooks/yolo26_optimization_8');sys.path[:0]=[str(O8),str(O8/'runtime_fast')]
from native_graph import NativeGraph
from device_initialize import initialize
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(path,value):
    temp=path.with_name(path.name+'.partial')
    with temp.open('w') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
    temp.replace(path)
def main():
    out=ROOT/'results';out.mkdir(exist_ok=False);cv2.setNumThreads(1)
    p=json.loads((ROOT/'protocol.json').read_text());assert p['size']==192 and p['class_count']==1 and p['real_video_count_accuracy_claimed'] is False
    for f in p['payload_files']:assert sha(ROOT/f['file'])==f['sha256']
    state={'status':'RUNNING','PID':os.getpid(),'boot_id':Path('/proc/sys/kernel/random/boot_id').read_text().strip(),
       'board_wall_clock_untrusted':datetime.now(timezone.utc).isoformat(),'protocol_sha256':sha(ROOT/'protocol.json'),
       'class_count':1,'model_checkpoint_sha256':p['model_checkpoint_sha256'],'size':192,'scope':'Tensor192->actualFPGA/ARMcompleteO8network->raw;notJPEG/camera/tracker/identity.',
       'rows':[],'warmups':[],'stages':[],'new_training_updates':0,'complete_pipeline5FPS_proven':False,'whole_goal_complete':False}
    graph=lock=None;failure=None;close_error=None
    def stage(name):
        state['stages'].append({'stage':name,'monotonic_ns':time.monotonic_ns()})
        write(out/'progress.json',{'status':state['status'],'stage':name,'PID':os.getpid(),'completed_vectors':len(state['rows'])})
        write(out/'record.json',state);print(json.dumps({'stage':name,'vectors':len(state['rows'])}),flush=True)
    try:
        stage('before_exclusive_lock');lock=Path('/home/xilinx/jupyter_notebooks/yolo26_stage_d/reports/accelerator_job.lock').open('a');fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        assert PL.bitfile_name and sha(PL.bitfile_name)==p['expected_O8_bit_sha256'],'ExpectedO8firmwarenotloaded;donotprogramimplicitly'
        state['PL_bitfile']=PL.bitfile_name;state['device_initialization']=initialize(O8);stage('before_new_cow_graph_create')
        graph=NativeGraph(192,program=str(ROOT/'program'),plan=str(ROOT/'resident_plan/resident_plan.bin'),options=4,
                          firmware_manifest='hardware/accepted/firmware_manifest.json')
        state['graph_memory']=graph.memory();stage('before_cow_warmups')
        first=np.load(ROOT/'vectors/parity_train_0.npz')['input']
        for i in range(2):
            start=time.perf_counter_ns();raw=graph.run(first).copy();elapsed=(time.perf_counter_ns()-start)/1e6
            assert raw.shape==(1,300,6) and np.isfinite(raw).all();state['warmups'].append({'index':i,'tensor_to_raw_ms':elapsed})
        stage('warmups_complete')
        for i in range(8):
            file=ROOT/'vectors'/('parity_train_'+str(i)+'.npz')
            with np.load(file) as a:x=a['input'];reference=a['reference_integer_raw'];cpu=a['native_integer_raw']
            assert x.shape==(1,3,192,192) and x.dtype==np.float32 and np.array_equal(reference,cpu)
            stage('before_vector_'+str(i));start=time.perf_counter_ns();actual=graph.run(x).copy();elapsed=(time.perf_counter_ns()-start)/1e6
            assert actual.shape==(1,300,6) and actual.dtype==np.float32 and np.isfinite(actual).all()
            box_error=float(np.max(np.abs(actual[:,:,:4]-reference[:,:,:4])));score_error=float(np.max(np.abs(actual[:,:,4]-reference[:,:,4])))
            classes_exact=bool(np.array_equal(actual[:,:,5],reference[:,:,5]));status=graph.status()
            assert status['error']=='0x0' and all(int(status[k],16)&2 for k in ['MM2S','S2MM'])
            rawfile=out/('vector_'+str(i)+'_raw.npy')
            with rawfile.open('xb') as f:np.save(f,actual);f.flush();os.fsync(f.fileno())
            passed=box_error<=p['parity_gate']['box_max_absolute_pixels'] and score_error<=p['parity_gate']['score_max_absolute'] and classes_exact
            row={'index':i,'input_array_sha256':hashlib.sha256(x.tobytes()).hexdigest(),'raw_file':rawfile.name,'raw_file_sha256':sha(rawfile),
                 'raw_array_sha256':hashlib.sha256(actual.tobytes()).hexdigest(),'reference_raw_sha256':hashlib.sha256(reference.tobytes()).hexdigest(),
                 'maximum_box_error':box_error,'maximum_score_error':score_error,'classes_exact':classes_exact,'passes_gate':passed,
                 'tensor_to_raw_ms':elapsed,'detections_above_conf02':int((actual[0,:,4]>=.2).sum()),'hardware_status':status}
            state['rows'].append(row);write(out/('vector_'+str(i)+'.json'),row);stage('vector_'+str(i)+'_saved')
            if not passed:raise RuntimeError('ActualO8cowvectorparitygatefailed;preserverawanddiagnosebeforecontinuing')
        state['status']='ALL8_ACTUAL_PYNQ_COW1_CLASS_O8_VECTORS_PASS_FIXED_CPU_REFERENCE_GATES'
    except BaseException as e:failure=e;state.update({'status':'FAILED','error_type':type(e).__name__,'detail':str(e),'traceback':traceback.format_exc()})
    finally:
        try:
            if graph:stage('before_safe_close');graph.close();stage('safe_close_complete')
        except Exception as e:close_error=repr(e);state['status']='CLOSE_FAILED_DEVICE_STATE_UNCERTAIN'
        state['close_error']=close_error;state['memory_after']=Path('/proc/meminfo').read_text();state['PL_after']=PL.bitfile_name
        if PL.bitfile_name:state['PL_after_bit_sha256']=sha(PL.bitfile_name)
        write(out/'record.json',state);os.sync();write(out/'terminal.json',{'status':state['status'],'PID':os.getpid(),
          'record_sha256':sha(out/'record.json'),'vectors':len(state['rows']),'warmups':len(state['warmups']),'close_error':close_error})
        if lock:fcntl.flock(lock,fcntl.LOCK_UN);lock.close()
        print(json.dumps({'status':state['status'],'vectors':len(state['rows']),'close_error':close_error}),flush=True)
    if failure or close_error:raise SystemExit(1)
if __name__=='__main__':main()
