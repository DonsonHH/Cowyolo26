"""Archive research deliverables, excluding model/data payloads per user request."""
from pathlib import PurePosixPath
import re
DEP_DIRS={'.git','__pycache__','.pytest_cache','.mypy_cache','node_modules','env','.venv','venv',
          'deps','tool_deps','serial_deps','local_deps','local_dependencies','site-packages',
          'wheelhouse','wheels','mpl_cache','mplconfig','font_cache'}
DATA_DIRS={'data','datasets','dataset','labels','images','frames','highres','lowres','camera_delivery',
           'original_images','raw_images','zip-files'}
MODEL_EXT={'.pt','.pth','.onnx','.bin','.npy','.npz','.safetensors','.pkl','.pickle','.ckpt','.pb',
           '.bit','.so','.dll','.pyd','.a','.o','.obj','.lib','.exe','.pyc','.whl'}
TEXT_EXT={'.md','.txt','.json','.jsonl','.csv','.tsv','.yaml','.yml','.toml','.ini','.cfg','.conf',
          '.xml','.py','.sh','.ps1','.bat','.cmd','.slurm','.html','.htm','.js','.mjs','.ts','.tsx',
          '.jsx','.css','.ipynb','.sql','.c','.cc','.cpp','.h','.hh','.hpp','.inc','.v','.vh','.sv','.svh',
          '.tcl','.xdc','.xpr','.hwh','.hls','.param','.prototxt','.patch','.diff','.log','.out','.err',
          '.rst','.f','.f90','.mk','.cmake','.text','.drawio','.mmd','.mermaid','.tex','.bib','.rpt','.jou',
          '.vhd','.vhdl','.proto','.dts','.dtsi','.xci','.bd','.prj','.sdc','.lock'}
META_WORDS=('manifest','metadata','protocol','summary','review','admission','mapping','catalog','split','inventory','config','info','provenance','readme','license','notice')
def choose(relative,size):
    path=PurePosixPath(relative);parts=[p.lower()for p in path.parts];name=parts[-1];ext=path.suffix.lower()
    if any(p in DEP_DIRS or p.endswith(('_deps','_dependencies'))for p in parts[:-1]):return False,'third_party_dependency_or_cache'
    if ext in MODEL_EXT:return False,'model_tensor_firmware_or_compiled_binary'
    if name.endswith(('.tar.gz','.tar.xz','.tar.zst','.tgz','.tar','.zip','.7z','.rar','.xz','.zst')):return False,'bulk_transport_archive'
    if name.endswith(('.json.gz','.jsonl.gz','.csv.gz','.tsv.gz')):
        return (True,'compressed_text_evidence')if size<=8*1024*1024 else(False,'large_raw_text_output')
    if ext in TEXT_EXT or name in{'license','notice','makefile','dockerfile','cmakelists.txt','.gitignore','.gitattributes'}:
        if size>8*1024*1024:return False,'large_raw_text_output'
        if ext in{'.json','.jsonl','.csv','.tsv'}and size>2*1024*1024 and not any(w in name for w in('summary','review','verification','protocol','config')):return False,'bulk_per_sample_or_dataset_listing'
        if ext=='.xml'and not any(w in name for w in('config','schema','manifest','project'))and not any(p in{'hardware','ip','design'}for p in parts[:-1]):return False,'dataset_xml_annotation'
        if any(p in DATA_DIRS for p in parts[:-1])and ext in{'.txt','.xml','.json','.csv','.tsv'}and not any(w in name for w in META_WORDS):return False,'dataset_annotation_payload'
        return True,'report_source_config_metric_or_log'
    if ext in{'.jpg','.jpeg'}:return False,'individual_dataset_or_validation_frame'
    if ext in{'.svg','.png','.gif','.webp','.pdf'}:
        if size>4*1024*1024:return False,'large_image_or_document_payload'
        if any(p in DATA_DIRS for p in parts[:-1]):return False,'dataset_or_input_image'
        visual=(ext=='.svg' or any('panel'in p or p.startswith(('figures','actual_photos'))for p in parts[:-1])
                or any(w in name for w in('panel','plot','figure','chart','contact','diagnos','comparison','dashboard','heatmap','curve','histogram','confusion','pareto','latency','timing','coverage','scores','overview','sheet')))
        return (True,'derived_visual_result')if visual else(False,'source_media_or_unclassified_image')
    if ext=='.mp4':return False,'video_payload_retained_at_source'
    return False,'non_review_payload'
