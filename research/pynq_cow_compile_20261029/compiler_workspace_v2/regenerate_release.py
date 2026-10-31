"""Official checkpoint -> actual smaller FP32 -> full Conv PTQ -> deployment compiler."""
import pathlib,os,sys,argparse,shutil,json,tempfile,runpy,time,hashlib
D=pathlib.Path(__file__).resolve().parent
p=argparse.ArgumentParser();p.add_argument('--size',type=int,choices=(192,224,256),default=192);p.add_argument('--train-images',type=pathlib.Path,required=True);p.add_argument('--output',type=pathlib.Path,required=True);p.add_argument('--calibration',type=int,choices=(128,),default=128);a=p.parse_args()
assert a.size%32==0 and a.size>=128;O=a.output.resolve();assert not O.exists(),'Fresh output required';O.mkdir(parents=True)
os.environ['OMP_NUM_THREADS']='4';os.environ['YOLO_CONFIG_DIR']=str(O/'ultralytics_config');temp=O/'temporary';temp.mkdir();tempfile.tempdir=str(temp)
sys.path.insert(0,str(D/'runtime'))
import cv2,torch,onnx
from ultralytics import YOLO
from board_runtime import preprocess
from onnxruntime.quantization import quantize_static,QuantFormat,QuantType,CalibrationMethod,CalibrationDataReader
cv2.setNumThreads(4);torch.set_num_threads(4)
pt=O/'official_source.pt';shutil.copy2(D/'reproduction_inputs/yolo26n.pt',pt)
fp=pathlib.Path(YOLO(str(pt)).export(format='onnx',imgsz=a.size,batch=1,dynamic=False,opset=17,simplify=True,nms=False,device='cpu',quantize=32))
model=onnx.shape_inference.infer_shapes(onnx.load(fp),strict_mode=True,data_prop=True);onnx.checker.check_model(model);onnx.save(model,fp)
split=json.loads((D/'dataset_split.json').read_text());assert set(split['calibration']).isdisjoint(split['validation'])
class Reader(CalibrationDataReader):
 def __init__(self):self.ids=iter(split['calibration'][:a.calibration]);self.count=0
 def get_next(self):
  try:i=next(self.ids)
  except StopIteration:return None
  im=cv2.imread(str(a.train_images/('%012d.jpg'%i)));assert im is not None,str(i)
  self.count+=1
  if self.count%16==0:print('PTQ_CALIBRATION',self.count,flush=True)
  return {'images':preprocess(im,a.size)}
source=O/'allconv_int8.onnx';reader=Reader()
quantize_static(str(fp),str(source),reader,quant_format=QuantFormat.QDQ,op_types_to_quantize=['Conv'],nodes_to_quantize=[n.name for n in model.graph.node if n.op_type=='Conv'],per_channel=True,activation_type=QuantType.QInt8,weight_type=QuantType.QInt8,calibrate_method=CalibrationMethod.MinMax,extra_options={'ActivationSymmetric':False,'WeightSymmetric':True,'CalibMaxIntermediateOutputs':15})
onnx.checker.check_model(onnx.load(source));assert reader.count==a.calibration
W=O/'compiler';W.mkdir();(W/'reports/stage_d').mkdir(parents=True);M=O/'model';shutil.copy2(D/'runtime/fixed_point.py',W/'fixed_point.py');sys.path.insert(0,str(W))
for name in ('prepare_graph.py','prepare_activation.py','prepare_fixed_parameters.py'):
 text=(D/'compiler_sources'/name).read_text().replace('ROOT=pathlib.Path(__file__).resolve().parents[2]','ROOT=pathlib.Path('+repr(str(W))+')')
 text=text.replace("O=ROOT/'output/stage_d'/args.output_name",'O=pathlib.Path('+repr(str(M))+')').replace("M=ROOT/'output/stage_d'/args.model_name",'M=pathlib.Path('+repr(str(M))+')').replace('str(M.relative_to(ROOT))','str(M)')
 s=W/name;s.write_text(text);sys.argv=[str(s)]+(['--source',str(source),'--output-name','generated'] if name=='prepare_graph.py' else ['--model-name','generated']);runpy.run_path(str(s),run_name='__main__')
sys.path.insert(0,str(D/'tools'))
from compiler import enable_integer_depthwise,export_program
dw=enable_integer_depthwise(M);export_program(M,a.size,O/'program')
(O/'recipe.json').write_text(json.dumps(dict(status='O7_OFFICIAL_CHECKPOINT_EXPORT_PTQ_NATIVE_COMPILE_COMPLETE',size=a.size,calibration_images=reader.count,training=False,PT_sha256=hashlib.sha256(pt.read_bytes()).hexdigest(),source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),quantization='MinMax W8 per-output-channel symmetric / signed asymmetric A8 / INT32 bias;94 dense PL +8 ARM integer depthwise; FP32 attention/other ops',integer_depthwise_ids=dw),indent=2));print('O7_REGENERATED',O,flush=True)
