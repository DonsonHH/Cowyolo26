from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
p=json.loads((ROOT/'protocol/study_v1.json').read_text())
p['version']=2;p['original_protocol_sha256']=sha(ROOT/'protocol/study_v1.json')
p['previous_CPU_gallery_reference']={'path':'/share/home/renly/projects/idcoo_research_20261026/confirmed12_capture_identity_20261029/results/replay/gallery_vectors.json',
'local_path':str((PROJECT/'confirmed12_capture_identity_20261029/delivery/results/replay/gallery_vectors.json').resolve()),
'sha256':sha(PROJECT/'confirmed12_capture_identity_20261029/delivery/results/replay/gallery_vectors.json')}
p['numerical_gate_revision']={'reason':'Failedattempt130422C28GPUgallerymaxcomponentdelta1.2129545211791992e-5;all60predictions/acceptancesandmetricsunchanged;maxscore9.722674536027931e-6beloworiginal1e-5.',
'old_GPU_component_delta':'Retainedandreporteddiagnostic,notusedtoadmitnewgallery.',
'current_gate':'ActualoldCPUgalleryfeaturecomponentdelta<=original1e-5;oldGPUmaxcosinescoredelta<=original1e-5;exactall60candidate/acceptance/metrics.',
'models_thresholds_selection_queries_same_as_v1':True,'new_gallery_results_from_failedattempt_examined_to_change_gate':False}
out=ROOT/'protocol/study_v2.json';assert not out.exists();out.write_text(json.dumps(p,indent=2)+'\n')
print(sha(out))
