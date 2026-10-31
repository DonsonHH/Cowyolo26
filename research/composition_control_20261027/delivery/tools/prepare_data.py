"""Traceable aliases, identical slot counts, isolated caches; never modifies source data."""
from pathlib import Path
from collections import Counter
import hashlib,json,os
from common import *


def main():
    pp=ROOT/'protocol/composition_v1.json';p=json.loads(pp.read_text())
    source=PROJECT/'data/opencows2020/derived_detection/manifest.json'
    assert sha(source)==p['source_manifest_sha256']
    manifest=json.loads(source.read_text());train=[r for r in manifest if r['split']=='train']
    val=sorted([r for r in manifest if r['split']=='val'],key=lambda r:Path(r['image']).name)
    real=sorted([r for r in train if not r['synthetic_by_readme']],key=lambda r:hashlib.sha256(('real-only-exposure-v1:'+Path(r['image']).name).encode()).hexdigest())
    assert (len(train),len(real),len(val))==(5913,2596,370)
    assert not {r['sha256'] for r in train}&{r['sha256'] for r in manifest if r['split'] in ['val','dev_test']}
    arms={'mixed':sorted(train,key=lambda r:Path(r['image']).name),'real_repeated':real+real+real[:721]}
    audit={};checked={};root=ROOT/'data';root.mkdir(exist_ok=False)
    for name,rows in arms.items():
        assert len(rows)==5913
        records=[]
        for split,items in [('train',rows),('val',val)]:
            image_dir=root/name/'images'/split;label_dir=root/name/'labels'/split
            image_dir.mkdir(parents=True);label_dir.mkdir(parents=True)
            for slot,row in enumerate(items):
                image=Path(row['image']);label=Path(row['derived_label'])
                if str(image) not in checked:
                    assert sha(image)==row['sha256']
                    lines=[line.split() for line in label.read_text().splitlines() if line.strip()]
                    for line in lines:
                        cls,cx,cy,w,h=map(float,line)
                        assert cls==0 and w>0 and h>0 and min(cx-w/2,cy-h/2)>=-1e-8 and max(cx+w/2,cy+h/2)<=1+1e-8
                    checked[str(image)]={'image_sha256':row['sha256'],'label_sha256':sha(label),'boxes':len(lines)}
                target_name=f'{slot:05d}__{image.name}'
                alias=image_dir/target_name;alias.symlink_to(image)
                label_alias=label_dir/(Path(target_name).stem+'.txt');label_alias.symlink_to(label)
                assert alias.resolve()==image.resolve() and label_alias.resolve()==label.resolve()
                records.append({'arm':name,'split':split,'slot':slot,'alias':str(alias),'label_alias':str(label_alias),
                                'original_image':str(image),'original_label':str(label),'synthetic':row['synthetic_by_readme'],**checked[str(image)]})
        data_yaml=root/name/'data.yaml'
        data_yaml.write_text(f'path: {root/name}\ntrain: images/train\nval: images/val\nnames:\n  0: cow\n')
        counts=Counter(r['original_image'] for r in records if r['split']=='train')
        expected=Counter({1:5913}) if name=='mixed' else Counter({2:1875,3:721})
        assert Counter(counts.values())==expected
        save(root/name/'slot_manifest.json',records)
        audit[name]={'yaml':str(data_yaml),'yaml_sha256':sha(data_yaml),'slot_manifest_sha256':sha(root/name/'slot_manifest.json'),
                     'train_slots':5913,'val_slots':370,'source_file_names':len(counts),'repetition_count_distribution':dict(Counter(counts.values())),
                     'train_synthetic_slots':sum(r['synthetic'] for r in records if r['split']=='train'),
                     'train_annotation_instances':sum(r['boxes'] for r in records if r['split']=='train'),
                     'validation_source_pairs':[(r['image_sha256'],r['label_sha256']) for r in records if r['split']=='val']}
    assert audit['mixed']['validation_source_pairs']==audit['real_repeated']['validation_source_pairs']
    save(ROOT/'results/data_prepared.json',{'status':'TWO_ARM_ALIAS_DATA_AND_SOURCE_HASHES_PREPARED','job_id':os.environ['SLURM_JOB_ID'],
         'protocol_sha256':sha(pp),'source_manifest_sha256':sha(source),'checked_unique_train_val_files':len(checked),'arms':audit,
         'dev_test_image_pixels_read':False,'source_video_or_Toros_used_for_training':False,
         'augmented_parent_capture_session_leakage_resolved':False})
    print(json.dumps({'status':'DATA_PREPARED','arms':[{k:v for k,v in r.items() if k!='validation_source_pairs'} for r in audit.values()]}),flush=True)


if __name__=='__main__':main()
