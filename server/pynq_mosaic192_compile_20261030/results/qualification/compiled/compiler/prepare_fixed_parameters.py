import pathlib,json,numpy as np,argparse
from fixed_point import coefficients
ROOT=pathlib.Path('/share/home/renly/projects/idcoo_research_20261026/pynq_mosaic192_compile_20261030/results/qualification/compiled/compiler');parser=argparse.ArgumentParser();parser.add_argument('--model-name',default='model');args=parser.parse_args();M=pathlib.Path('/share/home/renly/projects/idcoo_research_20261026/pynq_mosaic192_compile_20261030/results/qualification/compiled/model')
graph=json.loads((M/'graph.json').read_text());parameters={};report=[]
with np.load(M/'constants.npz') as arrays:
    for spec in graph['convolutions']:
        if spec['FPGA_supported']:
            q=spec['quant'];ratio=float(arrays[q['input_scale']])*arrays[q['weight_scale']].astype(np.float64)/float(arrays[q['output_scale']])
            mult,shift=coefficients(ratio);parameters['mult%d'%spec['id']]=mult;parameters['shift%d'%spec['id']]=shift
            approximate=mult.astype(np.float64)*np.exp2(-shift.astype(np.int64))
            report.append({'name':spec['name'],'multipliers':mult.tolist(),'shifts':shift.tolist(),
                           'max_absolute_ratio_error':float(np.abs(approximate-ratio).max()),'output_zp':int(arrays[q['output_zp']])})
np.savez(M/'fixed_parameters.npz',**parameters)
(ROOT/'reports/stage_d/fixed_point_parameters.json').write_text(json.dumps(report,indent=2))
print('FIXED_PARAMETERS_READY',len(report))
