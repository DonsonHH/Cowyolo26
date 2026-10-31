"""Separate CPU process running real frozen encoders, not a score cache."""
import hashlib,json,os,time,traceback,resource
from pathlib import Path

def worker_main(job_queue,result_queue,protocol,project_path):
    os.environ['CUDA_VISIBLE_DEVICES']=''
    os.environ['OMP_NUM_THREADS']='2';os.environ['OPENBLAS_NUM_THREADS']='2'
    try:
        import numpy as np
        from PIL import Image
        import torch
        from torchvision.models import mobilenet_v3_small,MobileNet_V3_Small_Weights
        import sys
        project=Path(project_path);study=project/'identity_training/results/study'
        sys.path.insert(0,str(project/'identity_training/tools'))
        from training_primitives import BodyTransform
        torch.set_num_threads(2);torch.set_num_interop_threads(1)
        assert not torch.cuda.is_available(),'Identity worker must remain CPU-only'
        index_path=study/'feature_index.json'
        assert hashlib.sha256(index_path.read_bytes()).hexdigest()==protocol['identity']['feature_index_sha256']
        assert hashlib.sha256((study/'summary.json').read_bytes()).hexdigest()==protocol['identity']['study_summary_sha256']
        entries=json.loads(index_path.read_text())['evaluation_gallery'];labels=sorted({r['identity'] for r in entries})
        assert len(entries)==30 and len(labels)==6
        models={};gallery={};transforms={};initialised=time.monotonic_ns()
        pretrained=None
        for condition in protocol['identity']['conditions']:
            checkpoint=Path(condition['checkpoint']);assert hashlib.sha256(checkpoint.read_bytes()).hexdigest()==condition['checkpoint_sha256']
            if condition['seed'] is None and pretrained is not None:encoder=pretrained
            else:
                base=mobilenet_v3_small(weights=None)
                if condition['seed'] is None:base.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True))
                encoder=torch.nn.Sequential(base.features,base.avgpool,torch.nn.Flatten()).eval()
                if condition['seed'] is not None:encoder.load_state_dict(torch.load(checkpoint,map_location='cpu',weights_only=True))
                for parameter in encoder.parameters():parameter.requires_grad_(False)
                if condition['seed'] is None:pretrained=encoder
            transform=MobileNet_V3_Small_Weights.IMAGENET1K_V1.transforms() if condition['preprocess']=='official' else BodyTransform()
            batch=[]
            for row in entries:
                with Image.open(project/'identity_training'/row['relative_path']) as im:batch.append(transform(im.convert('RGB')))
            with torch.inference_mode():vectors=torch.nn.functional.normalize(encoder(torch.stack(batch)),dim=1).numpy()
            models[condition['name']]=encoder;gallery[condition['name']]=vectors;transforms[condition['name']]=transform
        result_queue.put({'kind':'ready','pid':os.getpid(),'device':'cpu','threads':torch.get_num_threads(),'conditions':len(models),
                          'gallery_identities':labels,'gallery_images':30,'gallery_build_ns':time.monotonic_ns()-initialised,
                          'monotonic_clock':time.get_clock_info('monotonic').implementation},timeout=10)
        while True:
            job=job_queue.get()
            if job is None:break
            started=time.monotonic_ns()
            if started>job['deadline_wall_ns']:
                result_queue.put({'kind':'result','event_id':job['event_id'],'status':'EXPIRED_WAITING','worker_pid':os.getpid(),
                                  'started_wall_ns':started,'finished_wall_ns':time.monotonic_ns(),'conditions':[]},timeout=10);continue
            try:
                file=Path(job['oriented_crop_path']);assert hashlib.sha256(file.read_bytes()).hexdigest()==job['oriented_crop_sha256']
                with Image.open(file) as im:im.load();image=im.convert('RGB')
                outputs=[]
                for condition in protocol['identity']['conditions']:
                    before=time.monotonic_ns();tensor=transforms[condition['name']](image).unsqueeze(0)
                    with torch.inference_mode():feature=torch.nn.functional.normalize(models[condition['name']](tensor),dim=1).numpy()[0]
                    similarities=gallery[condition['name']].astype(float)@feature.astype(float)
                    scores=[max(float(similarities[i]) for i,r in enumerate(entries) if r['identity']==label) for label in labels]
                    best=int(np.argmax(scores))
                    outputs.append({'condition':condition['name'],'candidate_anonymous_id':labels[best],'cosine_similarity':scores[best],
                                    'frozen_threshold':condition['threshold'],'passes_frozen_threshold':scores[best]>=condition['threshold'],
                                    'verified_identity':False,'model_sha256':condition['checkpoint_sha256'],
                                    'feature_norm':float(np.linalg.norm(feature)),'feature_vector':feature.tolist(),
                                    'preprocess_and_forward_and_matching_ns':time.monotonic_ns()-before})
                finished=time.monotonic_ns()
                result_queue.put({'kind':'result','event_id':job['event_id'],'status':'COMPLETED' if finished<=job['deadline_wall_ns'] else 'COMPLETED_LATE',
                                  'worker_pid':os.getpid(),'started_wall_ns':started,'finished_wall_ns':finished,
                                  'decoded_oriented_size':list(image.size),'conditions':outputs},timeout=10)
            except Exception as error:
                result_queue.put({'kind':'result','event_id':job['event_id'],'status':'TASK_FAILED','worker_pid':os.getpid(),
                                  'started_wall_ns':started,'finished_wall_ns':time.monotonic_ns(),
                                  'error_type':type(error).__name__,'error_detail':str(error)[:500],'conditions':[]},timeout=10)
        result_queue.put({'kind':'stopped','pid':os.getpid(),'maximum_rss_kib':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss},timeout=10)
    except Exception as error:
        result_queue.put({'kind':'fatal','pid':os.getpid(),'error_type':type(error).__name__,'error_detail':str(error)[:500]},timeout=10)
        raise
