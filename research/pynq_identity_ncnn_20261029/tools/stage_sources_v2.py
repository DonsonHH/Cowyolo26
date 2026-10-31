"""Fetch official pinned converter/runtime sources without touching the board."""
from pathlib import Path
from datetime import datetime,timezone
import json,urllib.request,hashlib,tarfile
PROJECT=Path(__file__).resolve().parents[2];ROOT=PROJECT/'pynq_identity_ncnn_20261029'
ROOT.mkdir(exist_ok=True)
for name in ['tools','protocol','input','evidence','sources','results']:(ROOT/name).mkdir(exist_ok=True)
def get(url):
 req=urllib.request.Request(url,headers={'User-Agent':'cow-research-artifact-staging','Accept':'application/json'})
 with urllib.request.urlopen(req,timeout=45) as response:return response.read()
def sha(data):return hashlib.sha256(data).hexdigest()
rows=[]
for package in ['pnnx','ncnn']:
 version={'pnnx':'20261020','ncnn':'1.0.20261020'}[package]
 metadata=json.loads(get('https://pypi.org/pypi/'+package+'/'+version+'/json'))
 (ROOT/'evidence'/(package+'_pypi_metadata_v2.json')).write_text(json.dumps(metadata,indent=2)+'\n')
 candidates=[r for r in metadata['urls'] if 'x86_64' in r['filename'] and ('manylinux' in r['filename']) and (package=='pnnx' or 'cp313' in r['filename'])]
 assert candidates,(package,[r['filename'] for r in metadata['urls']])
 selected=sorted(candidates,key=lambda r:r['filename'])[0]
 destination=ROOT/'sources'/selected['filename']
 content=destination.read_bytes() if destination.exists() else get(selected['url'])
 assert len(content)==selected['size'] and sha(content)==selected['digests']['sha256']
 if not destination.exists():destination.write_bytes(content)
 rows.append({'package':package,'version':version,'file':selected['filename'],'source_URL':selected['url'],'bytes':len(content),'sha256':sha(content)})
 print(json.dumps(rows[-1]),flush=True)
url='https://api.github.com/repos/Tencent/ncnn/git/ref/tags/20261020';ref=json.loads(get(url))
(ROOT/'evidence/ncnn_tag_ref.json').write_text(json.dumps(ref,indent=2)+'\n')
url='https://codeload.github.com/Tencent/ncnn/tar.gz/refs/tags/20261020';content=get(url)
(ROOT/'sources/ncnn-20261020.tar.gz').write_bytes(content)
rows.append({'package':'ncnn_source','version':'20261020','file':'ncnn-20261020.tar.gz','source_URL':url,'bytes':len(content),'sha256':sha(content),'tag_object':ref['object']})
(ROOT/'evidence/source_staging.json').write_text(json.dumps({'created_UTC':datetime.now(timezone.utc).isoformat(),'artifacts':rows,'board_changes':0,'model_execution':0},indent=2)+'\n')
with tarfile.open(ROOT/'sources/ncnn-20261020.tar.gz') as tar:
 for name in ['ncnn-20261020/CMakeLists.txt','ncnn-20261020/src/CMakeLists.txt','ncnn-20261020/cmake/ncnn_add_layer.cmake','ncnn-20261020/LICENSE.txt']:
  if name in tar.getnames():(ROOT/'evidence'/Path(name).name).write_bytes(tar.extractfile(name).read())
(ROOT/'部署依据与计划.md').write_text('''# PYNQ同板后台身份编码器：部署依据与计划

实时YOLO输出是cow框和临时track ID。永久奶牛身份仍需已注册花纹图库与身份编码器；使用现有MobileNetV3-small的576维特征，不把YOLO类别当作具体身份。

现有板卡缺Torch。ncnn官方列出ARM NEON／C++部署能力，并提供pnnx从PyTorch导出的路径，因此先检验这一路径；这属于实现可行性依据，尚不是本模型已在PYNQ执行或达成并发吞吐的证据。[ncnn官方仓库](https://github.com/Tencent/ncnn) · [官方PyTorch转换说明](https://github.com/Tencent/ncnn/wiki/use-ncnn-with-pytorch-or-onnx) · [官方ARM构建说明](https://ncnn.readthedocs.io/en/latest/how-to-build/how-to-build.html)

版本固定20261020，PyPI轮子校验发布方SHA-256，源码固定同名tag并保存GitHub tag对象。先在Slurm隔离环境导出现有seed26编码器，按原预处理和图库核对全部特征／排序，再在板上编译仅需算子、执行同组向量及真实查询。不得在当前前台性能回放期间进行板端编译或后台推理，以免混淆前台基线。

原人工12事件查询没有永久身份真值，Aug14同次通行图库已排除独立评价。保持既定跨日期图库与拒识门限；端侧特征和排序复现只是部署一致性，不能代替真实掉标身份找回准确率。最终仍需在同一块板卡测真实检测、触发抓拍、后台检索、队列时延、前台5Hz丢帧和资源竞争。
''',encoding='utf-8')
print(json.dumps({'phase':str(ROOT),'source_files':len(rows),'total_bytes':sum(r['bytes'] for r in rows),'model_execution':0,'board_changes':0}))
