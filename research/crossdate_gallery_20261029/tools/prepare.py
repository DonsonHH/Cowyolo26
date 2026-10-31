from pathlib import Path
from datetime import datetime,timezone
import hashlib,json,zlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent;REMOTE='/share/home/renly/projects/idcoo_research_20261026'
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def save(p,v):assert not p.exists(),p;p.write_text(json.dumps(v,indent=2)+'\n',encoding='utf-8')
def main():
    source=PROJECT/'identity_source_provenance_20261029';entries=load(source/'evidence/zip_directory/entries.json')
    info=load(source/'evidence/zip_metadata/info.json');file_records={}
    def walk(r):
        if isinstance(r,dict):
            if 'sha1' in r and 'id' in r:file_records[r['id']]=r
            for x in r.values():walk(x)
        elif isinstance(r,list):
            for x in r:walk(x)
    walk(info)
    old=load(PROJECT/'confirmed12_capture_identity_20261029/protocol/chain_v1.json')
    indexfile=PROJECT/'identity_training_20261026/delivery/results/study/feature_index.json';index=load(indexfile)
    labels=sorted({r['identity'] for r in index['evaluation_gallery']});assert labels==['009','020','026','028','031','054']
    new=[];directory_counts={}
    for identity in labels:
        prefix='2inu67jru7a6821kkgehxg3cv2/MultiCamCows2024Root/2023Aug19/'+identity+'/'
        eligible=sorted([r for r in entries if r['name'].startswith(prefix) and r['name'].endswith('_1.jpg')],key=lambda r:r['name'])
        assert len(eligible)>=5;indices=[round(i*(len(eligible)-1)/4) for i in range(5)];assert len(set(indices))==5
        directory_counts[identity]=len(eligible)
        for position in indices:
            r=eligible[position];meta=file_records[r['name']];assert int(meta['extent']['@value'])==r['bytes']
            filename=Path(r['name']).name;new.append({'identity':identity,'day':'2023Aug19','camera':1,'gallery_name':'new_Aug19',
                'source_filename':filename,'source_sequence_position':position,'source_sequence_length':len(eligible),
                'url':'https://data.bris.ac.uk/datasets/'+r['name'],
                'relative_file':'data/2023Aug19/'+identity+'/'+filename,'official_bytes':r['bytes'],'official_CRC32':r['CRC32'],
                'official_SHA1':meta['sha1'],'official_archive_member':r['name']})
    def existing(row,kind):
        f=PROJECT/'identity_training_20261026/delivery'/row['relative_path'];assert sha(f)==row['sha256']
        return {**row,'path':REMOTE+'/identity_training/'+row['relative_path'],'local_path':str(f.resolve()),'input_kind':kind}
    old_gallery=[existing(r,'old_Aug14_gallery') for r in index['evaluation_gallery']]
    labelled=[existing(r,'labelled_curated_query') for r in index['evaluation_query']];assert len(labelled)==60
    events=load(PROJECT/'confirmed12_capture_identity_20261029/delivery/results/replay/events.json');real=[]
    for e in events:
        s=e['selected_snapshot'];f=PROJECT/'confirmed12_capture_identity_20261029/delivery/results/replay'/s['oriented_path']
        assert sha(f)==s['oriented_sha256']
        real.append({'query_id':e['event_id'],'input_kind':'real_event_query','day':'2023Aug14','source_frame0':s['frame0'],
            'event_source_frame0':e['frame0'],'path':REMOTE+'/confirmed12_capture_identity_20261029/results/replay/'+s['oriented_path'],
            'local_path':str(f.resolve()),'sha256':sha(f),'identity_reference':None})
    protocol=ROOT/'protocol';protocol.mkdir(exist_ok=False);inputs=ROOT/'input';inputs.mkdir(exist_ok=False)
    save(inputs/'new_gallery_selection.json',new);save(inputs/'old_gallery.json',old_gallery);save(inputs/'labelled_queries.json',labelled);save(inputs/'real_event_queries.json',real)
    for name,src in [('training_primitives.py',PROJECT/'identity_training_20261026/tools/training_primitives.py'),
                     ('identity_metrics.py',PROJECT/'identity_training_20261026/tools/identity_metrics.py')]:
        (inputs/name).write_bytes(src.read_bytes())
    source_models=load(PROJECT/'identity_training_20261026/delivery/results/study/summary.json')
    expected={r['name']:r['evaluation'] for r in source_models['conditions']}
    baseline=[]
    for c in old['identity']['conditions']:
        path=PROJECT/'identity_training_20261026/delivery/results/study'/c['name']/'evaluation_predictions.json'
        feature=path.with_name('evaluation_embeddings.npz')
        baseline.append({'condition':c['name'],'prediction_path':REMOTE+'/identity_training/results/study/'+c['name']+'/evaluation_predictions.json',
            'local_prediction_path':str(path.resolve()),'prediction_sha256':sha(path),'feature_path':REMOTE+'/identity_training/results/study/'+c['name']+'/evaluation_embeddings.npz',
            'local_feature_path':str(feature.resolve()),'feature_sha256':sha(feature),'expected_summary':expected[c['name']]})
    p={'name':'Fixed fiveencoders and thresholds, Aug14vsAug19gallery on existing curated and realevent queries',
        'created_UTC':datetime.now(timezone.utc).isoformat(),'source_provenance_final_sha256':sha(source/'results/final_review.json'),
        'source_pair_exclusion_sha256':sha(source/'results/evaluation_admission.json'),'official_index_sha256':sha(source/'evidence/zip_directory/entries.json'),
        'official_info_sha256':sha(source/'evidence/zip_metadata/info.json'),'registered_IDs':labels,'new_gallery_day':'2023Aug19',
        'new_gallery_directory_camera1_counts':directory_counts,'new_gallery_images':30,'old_gallery_images':30,'labelled_query_images':60,'real_event_query_images':12,
        'selection':'Sorted officialcamera1filenames;5uniform positions incl endpoints perID, before image download and model scoring.',
        'conditions':old['identity']['conditions'],'baselines':baseline,'gallery_conditions':['old_Aug14','new_Aug19'],
        'retrieval':'L2normalized576dim embeddings;maxcosine over5gallery images perID then maxidentity;originalfixedthresholds;ties earlier sortedanonymousID.',
        'input_module_sha256':{f.name:sha(f) for f in inputs.iterdir() if f.is_file()},
        'new_gallery_file_integrity':'Official size,CRC32,SHA1 then localSHA256;fullimage decode and pixelduplicate checks before model gate.',
        'old_baseline_tolerances':{'maximum_feature_absolute_difference':1e-5,'maximum_similarity_absolute_difference':1e-5,'candidate_and_acceptance_exact':True},
        'all_conditions_retained':True,'new_training_updates':0,'new_threshold_optimisation':False,
        'Aug20curated_queries_previously_used_development':True,'Aug14event_withAug19gallery_is_retrospective_not_deployment_chronology':True,
        'real_event_identity_reference_available':False,'source_ID009_evidence_does_not_enable_event_accuracy_scoring':True,
        'new_independent_test':False,'RF_hardware_connected':False,'FPGA_execution_verified':False,'whole_goal_complete':False}
    save(protocol/'study_v1.json',p)
    print(json.dumps({'protocol_sha256':sha(protocol/'study_v1.json'),'new_gallery':30,'labelled_queries':60,'real_event_queries':12,
                      'models':5,'paired_model_gallery_conditions':10,'newgallery_directory_counts':directory_counts}))
if __name__=='__main__':main()
