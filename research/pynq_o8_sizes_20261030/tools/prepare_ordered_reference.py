from pathlib import Path
from datetime import datetime,timezone
import json,hashlib,ast
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=ROOT/'s320/compiler_workspace/pc_intdw/hybrid_executor.py';text=source.read_text();text=text.replace('import numpy as np', 'import numpy as np\nfrom ordered_float_reference import ordered_matmul,ordered_softmax')
assert text.count('else:y=np.matmul(*inputs)')==1
text=text.replace('else:y=np.matmul(*inputs)','else:y=ordered_matmul(*inputs)')
old="x=inputs[0];axis=a.get('axis',-1);e=np.exp(x-x.max(axis=axis,keepdims=True));y=e/e.sum(axis=axis,keepdims=True)"
assert text.count(old)==1;text=text.replace(old,"y=ordered_softmax(inputs[0],a.get('axis',-1))")
file=ROOT/'tools/ordered_hybrid_executor.py';assert not file.exists();file.write_text(text,newline='\n');ast.parse(text)
p={'status':'FROZEN_EXPLICIT_NONCONV_FLOAT_REFERENCE_CONTRACT_BEFORE24_VECTOR_RECHECK','created_UTC':datetime.now(timezone.utc).isoformat(),
 'reason':'Failed320vectorFP32attentionBLASsumorderstraddlesoneINT8halfboundary;oneboundaryinterventionrestoresallraw. Oldreferencefailureunchanged.',
 'integer_conv_contract_unchanged':True,'weights_calibration_runtime_firmware_and_quantization_unchanged':True,
 'MatMul':'FP32products,FP32serialaccumulationalongK;noFMA;finalFP32',
 'Softmax':'FP32subtractmax,C99expfperlogit,FP32left-to-rightsum,FP32division;axislast',
 'reference_code_calls_native_executor':False,'expf_scalar_math_primitive_shared_with_host_C99_libm':True,
 'reference_implementation_is_operationally_independent_vectorized_MatMul_and_Python_serial_Softmax':True,
 'scope':'Referencecontractclarification,noinferencefix. OriginalNumPyreferencefullrawparityfailurepreserved.',
 'original_hybrid_executor_sha256':sha(source),'new_ordered_reference_sha256':sha(ROOT/'tools/ordered_float_reference.py'),
 'ordered_hybrid_executor_sha256':sha(file),'frozen_test_sizes':[192,256,320],'fixed_train_vectors_each':8,
 'complete_raw_gate':'Originalscore<=1e-4,box<=.002,classsame;also report exactbytes against orderedreference and originalreference.',
 'no_new_training_or_model_selection':True,'whole_goal_complete':False}
protocol=ROOT/'protocol/ordered_float_reference_v1.json';protocol.write_text(json.dumps(p,indent=2)+'\n');print(json.dumps({'ordered_reference_protocol_sha256':sha(protocol),'original_gate_failure_retained':True}))
