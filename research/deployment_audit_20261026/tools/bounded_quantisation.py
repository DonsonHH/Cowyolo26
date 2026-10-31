"""ORT1.23.2 MinMax/QDQ building blocks with an explicit CPU thread budget.

The high-level quantize_static helper does not expose calibrator SessionOptions
in this pinned release. Subclass only the calibrator session factory; leave
all graph/calibration/quantisation rules unchanged. No library patching.
"""
from pathlib import Path
import tempfile
import onnxruntime as ort
from onnxruntime.quantization import QuantType
from onnxruntime.quantization.calibrate import MinMaxCalibrater,TensorsData
from onnxruntime.quantization.qdq_quantizer import QDQQuantizer
from onnxruntime.quantization.quant_utils import load_model_with_shape_infer

class BudgetedMinMaxCalibrater(MinMaxCalibrater):
    def create_inference_session(self):
        options=ort.SessionOptions()
        options.intra_op_num_threads=2;options.inter_op_num_threads=1
        options.graph_optimization_level=ort.GraphOptimizationLevel.ORT_DISABLE_ALL
        self.infer_session=ort.InferenceSession(str(self.augmented_model_path),sess_options=options,providers=['CPUExecutionProvider'])

def quantise_conv_qdq(source,dest,reader):
    assert ort.__version__=='1.23.2','Review building-block API before changing runtime version'
    model=load_model_with_shape_infer(Path(source))
    with tempfile.TemporaryDirectory(prefix='bounded-ort-calibration-') as temporary:
        calibration=BudgetedMinMaxCalibrater(Path(source),['Conv'],str(Path(temporary)/'augmented.onnx'),
                                            symmetric=False,use_external_data_format=False,moving_average=False,
                                            averaging_constant=.01,max_intermediate_outputs=None,per_channel=False)
        calibration.augment_graph();calibration.create_inference_session();calibration.collect_data(reader)
        ranges=calibration.compute_data();assert isinstance(ranges,TensorsData)
        del calibration
    quantiser=QDQQuantizer(model,True,False,QuantType.QInt8,QuantType.QUInt8,ranges,[],[],['Conv'],
                           {'WeightSymmetric':True,'ActivationSymmetric':False})
    quantiser.quantize_model();quantiser.model.save_model_to_file(str(dest),False)
    return {'runtime':'1.23.2','calibration_intra_op_threads':2,'calibration_inter_op_threads':1,
            'method':'MinMax','activation_type':'QUInt8','weight_type':'QInt8','weight_per_channel':True,
            'quantised_op_types':['Conv'],'other_operators_float':True,'library_files_modified':False}
