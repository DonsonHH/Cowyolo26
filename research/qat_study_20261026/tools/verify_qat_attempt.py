"""Independent saved-vector/graph review, retaining failed original tolerances."""
from pathlib import Path
import hashlib,json,sys
import numpy as np

BASE=Path(__file__).resolve().parents[2]
ROOT=BASE/'qat_study_20261026'
sys.path.insert(0,str(BASE/'deployment_audit_20261026/local_dependencies'))
import onnx,onnxruntime as ort
from onnx import numpy_helper


def main():
    source=ROOT/'delivery'
    protocols={name:json.loads((source/'protocol'/name).read_text()) for name in ['qat_v1.json','qat_v2.json']}
    assert protocols['qat_v1.json']['training']==protocols['qat_v2.json']['training']
    assert protocols['qat_v1.json']['source_models']==protocols['qat_v2.json']['source_models']
    checks=[]
    for folder,expected_pass in [('smoke_failed_129740',0),('smoke',7)]:
        directory=source/'results'/folder
        data=np.load(directory/'export_parity_vectors.npz')
        rows=json.loads((directory/'export_parity.json').read_text())
        assert len(rows)==8 and data['inputs'].shape==(8,3,224,224)
        count=0
        for i,r in enumerate(rows):
            a,b,c=data['torch'][i],data['packed'][i],data['unpacked'][i]
            err=float(np.abs(a-b).max());pack=float(np.abs(c-b).max())
            cosine=float((a.astype(float)*b.astype(float)).sum()/(np.linalg.norm(a)*np.linalg.norm(b)))
            assert abs(err-r['torch_packed_max_absolute_error'])<1e-10
            assert abs(cosine-r['torch_packed_cosine'])<1e-12
            passed=err<=.001 and cosine>=.9999 and pack<=1e-6
            assert passed==r['reference_pass']
            count+=int(passed)
        assert count==expected_pass
        graph=onnx.load(directory/'initial_qat_packed.onnx');onnx.checker.check_model(graph,full_check=True)
        arrays={v.name:numpy_helper.to_array(v) for v in graph.graph.initializer}
        producers={n:node for node in graph.graph.node for n in node.output}
        convs=[n for n in graph.graph.node if n.op_type=='Conv'];assert len(convs)==52
        weight_bytes=0
        for conv in convs:
            dq=producers[conv.input[1]];assert dq.op_type=='DequantizeLinear'
            value=arrays[dq.input[0]];assert value.dtype==np.int8
            weight_bytes+=value.nbytes
        assert weight_bytes==912008
        options=ort.SessionOptions();options.intra_op_num_threads=2;options.inter_op_num_threads=1
        options.graph_optimization_level=ort.GraphOptimizationLevel.ORT_DISABLE_ALL
        runtime=ort.InferenceSession(str(directory/'initial_qat_packed.onnx'),sess_options=options,providers=['CPUExecutionProvider'])
        actual=runtime.run(None,{'images':data['inputs'][:1]})[0]
        err=float(np.abs(actual-data['packed'][:1]).max())
        assert np.allclose(actual,data['packed'][:1],rtol=1e-4,atol=1e-5)
        checks.append({'folder':folder,'original_tolerance_passed_vectors':count,'failed_vectors':8-count,
                       'packed_weight_tensors':52,'packed_weight_bytes':weight_bytes,'local_reference_forward_max_difference':err})
    probe=json.loads((source/'results/rounding_probe.json').read_text())
    assert len(probe['cases'])==156
    differing=[r for r in probe['cases'] if r['kind']=='weight' and r['different_elements']]
    assert len(differing)==47 and sum(r['different_elements'] for r in differing)==812
    assert sum(r['different_elements'] for r in probe['cases'] if r['kind']=='activation')==0
    assert all(r['torch_vs_multiply_difference_elements']==0 and r['onnx_vs_divide_difference_elements']==0 for r in differing)
    probe3=json.loads((source/'results/rounding_probe_training3.json').read_text())
    assert probe3['training_index']==3 and all(r['torch_explicit_division_vs_onnx_difference_elements']==0 for r in probe3['cases'])
    drift=json.loads((source/'results/remaining_drift_probe.json').read_text())
    assert drift['exact_restore_saved_torch_output']
    assert all(r['embedding_max_absolute_error']>.001 for r in drift['conditions'])
    assert drift['conditions'][0]['first_quantised_output_difference']['after_different_elements']==1
    assert not (source/'results/study').exists()
    result={'status':'DIAGNOSTIC_ARITHMETIC_GRAPH_AND_LOCAL_REFERENCE_CHECKS_PASS_QAT_GATE_STILL_FAILS',
            'graph_checks':checks,'quantiser_probe_cases':312,'weight_rounding_different_tensors':47,
            'weight_rounding_different_elements':812,'training_role_only_inputs_verified':probe['row']['split']=='train' and probe3['row']['split']=='train',
            'formal_QAT_or_paired_training_updates':0,'remaining_original_tolerance_failures':1,
            'FPGA_execution_verified':False,'full_goal_complete':False}
    (ROOT/'results/independent_verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result),flush=True)


if __name__=='__main__':main()
