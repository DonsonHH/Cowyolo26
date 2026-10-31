from pathlib import Path
import tempfile,unittest
import numpy as np
import onnx
from onnx import helper,numpy_helper,TensorProto
from graph_audit import audit_graph

class GraphAccountingContract(unittest.TestCase):
    def graph(self,channels,output,group=1,dynamic=False):
        x=helper.make_tensor_value_info('images',TensorProto.FLOAT,[1,channels,'H' if dynamic else 8,8])
        y=helper.make_tensor_value_info('out',TensorProto.FLOAT,[1,output,'H' if dynamic else 8,8])
        weights=numpy_helper.from_array(np.ones((output,channels//group,3,3),dtype=np.float32),name='weights')
        node=helper.make_node('Conv',['images','weights'],['out'],pads=[1,1,1,1],group=group)
        model=helper.make_model(helper.make_graph([node],'analytical',[x],[y],[weights]),opset_imports=[helper.make_opsetid('',13)])
        return model
    def evaluate(self,model):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'model.onnx';onnx.save(model,path);return audit_graph(path)
    def test_standard_conv_macs_have_known_analytic_value(self):
        r=self.evaluate(self.graph(3,4));self.assertEqual(r['Conv_MACs_direct_initializer_only'],1*4*8*8*3*3*3)
        self.assertEqual(r['initializer_bytes'],4*3*3*3*4)
        self.assertEqual(r['largest_inferred_nonconstant_tensor_bytes'],4*8*8*4)
    def test_grouped_depthwise_count_uses_per_group_channels(self):
        r=self.evaluate(self.graph(4,4,4));self.assertEqual(r['Conv_MACs_direct_initializer_only'],1*4*8*8*1*3*3)
        self.assertEqual(r['Conv_details'][0]['group'],4)
    def test_dynamic_shape_is_flagged_as_incomplete(self):
        r=self.evaluate(self.graph(3,4,dynamic=True));self.assertIn('out',r['unknown_output_size_tensors'])
        self.assertEqual(r['Conv_MACs_direct_initializer_only'],0);self.assertFalse(r['is_fpga_compile_proof'])

if __name__=='__main__':unittest.main(verbosity=2)
