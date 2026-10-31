"""Exact structural rewrites for the observed single-class static ONNX graph."""
from pathlib import Path
import copy,json,hashlib
import onnx,numpy as np
from onnx import helper,numpy_helper
def normalize(source,destination,record_path):
    source=Path(source);destination=Path(destination);assert not destination.exists()
    model=onnx.shape_inference.infer_shapes(onnx.load(source),strict_mode=True,data_prop=True)
    constants={a.name:numpy_helper.to_array(a) for a in model.graph.initializer}
    shapes={v.name:[d.dim_value for d in v.type.tensor_type.shape.dim] for v in [*model.graph.input,*model.graph.value_info,*model.graph.output]}
    nodes=[];added=[];changes=[]
    for i,node in enumerate(model.graph.node):
        if node.op_type=='Tile':
            shape=shapes[node.input[0]];repeats=constants[node.input[1]].astype(np.int64)
            assert len(shape)==len(repeats) and all(s>0 and r>=1 and (r==1 or s==1) for s,r in zip(shape,repeats))
            target=np.asarray(shape,np.int64)*repeats;name='__cow_tile_expand_shape_'+str(i)
            added.append(numpy_helper.from_array(target,name));nodes.append(helper.make_node('Expand',[node.input[0],name],list(node.output),name=node.name+'_ExactBroadcast'))
            changes.append({'original_name':node.name,'operation':'Tile_to_Expand','input_shape':shape,'repeats':repeats.tolist(),'proof':'Everyrepeatedaxiswaslength1;broadcastvalue/orderexact','output_shape':target.tolist()})
        elif node.op_type=='Gather':
            attrs={a.name:helper.get_attribute_value(a) for a in node.attribute};data_shape=shapes[node.input[0]];index_shape=shapes[node.input[1]]
            assert attrs.get('axis',0)==0 and len(data_shape)==2 and data_shape[1]==1 and len(index_shape)==2 and index_shape[0]==1
            assert node.name=='/model.23/Gather_3','Onlyobservedsingleclassstaticindexgatherisqualified'
            count=data_shape[0];shape_name='__cow_gather_shape_'+str(i);axis_name='__cow_gather_axis_'+str(i)
            added.extend([numpy_helper.from_array(np.array([1,count,1],np.int64),shape_name),numpy_helper.from_array(np.array([2],np.int64),axis_name)])
            data='__cow_gather_data_'+str(i);indices='__cow_gather_indices_'+str(i)
            nodes.extend([helper.make_node('Reshape',[node.input[0],shape_name],[data],name=node.name+'_ExactReshape'),
                          helper.make_node('Unsqueeze',[node.input[1],axis_name],[indices],name=node.name+'_ExactUnsqueeze'),
                          helper.make_node('GatherElements',[data,indices],list(node.output),axis=1,name=node.name+'_ExactElements')])
            changes.append({'original_name':node.name,'operation':'Gather_axis0_to_GatherElements_axis1','data_shape':data_shape,'index_shape':index_shape,
             'proof':'Batch1andonecolumn;reshapeisaliasandunsqueezepreservesindexorder;outputs1xKx1unchanged.'})
        else:nodes.append(copy.deepcopy(node))
    assert len(changes)==3 and sum(c['operation']=='Tile_to_Expand' for c in changes)==2
    del model.graph.node[:];model.graph.node.extend(nodes);model.graph.initializer.extend(added)
    model=onnx.shape_inference.infer_shapes(model,strict_mode=True,data_prop=True);onnx.checker.check_model(model,full_check=True);onnx.save(model,destination)
    record={'status':'EXACT_STATIC_SINGLE_CLASS_STRUCTURE_NORMALIZATION','source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
      'normalized_sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'changes':changes,'weight_and_quantization_initializer_bytes_modified':False,
      'new_constants_only_shapes_and_axes':len(added),'runtime_parity_still_required':True}
    Path(record_path).write_text(json.dumps(record,indent=2)+'\n');return record
