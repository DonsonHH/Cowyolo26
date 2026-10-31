"""Independent graph parsing, class-LUT contract and actual board raw checks."""
from pathlib import Path
from datetime import datetime,timezone
from types import SimpleNamespace
import json,hashlib,struct,tarfile,copy,math,importlib.util,statistics
import numpy as np
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists();p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
q=ROOT/'delivery/results/qualification';summary=load(q/'summary.json');proto=load(ROOT/'protocol/compile_v1.json')
assert summary['checkpoint_sha256']==proto['source_checkpoint_sha256']=='7b01cead4841f17d561f2a6bd768f9b229f1b3bd142818d8302135d3c69ffd45'
assert summary['class_count']==1 and summary['actual_train_calibration_images']==128
assert summary['maximum_box_parity_error']==summary['maximum_score_parity_error']==0 and summary['all_native_CPU_parity_gates_pass'] is True
assert sha(q/'compiled/program/graph.bin')==summary['graph_sha256'] and sha(q/'resident_plan_all/resident_plan.bin')==summary['resident_plan_sha256']
raw=(q/'compiled/program/graph.bin').read_bytes();cursor=0
def ints(n):
    global cursor
    values=struct.unpack_from('<'+'i'*n,raw,cursor);cursor+=4*n;return list(values)
magic,nt,nn,inputid,outputid=ints(5);assert magic==0x3747504f
meta=load(q/'compiled/program/program.json');assert nt==len(meta['names']) and nn==len(meta['nodes']) and inputid==meta['input_id'] and outputid==meta['output_id']
types={1:np.dtype('<f4'),2:np.dtype('u1'),3:np.dtype('i1'),6:np.dtype('<i4'),7:np.dtype('<i8'),12:np.dtype('<u4'),9:np.dtype('bool')}
constants={};shapes={}
for i,name in enumerate(meta['names']):
    kind,rank,*dims=ints(8);shape=dims[:rank];nbytes=ints(1)[0];assert 0<=rank<=6 and nbytes>=0
    assert meta['shapes'][name]==[shape,str(types[kind])]
    data=raw[cursor:cursor+nbytes];cursor+=nbytes
    if nbytes:constants[name]=np.frombuffer(data,dtype=types[kind]).reshape(shape).copy()
    shapes[name]=shape
for node in meta['nodes']:
    opcode,ni,no,na=ints(4);inputs=ints(ni);outputs=ints(no);attrs=ints(na)
    assert [meta['names'][i] if i!=-1 else '' for i in inputs]==node['inputs'] and [meta['names'][i] for i in outputs]==node['outputs'] and attrs==node['attrs']
assert cursor==len(raw) and shapes[meta['names'][outputid]]==[1,300,6]
assert sum(n['op']=='QuantConv' for n in meta['nodes'])==94 and sum(n['op']=='Depthwise' for n in meta['nodes'])==8
modelgraph=load(q/'compiled/model/graph.json')
with np.load(q/'compiled/model/constants.npz') as archive:original_constants={name:archive[name] for name in archive.files}
def module(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
modified=module('cow_lut_generalized',ROOT/'compiler_workspace/pc_intdw/head_lut.py')
baseline=module('cow_lut_original80',PROJECT/'pynq_cow_compile_20261029/source_snapshot/runtime_fast/head_lut.py')
heads=[s for s in modelgraph['convolutions'] if '/one2one_cv3.' in s['name'] and s['name'].endswith('.2/Conv')];assert len(heads)==3 and all(s['Cout']==1 for s in heads)
def fake(classes):
    specs=copy.deepcopy(modelgraph['convolutions'])
    for s in specs:
        if s['id'] in {h['id'] for h in heads}:s['Cout']=classes
    graph={'nodes':copy.deepcopy(modelgraph['nodes']),'output':modelgraph['output']}
    return SimpleNamespace(head_nets={},graph=graph,specs={s['id']:s for s in specs},constants={k:v.copy() for k,v in original_constants.items()},
         required_inputs={n['name']:list(n['inputs']) for n in graph['nodes']})
ex1=fake(1);ex80=fake(80);ref80=fake(80);modified.optimize(ex1);modified.optimize(ex80);baseline.optimize(ref80)
assert ex80.graph==ref80.graph and all(np.array_equal(ex80.constants[k],ref80.constants[k]) for k in ex80.constants)
maximum_scalar=0.;codechecks=0
for scale,head in enumerate(heads):
    key='_o6_cls_sigmoid_table_'+str(scale);assert np.array_equal(ex1.constants[key],constants[key]) and np.array_equal(ex80.constants[key],ref80.constants[key])
    assert ex1.constants['_o6_cls_shape_'+str(scale)].tolist()==[1,1,-1] and ex80.constants['_o6_cls_shape_'+str(scale)].tolist()==[1,80,-1]
    query=head['quant'];scale_value=np.float32(original_constants[query['output_scale']]);zero=np.float32(original_constants[query['output_zp']])
    for i in range(256):
        signed=i if i<128 else i-256;x=float(np.float32(np.float32(signed)-zero)*scale_value)
        expected=1/(1+math.exp(-x)) if x>=0 else math.exp(x)/(1+math.exp(x))
        delta=abs(float(constants[key][i])-expected);assert delta<2e-7;maximum_scalar=max(maximum_scalar,delta);codechecks+=1
assert codechecks==768
calibration=load(ROOT/'delivery/results/qualification/actual_calibration_inputs.json');assert len(calibration)==128
assert {r['file_name'] for r in calibration}=={r['file_name'] for r in proto['calibration']} and all(r['actual_split']=='train' for r in proto['calibration'])
for index in range(8):
    with np.load(q/('parity_train_'+str(index)+'.npz')) as ar:
        assert np.array_equal(ar['reference_integer_raw'],ar['native_integer_raw'])
        assert ar['input'].shape==(1,3,192,192) and np.isfinite(ar['FP32_raw']).all()
transfer=load(ROOT/'evidence/board_transfer.json');archive=ROOT/'board_results.tar.gz';assert archive.stat().st_size==transfer['bytes'] and sha(archive)==transfer['sha256']
out=ROOT/'board_delivery';out.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    members=tar.getmembers();assert len(members)==transfer['members']
    for member in members:
        assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
        file=(out/member.name).resolve();assert file.is_relative_to(out.resolve()) and not file.exists()
        file.parent.mkdir(parents=True,exist_ok=True);file.write_bytes(tar.extractfile(member).read())
for row in load(out/'board_result_manifest.json'):
    file=out/row['relative_file'];assert file.stat().st_size==row['bytes'] and sha(file)==row['sha256']
assert sha(out/'protocol.json')==sha(ROOT/'protocol/board_vectors_v1.json') and sha(out/'board_cow_vectors.py')==sha(ROOT/'tools/board_cow_vectors.py')
board=load(out/'results/record.json');terminal=load(out/'results/terminal.json');final=load(out/'final_state.json')
assert board['status']==terminal['status']=='ALL8_ACTUAL_PYNQ_COW1_CLASS_O8_VECTORS_PASS_FIXED_CPU_REFERENCE_GATES'
assert terminal['record_sha256']==sha(out/'results/record.json') and terminal['vectors']==8 and terminal['warmups']==2 and terminal['close_error'] is None
assert final['proc_exists'] is False and final['PL_bit_sha256']==board['PL_after_bit_sha256']==load(ROOT/'protocol/board_vectors_v1.json')['expected_O8_bit_sha256']
assert board['model_checkpoint_sha256']==summary['checkpoint_sha256'] and board['class_count']==1
max_box=max_score=0.;detections=[]
for i,row in enumerate(board['rows']):
    with np.load(q/('parity_train_'+str(i)+'.npz')) as ar:x=ar['input'];ref=ar['reference_integer_raw'];cpu=ar['native_integer_raw']
    file=out/'results'/row['raw_file'];assert sha(file)==row['raw_file_sha256'];actual=np.load(file)
    assert actual.shape==ref.shape==cpu.shape==(1,300,6) and actual.dtype==np.float32 and np.isfinite(actual).all()
    assert hashlib.sha256(x.tobytes()).hexdigest()==row['input_array_sha256'] and hashlib.sha256(actual.tobytes()).hexdigest()==row['raw_array_sha256']
    assert np.array_equal(actual[:,:,5],ref[:,:,5]) and np.all(actual[:,:,5]==0)
    box=float(np.max(np.abs(actual[:,:,:4]-ref[:,:,:4])));score=float(np.max(np.abs(actual[:,:,4]-ref[:,:,4])))
    assert box==row['maximum_box_error']<=.002 and score==row['maximum_score_error']<=.0001 and row['passes_gate'] is True
    max_box=max(max_box,box);max_score=max(max_score,score);count=int((actual[0,:,4]>=.2).sum());assert count==row['detections_above_conf02'];detections.append(count)
    assert row==load(out/'results'/('vector_'+str(i)+'.json')) and row['hardware_status']['error']=='0x0' and row['hardware_status']['version']=='0x80001'
assert len(board['rows'])==8 and len(board['warmups'])==2 and detections==[2,3,2,1,3,2,1,2]
result={'status':'SINGLE_CLASS_O8_COMPILE_STATIC_GRAPH_CLASS_LUT_AND8_ACTUAL_FPGA_ARM_VECTORS_INDEPENDENTLY_VERIFIED',
 'created_host_UTC':datetime.now(timezone.utc).isoformat(),'model_checkpoint_sha256':summary['checkpoint_sha256'],'size':192,'class_count':1,
 'static_tensor_entries_parsed':nt,'static_nodes_parsed':nn,'graph_binary_bytes_parsed':len(raw),'dense_PL_convolutions':94,'integer_ARM_depthwise':8,
 'class_LUT_codes_scalar_checked':768,'maximum_LUT_scalar_sigmoid_difference':maximum_scalar,
 'generalized80class_LUT_metadata_contract_matches_original':True,'80class_test_is_LUT_contract_not_full_network_execution':True,
 'CPU_reference_vs_native_vectors_exact':8,'actual_FPGA_ARM_reference_vectors_checked':8,'actual_model_forwards_with2warmups':10,
 'board_maximum_box_error':max_box,'board_maximum_score_error':max_score,'actual_board_raw_arrays_byte_exact':max_box==max_score==0,
 'training_vector_detections_above_conf02':detections,'mean_training_vector_tensor_to_raw_ms':statistics.mean(r['tensor_to_raw_ms'] for r in board['rows']),
 'real_source_video_count_or_identity_accuracy_admitted':False,'one_preselected_new_model_actual_board_vectors_verified':True,'all15_new_models_board_verified':False,
 'new_firmware_programming':False,'original_O8_assets_modified':False,'board_process_terminal_and_absent':True,
 'foreground_background_joint5FPS_proven':False,'new_training_updates':0,'whole_goal_complete':False}
save(ROOT/'results/independent_implementation_verification.json',result);print(json.dumps(result))
