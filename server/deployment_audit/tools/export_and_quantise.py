"""Static FP32 graphs, real CPU parity and train-only QDQ sensitivity study."""
from pathlib import Path
from collections import Counter
import hashlib,json,os,shutil,sys,time
import numpy as np
import onnx,onnxruntime as ort
from onnxruntime.quantization import CalibrationDataReader
import torch
from PIL import Image
from torchvision.models import mobilenet_v3_small
from graph_audit import audit_graph
from bounded_quantisation import quantise_conv_qdq

PROJECT=Path('/share/home/renly/projects/idcoo_research_20261026');ROOT=PROJECT/'deployment_audit';STUDY=PROJECT/'identity_training/results/study'
os.environ['YOLO_AUTOINSTALL']='false';os.environ['YOLO_CONFIG_DIR']=str(ROOT/'cache/ultralytics')
(ROOT/'cache/ultralytics/Ultralytics').mkdir(parents=True,exist_ok=True)
sys.path.insert(0,str(PROJECT/'identity_training/tools'))
from training_primitives import BodyTransform
from identity_metrics import calibrate_threshold,summarise

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def save(path,value):path.write_text(json.dumps(value,indent=2))
def session(path):
    options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
    return ort.InferenceSession(str(path),sess_options=options,providers=['CPUExecutionProvider'])
def images(rows,transform):
    values=[]
    for r in rows:
        with Image.open(PROJECT/'identity_training'/r['relative_path']) as im:values.append(transform(im.convert('RGB')).numpy())
    return values
def infer(runtime,tensors):return np.concatenate([runtime.run(None,{'images':t[None]})[0] for t in tensors])
class NormalisedEmbedding(torch.nn.Module):
    def __init__(self,encoder):super().__init__();self.encoder=encoder
    def forward(self,x):return torch.nn.functional.normalize(self.encoder(x),p=2,dim=1,eps=1e-12)
def retrieval(gallery,query,gs,qs,threshold=None):
    labels=sorted({r['identity'] for r in gs});similarity=query.astype(float)@gallery.astype(float).T
    scores=np.stack([similarity[:,[i for i,r in enumerate(gs) if r['identity']==label]].max(1) for label in labels],axis=1)
    rows=[]
    for r,values in zip(qs,scores):
        i=int(np.argmax(values));rows.append({'relative_path':r['relative_path'],'identity':r['identity'],'is_known':r['identity'] in labels,
            'predicted_id':labels[i],'similarity':float(values[i]),'accepted':None if threshold is None else bool(values[i]>=threshold)})
    return rows

def main():
    import cv2
    from scipy.optimize import linear_sum_assignment
    from ultralytics import YOLO
    from ultralytics.data.augment import LetterBox
    OUT=ROOT/'results/export_audit';OUT.mkdir(parents=True,exist_ok=False)
    p=json.loads((ROOT/'protocol/export_ptq_v1.json').read_text());torch.set_num_threads(2);cv2.setNumThreads(1);torch.manual_seed(26)
    started=time.perf_counter()
    # Export the trained one-class YOLO26n without modifying the source file.
    det=OUT/'detector';det.mkdir();source=PROJECT/'results/detection_pilot/five_epoch_dev/weights/best.pt'
    assert sha(source)==p['detector']['weights_sha256']
    copy=det/'yolo26n_pilot.pt';shutil.copy2(source,copy);yolo=YOLO(str(copy))
    core=yolo.model.cpu().float().eval()
    references=[];det_inputs=[]
    photo_rows=json.loads((PROJECT/'video_chain/results/replay/events.json').read_text())
    for row in photo_rows:
        image=cv2.imread(str(PROJECT/'video_chain/results/replay'/row['selected_snapshot']['native_photo_path']));assert image.shape==(1440,2560,3)
        lb=LetterBox(new_shape=(320,320),auto=True,stride=32)(image=image)
        value=np.ascontiguousarray(lb[:,:,::-1].transpose(2,0,1)[None],dtype=np.float32)/255
        assert list(value.shape)==[1,3,192,320]
        with torch.inference_mode():result=core(torch.from_numpy(value))
        if isinstance(result,(tuple,list)):result=result[0]
        references.append(result.numpy());det_inputs.append(value)
    exported=yolo.export(format='onnx',imgsz=(192,320),batch=1,opset=13,dynamic=False,simplify=False,nms=False,device='cpu',half=False)
    det_path=Path(exported);assert det_path.exists() and det_path.parent==det
    det_graph=audit_graph(det_path);runtime=session(det_path);comparisons=[];ort_results=[]
    for row,value,reference in zip(photo_rows,det_inputs,references):
        output=runtime.run(None,{'images':value})[0];ort_results.append(output)
        assert output.shape==reference.shape and output.shape[-1]==6
        a=reference[0][reference[0,:,4]>=.2];b=output[0][output[0,:,4]>=.2]
        assert len(a)==len(b)
        coordinate_error=score_error=0.
        if len(a):
            cost=np.abs(a[:,None,:4]-b[None,:,:4]).sum(2)+1000*(a[:,None,5]!=b[None,:,5])
            ii,jj=linear_sum_assignment(cost)
            coordinate_error=float(np.abs(a[ii,:4]-b[jj,:4]).max());score_error=float(np.abs(a[ii,4]-b[jj,4]).max())
            assert coordinate_error<.02 and score_error<1e-4 and np.array_equal(a[ii,5],b[jj,5])
        comparisons.append({'event_id':row['event_id'],'output_shape':list(output.shape),'detections_at_conf02':len(a),
                            'matched_max_coordinate_error_input_pixels':coordinate_error,'matched_max_score_error':score_error,
                            'raw_unsorted_max_absolute_error':float(np.abs(reference-output).max()),'strong_detection_parity':'PASS'})
    np.savez_compressed(det/'parity_vectors.npz',inputs=np.concatenate(det_inputs),torch_outputs=np.concatenate(references),ort_outputs=np.concatenate(ort_results))
    save(det/'parity_index.json',[r['event_id'] for r in photo_rows]);save(det/'graph_audit.json',det_graph)
    save(det/'parity.json',comparisons);del runtime,yolo,core
    # Identity PTQ calibration is exclusively from training-role images.
    manifest=json.loads((PROJECT/'identity_training/results/input_audit/manifest.json').read_text())
    train=sorted([r for r in manifest if r['split']=='train'],key=lambda r:hashlib.sha256(('ptq-calibration-v1:'+r['relative_path']).encode()).hexdigest())[:64]
    index=json.loads((STUDY/'feature_index.json').read_text());train_ids={r['identity'] for r in train}
    assert len(train)==64 and not train_ids&{r['identity'] for split,rows in index.items() for r in rows}
    save(OUT/'ptq_calibration_training_only.json',train)
    transform=BodyTransform();calibration_tensors=images(train,transform)
    validation_g=images(index['validation_gallery'],transform);validation_q=images(index['validation_query'],transform)
    class Reader(CalibrationDataReader):
        def __init__(self):self.position=0
        def get_next(self):
            if self.position>=len(calibration_tensors):return None
            result={'images':calibration_tensors[self.position][None]};self.position+=1;return result
    identity_results=[]
    for condition in p['identity']['conditions']:
        directory=OUT/condition['name'];directory.mkdir();checkpoint=Path(condition['checkpoint']);assert sha(checkpoint)==condition['sha256']
        base=mobilenet_v3_small(weights=None);encoder=torch.nn.Sequential(base.features,base.avgpool,torch.nn.Flatten()).eval()
        encoder.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True));model=NormalisedEmbedding(encoder).eval()
        float_path=directory/'embedding_fp32.onnx';quant_path=directory/'embedding_conv_qdq.onnx'
        torch.onnx.export(model,torch.from_numpy(validation_g[0][None]),str(float_path),opset_version=13,dynamo=False,
                          input_names=['images'],output_names=['embedding'],dynamic_axes=None,do_constant_folding=True)
        fg=audit_graph(float_path)
        quantiser_record=quantise_conv_qdq(float_path,quant_path,Reader())
        save(directory/'calibration_execution_budget.json',quantiser_record)
        qg=audit_graph(quant_path);fr=session(float_path);qr=session(quant_path)
        float_g=infer(fr,validation_g);float_q=infer(fr,validation_q)
        quant_g=infer(qr,validation_g);quant_q=infer(qr,validation_q)
        old=np.load(STUDY/condition['name']/'validation_embeddings.npz')
        assert np.allclose(float_g,old['gallery'],rtol=1e-4,atol=1e-5) and np.allclose(float_q,old['query'],rtol=1e-4,atol=1e-5)
        quant_rows=retrieval(quant_g,quant_q,index['validation_gallery'],index['validation_query'])
        threshold=calibrate_threshold([r['similarity'] for r in quant_rows],[r['predicted_id'] for r in quant_rows],
                                      [r['identity'] for r in quant_rows],[r['is_known'] for r in quant_rows])
        for row in quant_rows:row['accepted']=row['similarity']>=threshold['threshold']
        save(directory/'quantised_validation_threshold.json',threshold);save(directory/'quantised_validation_predictions.json',quant_rows)
        np.savez_compressed(directory/'validation_embeddings.npz',fp32_gallery=float_g,fp32_query=float_q,qdq_gallery=quant_g,qdq_query=quant_q)
        save(directory/'fp32_graph_audit.json',fg);save(directory/'qdq_graph_audit.json',qg)
        identity_results.append({'name':condition['name'],'seed':condition['seed'],'checkpoint_sha256':condition['sha256'],
            'fp32_path':str(float_path),'fp32_sha256':sha(float_path),'qdq_path':str(quant_path),'qdq_sha256':sha(quant_path),
            'original_fp32_threshold':condition['original_threshold'],'qdq_threshold':threshold,'quantised_validation':summarise(quant_rows),
            'validation_fp32_max_feature_error':max(float(np.abs(float_g-old['gallery']).max()),float(np.abs(float_q-old['query']).max())),
            'calibration_execution':quantiser_record,
            'fp32_graph':fg,'qdq_graph':qg,'parameters':sum(v.numel() for v in encoder.parameters())})
        del fr,qr,encoder,model,base
    freeze={'protocol_sha256':sha(ROOT/'protocol/export_ptq_v1.json'),'calibration_training_paths':[r['relative_path'] for r in train],
            'ptq_training_identity_count':len(train_ids),'all_three_quantised_thresholds_frozen_before_evaluation':True,
            'conditions':[{k:r[k] for k in ['name','fp32_sha256','qdq_sha256','original_fp32_threshold','qdq_threshold']} for r in identity_results]}
    save(OUT/'all_quantised_thresholds_frozen.json',freeze);freeze_hash=sha(OUT/'all_quantised_thresholds_frozen.json')
    evaluation_g=images(index['evaluation_gallery'],transform);evaluation_q=images(index['evaluation_query'],transform)
    for condition in identity_results:
        directory=OUT/condition['name'];fr=session(Path(condition['fp32_path']));qr=session(Path(condition['qdq_path']))
        assert sha(Path(condition['fp32_path']))==condition['fp32_sha256'] and sha(Path(condition['qdq_path']))==condition['qdq_sha256']
        float_g=infer(fr,evaluation_g);float_q=infer(fr,evaluation_q);quant_g=infer(qr,evaluation_g);quant_q=infer(qr,evaluation_q)
        old=np.load(STUDY/condition['name']/'evaluation_embeddings.npz')
        assert np.allclose(float_g,old['gallery'],rtol=1e-4,atol=1e-5) and np.allclose(float_q,old['query'],rtol=1e-4,atol=1e-5)
        fp_rows=retrieval(float_g,float_q,index['evaluation_gallery'],index['evaluation_query'],condition['original_fp32_threshold'])
        qp_rows=retrieval(quant_g,quant_q,index['evaluation_gallery'],index['evaluation_query'],condition['qdq_threshold']['threshold'])
        save(directory/'fp32_evaluation_predictions.json',fp_rows);save(directory/'qdq_evaluation_predictions.json',qp_rows)
        np.savez_compressed(directory/'evaluation_embeddings.npz',fp32_gallery=float_g,fp32_query=float_q,qdq_gallery=quant_g,qdq_query=quant_q)
        condition.update(fp32_evaluation=summarise(fp_rows),qdq_evaluation=summarise(qp_rows),
                         evaluation_fp32_max_feature_error=max(float(np.abs(float_g-old['gallery']).max()),float(np.abs(float_q-old['query']).max())),
                         evaluation_qdq_max_feature_error=max(float(np.abs(quant_g-float_g).max()),float(np.abs(quant_q-float_q).max())))
        print(json.dumps({'name':condition['name'],'fp32':{k:v for k,v in condition['fp32_evaluation'].items() if k!='per_identity'},
                          'qdq':{k:v for k,v in condition['qdq_evaluation'].items() if k!='per_identity'}},indent=2),flush=True)
        save(directory/'summary.json',condition);del fr,qr
    assert sha(OUT/'all_quantised_thresholds_frozen.json')==freeze_hash
    save(OUT/'feature_index.json',index)
    summary={'status':'GRAPH_EXPORT_AND_PTQ_HOST_AUDIT_COMPLETE','job_id':os.environ['SLURM_JOB_ID'],
             'versions':{'torch':torch.__version__,'onnx':onnx.__version__,'onnxruntime':ort.__version__},
             'protocol_sha256':sha(ROOT/'protocol/export_ptq_v1.json'),'detector_graph':det_graph,'detector_parity':comparisons,
             'identity_conditions':identity_results,'quantised_threshold_freeze_sha256':freeze_hash,
             'PTQ_calibration_training_images':len(train),'PTQ_calibration_training_identities':len(train_ids),
             'elapsed_s':time.perf_counter()-started,'hardware_build_performed':False,'pynq_measurements':None,
             'scope':p['scope']}
    save(OUT/'summary.json',summary);print(json.dumps({'status':summary['status'],'job_id':os.environ['SLURM_JOB_ID'],'elapsed_s':summary['elapsed_s']},indent=2),flush=True)
if __name__=='__main__':main()
