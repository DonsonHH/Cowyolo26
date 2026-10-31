from pathlib import Path
import hashlib,json,os,sys,tempfile
import numpy as np
import onnx,onnxruntime as ort
from onnxruntime.quantization import CalibrationDataReader,QuantType
from onnxruntime.quantization.qdq_quantizer import QDQQuantizer
from onnxruntime.quantization.quant_utils import load_model_with_shape_infer
from PIL import Image
PROJECT=Path('/share/home/renly/projects/idcoo_research_20261026');ROOT=PROJECT/'quant_diagnosis';SOURCE=PROJECT/'deployment_audit/results/export_audit'
sys.path.insert(0,str(PROJECT/'deployment_audit/tools'))
from bounded_quantisation import BudgetedMinMaxCalibrater
from graph_audit import audit_graph
sys.path.insert(0,str(PROJECT/'identity_training/tools'))
from training_primitives import BodyTransform
from identity_metrics import calibrate_threshold,summarise

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def session(path):
    options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
    return ort.InferenceSession(str(path),sess_options=options,providers=['CPUExecutionProvider'])
def main():
    OUT=ROOT/'results/mixed';OUT.mkdir(parents=True,exist_ok=False)
    pp=ROOT/'protocol/mixed_precision_v1.json';p=json.loads(pp.read_text())
    base=json.loads((SOURCE/'summary.json').read_text());index=json.loads((SOURCE/'feature_index.json').read_text())
    calibration=json.loads((SOURCE/'ptq_calibration_training_only.json').read_text());assert len(calibration)==64
    transform=BodyTransform();reads=[]
    def tensor(row):
        assert row['split'] in ['train','validation_gallery','validation_query']
        path=PROJECT/'identity_training'/row['relative_path'];reads.append({'relative_path':row['relative_path'],'split':row['split']})
        with Image.open(path) as im:return transform(im.convert('RGB')).numpy()[None]
    ct=[tensor(r) for r in calibration];vg=[tensor(r) for r in index['validation_gallery']];vq=[tensor(r) for r in index['validation_query']]
    class Reader(CalibrationDataReader):
        def __init__(self):self.index=0
        def get_next(self):
            if self.index==len(ct):return None
            row={'images':ct[self.index]};self.index+=1;return row
    def retrieve(g,q):
        ids=sorted({r['identity'] for r in index['validation_gallery']});similarities=q.astype(float)@g.astype(float).T
        scores=np.stack([similarities[:,[i for i,r in enumerate(index['validation_gallery']) if r['identity']==identity]].max(1) for identity in ids],axis=1)
        predictions=[]
        for row,s in zip(index['validation_query'],scores):
            j=int(np.argmax(s));predictions.append({'relative_path':row['relative_path'],'identity':row['identity'],
                'is_known':row['identity'] in ids,'predicted_id':ids[j],'similarity':float(s[j])})
        threshold=calibrate_threshold([r['similarity'] for r in predictions],[r['predicted_id'] for r in predictions],
                       [r['identity'] for r in predictions],[r['is_known'] for r in predictions])
        for row in predictions:row['accepted']=row['similarity']>=threshold['threshold']
        return predictions,threshold,summarise(predictions)
    rows=[]
    for source_condition in base['identity_conditions']:
        name=source_condition['name'];seed=source_condition['seed'];source=SOURCE/name/'embedding_fp32.onnx'
        convs=source_condition['fp32_graph']['Conv_details'];assert [r['name'] for r in convs]==p['all_conv_nodes']
        for candidate in p['candidates']:
            destination=OUT/candidate['name']/name;destination.mkdir(parents=True)
            if candidate['name']=='full_conv_qdq':model=SOURCE/name/'embedding_conv_qdq.onnx'
            else:
                model=destination/'embedding_mixed_qdq.onnx'
                graph=load_model_with_shape_infer(source)
                with tempfile.TemporaryDirectory(prefix='budgeted-mixed-calibration-') as temporary:
                    calibrator=BudgetedMinMaxCalibrater(source,['Conv'],str(Path(temporary)/'augmented.onnx'),symmetric=False)
                    calibrator.augment_graph();calibrator.create_inference_session();calibrator.collect_data(Reader());ranges=calibrator.compute_data();del calibrator
                quantiser=QDQQuantizer(graph,True,False,QuantType.QInt8,QuantType.QUInt8,ranges,[],candidate['exclude_nodes'],['Conv'],
                                        {'WeightSymmetric':True,'ActivationSymmetric':False})
                quantiser.quantize_model();quantiser.model.save_model_to_file(str(model),False)
            graph_audit=audit_graph(model);runtime=session(model)
            g=np.concatenate([runtime.run(None,{'images':t})[0] for t in vg]);q=np.concatenate([runtime.run(None,{'images':t})[0] for t in vq])
            predictions,threshold,metrics=retrieve(g,q);np.savez_compressed(destination/'validation_embeddings.npz',gallery=g,query=q)
            (destination/'validation_predictions.json').write_text(json.dumps(predictions,indent=2));(destination/'threshold.json').write_text(json.dumps(threshold,indent=2))
            fp_macs=sum(r['MACs'] for r in convs if r['name'] in candidate['exclude_nodes'])
            record={'candidate':candidate['name'],'seed':seed,'source_condition':name,'model_path':str(model),'model_sha256':sha(model),
                    'excluded_nodes':candidate['exclude_nodes'],'excluded_fp32_Conv_MACs':fp_macs,
                    'all_Conv_MACs':source_condition['fp32_graph']['Conv_MACs_direct_initializer_only'],
                    'model_graph':graph_audit,'validation_threshold':threshold,'validation':metrics}
            (destination/'summary.json').write_text(json.dumps(record,indent=2));rows.append(record)
            print(json.dumps({'candidate':candidate['name'],'seed':seed,'validation_C':metrics['known_correct_accepted_C'],
                             'validation_W':metrics['known_wrong_accepted_W'],'validation_unknown_false_accepts':metrics['unknown_false_accepts'],
                             'FP32_Conv_MACs':fp_macs,'graph_bytes':model.stat().st_size}),flush=True)
            del runtime
    rankings=[]
    for ordinal,candidate in enumerate(p['candidates']):
        group=[r for r in rows if r['candidate']==candidate['name']];assert len(group)==3
        key=[min(r['validation']['known_correct_accepted_C'] for r in group),
             sum(r['validation']['known_correct_accepted_C'] for r in group)/3,
             -sum(r['validation']['known_wrong_accepted_W'] for r in group),-group[0]['excluded_fp32_Conv_MACs'],-ordinal]
        rankings.append({'candidate':candidate['name'],'selection_key':key})
    selected=max(rankings,key=lambda r:r['selection_key'])['candidate'];selected_rows=[r for r in rows if r['candidate']==selected]
    assert all(r['validation']['unknown_false_acceptance_rate']<=.05 for r in selected_rows)
    freeze={'protocol_sha256':sha(pp),'selection':p['selection'],'all_candidate_rankings':rankings,'selected_recipe':selected,
            'conditions':[{'seed':r['seed'],'model_path':r['model_path'],'model_sha256':r['model_sha256'],'threshold':r['validation_threshold']['threshold']} for r in selected_rows],
            'future_holdout_inference_performed':False,'old_evaluation_forward_performed':False,'use_case':'Candidate recipe for future holdout, not deployed board acceptance'}
    (OUT/'candidate_and_thresholds_frozen.json').write_text(json.dumps(freeze,indent=2));(OUT/'image_access_log.json').write_text(json.dumps(reads,indent=2))
    result={'status':'VALIDATION_ONLY_MIXED_PRECISION_COMPLETE','job_id':os.environ['SLURM_JOB_ID'],'protocol_sha256':sha(pp),'conditions':rows,
            'frozen_candidate':freeze,'future_evaluation_not_yet_performed':True,'validation_identity_counts':{'registered':5,'unknown':6}}
    (OUT/'summary.json').write_text(json.dumps(result,indent=2));print(json.dumps({'selected_recipe':selected,'rankings':rankings}),flush=True)
if __name__=='__main__':main()
