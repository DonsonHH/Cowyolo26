import pathlib,json,copy,argparse
import onnx
from onnx import helper,numpy_helper,TensorProto
import numpy as np
ROOT=pathlib.Path(__file__).resolve().parents[2];parser=argparse.ArgumentParser();parser.add_argument('--model-name',default='model');args=parser.parse_args();M=ROOT/'output/stage_d'/args.model_name
g=json.loads((M/'graph.json').read_text());heads=[]
with np.load(M/'constants.npz') as c:
    for scale in range(3):
        prefixes=('/model.23/one2one_cv2.%d/'%scale,'/model.23/one2one_cv3.%d/'%scale)
        selected=[n for n in g['nodes'] if n['name'].startswith(prefixes)]
        outputs={o for n in selected for o in n['outputs']}
        external={i for n in selected for i in n['inputs'] if i not in outputs and i not in c.files}
        assert len(external)==1,external
        input_name=external.pop();last=[]
        for prefix in prefixes:
            convolutions=[n for n in selected if n['op']=='Conv' and n['name'].startswith(prefix)]
            last.append(convolutions[-1]['outputs'][0])
        constants={i for n in selected for i in n['inputs'] if i in c.files}
        nodes=[]
        for n in selected:
            inputs=['x' if i==input_name else i for i in n['inputs']]
            nodes.append(helper.make_node(n['op'],inputs,n['outputs'],name=n['name'],**n['attrs']))
        nodes.extend([helper.make_node('Identity',[last[0]],['box'],name='box'),helper.make_node('Identity',[last[1]],['cls'],name='cls')])
        graph=helper.make_graph(nodes,'head%d'%scale,[helper.make_tensor_value_info('x',TensorProto.FLOAT,g['tensors'][input_name]['shape'])],
            [helper.make_tensor_value_info(name,TensorProto.FLOAT,g['tensors'][tensor]['shape']) for name,tensor in zip(('box','cls'),last)],
            [numpy_helper.from_array(c[name],name) for name in constants])
        model=helper.make_model(graph,opset_imports=[helper.make_opsetid('',17)],ir_version=8);onnx.checker.check_model(model)
        onnx.save(model,M/('cpu_head_%d.onnx'%scale))
        heads.append({'scale':scale,'input':input_name,'outputs':last,'names':['box','cls'],'nodes':[n['name'] for n in selected]})
(M/'cpu_heads.json').write_text(json.dumps(heads,indent=2));print('CPU_HEAD_GROUPING_READY',len(heads))
