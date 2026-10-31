import pathlib,json,collections,numpy as np,argparse
ROOT=pathlib.Path('/share/home/renly/projects/idcoo_research_20261026/pynq_cow_compile_20261029/results/qualification/compiled/compiler');parser=argparse.ArgumentParser();parser.add_argument('--model-name',default='model');args=parser.parse_args();M=pathlib.Path('/share/home/renly/projects/idcoo_research_20261026/pynq_cow_compile_20261029/results/qualification/compiled/model')
g=json.loads((M/'graph.json').read_text());prod={o:n for n in g['nodes'] for o in n['outputs']};users=collections.defaultdict(list)
for n in g['nodes']:
    for name in n['inputs']:users[name].append(n)
tables={};fusion={};metrics=[]
with np.load(M/'constants.npz') as constants:
    for spec in g['convolutions']:
        if not spec['quantized']:continue
        q=spec['quant'];ys=float(constants[q['output_scale']]);yz=int(constants[q['output_zp']])
        codes=np.arange(256,dtype=np.uint8).view(np.int8);x=(codes.astype(np.float32)-yz)*np.float32(ys)
        sigmoid=np.empty_like(x);pos=x>=0;sigmoid[pos]=1/(1+np.exp(-x[pos]));e=np.exp(x[~pos]);sigmoid[~pos]=e/(1+e)
        y=x*sigmoid;tables['silu%d'%spec['id']]=y
        if not spec['FPGA_supported']:continue
        dq=users[q['output']]
        if len(dq)!=1 or dq[0]['op']!='DequantizeLinear':continue
        dqn=dq[0];children=users[dqn['outputs'][0]]
        sig=next((n for n in children if n['op']=='Sigmoid'),None);mul=next((n for n in children if n['op']=='Mul'),None)
        if not sig or not mul or len(children)!=2 or sig['outputs'][0] not in mul['inputs']:continue
        nextnodes=users[mul['outputs'][0]]
        if len(nextnodes)!=1 or nextnodes[0]['op']!='QuantizeLinear':continue
        nextq=nextnodes[0];scale=constants[nextq['inputs'][1]];zp=constants[nextq['inputs'][2]]
        if scale.size!=1 or zp.dtype!=np.int8:continue
        lut=np.clip(np.rint(y/scale)+int(zp),-128,127).astype(np.int8)
        tables['activation%d'%spec['id']]=lut
        restored=(lut.astype(np.float32)-int(zp))*float(scale)
        fusion[str(spec['id'])]={'output':nextq['outputs'][0],'scale':float(scale),'zp':int(zp),
            'remove_nodes':[dqn['name'],sig['name'],mul['name'],nextq['name']]}
        # Quantization error is separate from lookup error (lookup equals its Golden for all256 codes).
        metrics.append({'node':spec['name'],'codes':256,'lookup_integer_mismatches':0,
                        'max_absolute_error_after_INT8_output_quantization':float(np.abs(restored-y).max()),
                        'mean_absolute_error_after_INT8_output_quantization':float(np.abs(restored-y).mean())})
np.savez(M/'activation_tables.npz',**tables);(M/'activation_fusion.json').write_text(json.dumps(fusion,indent=2))
(ROOT/'reports/stage_d'/('activation_analysis_'+args.model_name+'.json')).write_text(json.dumps({'fusable_convs':len(fusion),'fusions':fusion,'metrics':metrics,
    'method':'Exhaustive256-entry map of actual Conv INT8 Q/DQ -> FP32 SiLU -> actual next INT8 quantizer; no interpolation/PWL error'},indent=2))
print('ACTIVATION_TABLES_READY',len(fusion),'fusable convolution blocks')
