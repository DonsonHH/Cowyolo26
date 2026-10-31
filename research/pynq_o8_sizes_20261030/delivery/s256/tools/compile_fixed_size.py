"""PreselectedS192rot90seed26 -> train-only PTQ -> verifiedO8 compiler -> CPU parity."""
from pathlib import Path
from datetime import datetime,timezone
from collections import Counter
import os,sys,socket,json,hashlib,shutil,time,subprocess,copy,gc
os.environ['OMP_NUM_THREADS']='4';os.environ['OPENBLAS_NUM_THREADS']='4';sys.dont_write_bytecode=True
import numpy as np,cv2,torch,onnx,onnxruntime as ort
from ultralytics import YOLO
from onnxruntime.quantization import quantize_static,QuantFormat,QuantType,CalibrationMethod,CalibrationDataReader
ROOT=Path(__file__).resolve().parents[1];D=ROOT/'compiler_workspace'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(p,obj):assert not p.exists();p.write_text(json.dumps(obj,indent=2)+'\n')
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    cv2.setNumThreads(1);torch.set_num_threads(4)
    p=json.loads((ROOT/'protocol/compile_v1.json').read_text());size=p['size'];assert size in [256,320] and p['pipeline_qualification_only'] is True
    for r in p['workspace_files']:assert sha(D/r['relative_file'])==r['sha256']
    assert sha(p['source_checkpoint'])==p['source_checkpoint_sha256']
    for row in p['calibration']:assert row['actual_split']=='train' and sha(row['image_alias'])==row['sha256']
    out=ROOT/'results/qualification';out.mkdir(parents=True,exist_ok=False)
    checkpoint=out/'frozen_S256_rot90_seed26.pt';shutil.copyfile(p['source_checkpoint'],checkpoint)
    assert sha(checkpoint)==p['source_checkpoint_sha256'];model=YOLO(str(checkpoint));assert model.names=={0:'cow'}
    print('EXPORT_FIXED_COW_CHECKPOINT',flush=True)
    fp=Path(model.export(format='onnx',imgsz=size,batch=1,dynamic=False,opset=17,simplify=True,nms=False,device='cpu'))
    graph=onnx.shape_inference.infer_shapes(onnx.load(fp),strict_mode=True,data_prop=True);onnx.checker.check_model(graph);onnx.save(graph,fp)
    assert [d.dim_value for d in graph.graph.input[0].type.tensor_type.shape.dim]==[1,3,size,size]
    convs=[n.name for n in graph.graph.node if n.op_type=='Conv'];assert len(convs)==102,(len(convs),Counter(n.op_type for n in graph.graph.node))
    sys.path.insert(0,str(D/'runtime'));from board_runtime import preprocess
    class Reader(CalibrationDataReader):
        def __init__(self):self.index=0;self.records=[]
        def get_next(self):
            if self.index==128:return None
            row=p['calibration'][self.index];image=cv2.imread(row['image_alias']);assert image.shape==(720,1280,3)
            image=np.rot90(image,k=row['orientation_ccw_quarter_turns']).copy();tensor=preprocess(image,size)
            self.records.append({'file_name':row['file_name'],'sha256':row['sha256'],'orientation_ccw_quarter_turns':row['orientation_ccw_quarter_turns'],
              'input_tensor_sha256':hashlib.sha256(tensor.tobytes()).hexdigest(),'shape':list(tensor.shape)})
            self.index+=1
            if self.index%16==0:print('TRAIN_ONLY_CALIBRATION',self.index,flush=True)
            return {'images':tensor}
    reader=Reader();source=out/'cow_allconv_int8.onnx'
    quantize_static(str(fp),str(source),reader,quant_format=QuantFormat.QDQ,op_types_to_quantize=['Conv'],nodes_to_quantize=convs,
      per_channel=True,activation_type=QuantType.QInt8,weight_type=QuantType.QInt8,calibrate_method=CalibrationMethod.MinMax,
      extra_options={'ActivationSymmetric':False,'WeightSymmetric':True,'CalibMaxIntermediateOutputs':15})
    assert reader.index==128;onnx.checker.check_model(onnx.load(source));save(out/'actual_calibration_inputs.json',reader.records)
    print('QUANTIZATION_COMPLETE_BEFORE_O8_COMPILE',flush=True)
    original=source;source=out/'cow_allconv_int8_normalized.onnx'
    from normalize_graph import normalize
    normalize(original,source,out/'structural_normalization.json')
    options=ort.SessionOptions();options.intra_op_num_threads=4;options.inter_op_num_threads=1
    options.graph_optimization_level=ort.GraphOptimizationLevel.ORT_DISABLE_ALL
    before_session=ort.InferenceSession(str(original),sess_options=options,providers=['CPUExecutionProvider'])
    after_session=ort.InferenceSession(str(source),sess_options=options,providers=['CPUExecutionProvider'])
    normalization_parity=[]
    for row in p['calibration'][:8]:
        image=cv2.imread(row['image_alias']);x=preprocess(np.rot90(image,k=row['orientation_ccw_quarter_turns']).copy(),size)
        before=before_session.run(None,{'images':x})[0];after=after_session.run(None,{'images':x})[0]
        assert before.tobytes()==after.tobytes()
        normalization_parity.append({'file_name':row['file_name'],'outputs_byte_exact':True,'raw_sha256':hashlib.sha256(before.tobytes()).hexdigest()})
    del before_session,after_session;gc.collect()
    save(out/'normalization_parity.json',normalization_parity)

    sys.path.insert(0,str(D/'tools'));from compiler import compile_onnx,enable_integer_depthwise,export_program
    compiled=out/'compiled';M=compile_onnx(source,compiled);ids=enable_integer_depthwise(M);export_program(M,size,compiled/'program')
    program=json.loads((compiled/'program/program.json').read_text());assert program['ops']['QuantConv']==94 and program['ops']['Depthwise']==8
    modelgraph=json.loads((M/'graph.json').read_text());classification=[s for s in modelgraph['convolutions'] if s['name'].endswith('.2/Conv') and '/one2one_cv3.' in s['name']]
    assert len(classification)==3 and all(s['Cout']==1 for s in classification)
    sys.path.insert(0,str(D/'compiler'));from resident_plan import make,write
    planroot=out/'plan_input'/('program_r'+str(size));planroot.mkdir(parents=True,exist_ok=False)
    for name in ['program.json','graph.bin']:shutil.copyfile(compiled/'program'/name,planroot/name)
    plan=make(planroot.parent,size,'all');plansha=write(plan,out/'resident_plan_all')
    command=['g++',*p['native_compile_flags']];native=D/'native_sources'
    assert not (native/'native_queue_linux.so').exists()
    with (out/'native_build.log').open('x') as log:completed=subprocess.run(command,cwd=native,stdout=log,stderr=subprocess.STDOUT)
    assert completed.returncode==0,(out/'native_build.log').read_text()[-4000:]
    # Class lookup remains the exhaustive FP32 sigmoid for all signed codes.
    c=np.load(M/'constants.npz');checks=[]
    for spec in classification:
        q=spec['quant'];codes=np.arange(-128,128,dtype=np.int16).astype(np.int8);x=(codes.astype(np.float32)-np.float32(c[q['output_zp']]))*np.float32(c[q['output_scale']])
        reference=np.float32(1)/(np.float32(1)+np.exp(-np.maximum(x,np.float32(-80))));extreme=x<-80
        if np.any(extreme):e=np.exp(x[extreme]);reference[extreme]=e/(np.float32(1)+e)
        checks.append({'conv_id':spec['id'],'Cout':1,'codes':256,'finite':bool(np.isfinite(reference).all()),'range_valid':bool(((reference>=0)&(reference<=1)).all())})
    c.close();sys.path.insert(0,str(D));from native_graph import NativeGraph
    sys.path.insert(0,str(D/'pc_intdw'));from hybrid_executor import YOLOHybridExecutor
    from integer_backend import TorchIntegerBackend
    nativegraph=NativeGraph(size,pc=True,library='native_queue_linux.so',program=str(compiled/'program'),model_dir=str(M),plan=str(out/'resident_plan_all/resident_plan.bin'),options=4)
    reference=YOLOHybridExecutor(M,TorchIntegerBackend(),quantization_mode='fixed',fuse_activation=True)
    so=ort.SessionOptions();so.intra_op_num_threads=4;so.inter_op_num_threads=1;so.graph_optimization_level=ort.GraphOptimizationLevel.ORT_DISABLE_ALL
    float_session=ort.InferenceSession(str(fp),sess_options=so,providers=['CPUExecutionProvider']);vectors=[];maximum_box=maximum_score=0.
    for i,row in enumerate(p['calibration'][:8]):
        image=cv2.imread(row['image_alias']);image=np.rot90(image,k=row['orientation_ccw_quarter_turns']).copy();x=preprocess(image,size)
        ref=reference.run(x).copy();actual=nativegraph.run(x).copy();fpraw=float_session.run(None,{'images':x})[0]
        assert ref.shape==actual.shape==fpraw.shape==(1,300,6) and np.isfinite(ref).all() and np.isfinite(actual).all()
        assert np.array_equal(ref[:,:,5],actual[:,:,5]) and np.all(actual[:,:,5]==0)
        box_error=float(np.max(np.abs(ref[:,:,:4]-actual[:,:,:4])));score_error=float(np.max(np.abs(ref[:,:,4]-actual[:,:,4])))
        maximum_box=max(maximum_box,box_error);maximum_score=max(maximum_score,score_error)
        np.savez_compressed(out/('parity_train_'+str(i)+'.npz'),input=x,reference_integer_raw=ref,native_integer_raw=actual,FP32_raw=fpraw)
        vectors.append({'file_name':row['file_name'],'input_sha256':hashlib.sha256(x.tobytes()).hexdigest(),'maximum_box_error':box_error,
                        'maximum_score_error':score_error,'classes_exact':True,'passes':box_error<=.002 and score_error<=.0001})
        print('PARITY_TRAIN_IMAGE',i+1,box_error,score_error,flush=True)
    nativegraph.close();del nativegraph,reference,float_session;gc.collect()
    result={'status':'FIXED_SAME_O8_SIZE_COW_COMPILE_AND_CPU_PARITY_COMPLETE','created_UTC':datetime.now(timezone.utc).isoformat(),
       'job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(ROOT/'protocol/compile_v1.json'),'size':size,'checkpoint_sha256':sha(checkpoint),
       'FP32_onnx_sha256':sha(fp),'QDQ_onnx_sha256':sha(source),'actual_train_calibration_images':128,'class_count':1,'primary_model':p['primary_model'],'normalization_parity':normalization_parity,
       'integer_depthwise_ids':ids,'compiled_op_counts':program['ops'],'graph_sha256':sha(compiled/'program/graph.bin'),
       'resident_plan_sha256':plansha,'resident_pairs':len(plan['pairs']),'native_PC_library_sha256':sha(native/'native_queue_linux.so'),
       'class_head_code_checks':checks,'CPU_integer_parity_vectors':vectors,'maximum_box_parity_error':maximum_box,'maximum_score_parity_error':maximum_score,
       'all_native_CPU_parity_gates_pass':all(v['passes'] for v in vectors),'new_training_updates':0,
       'source_video_Toros_or_validation_pixels_used':False,'board_inference_executed':False,'whole_goal_complete':False}
    save(out/'summary.json',result);print(json.dumps(result),flush=True)
    if not result['all_native_CPU_parity_gates_pass']:raise SystemExit(2)
if __name__=='__main__':main()
