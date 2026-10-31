"""Read public annotation metadata and supplied folds, without opening held-out images."""
from pathlib import Path
from collections import Counter,defaultdict
import hashlib,json,zipfile,xml.etree.ElementTree as ET

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent
ARCHIVE=Path('C:/Users/Donson/Downloads/10m32xl88x2b61zlkkgz3fml17.zip/10m32xl88x2b61zlkkgz3fml17.zip')


def main():
    manifest_path=BASE/'detector_training_20261027/delivery/results/training/manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    by_name={Path(r['image']).name:r for r in manifest};assert len(by_name)==7043
    by_hash=defaultdict(list)
    for name,row in by_name.items():by_hash[row['sha256']].append(name)
    duplicates=[(h,sorted(names)) for h,names in by_hash.items() if len(names)>1]
    assert len(duplicates)==69
    prefix='10m32xl88x2b61zlkkgz3fml17/detection_and_localisation/'
    metadata=[];shapes=Counter();tagsets=Counter();mismatches=[]
    with zipfile.ZipFile(ARCHIVE) as archive:
        xml_names=sorted(n for n in archive.namelist() if n.startswith(prefix+'labels-xml/') and n.endswith('.xml'))
        assert len(xml_names)==7043
        for path in xml_names:
            value=ET.fromstring(archive.read(path))
            basename=Path(path).stem+'.jpg';filename=value.findtext('filename')
            if filename!=basename:mismatches.append({'xml':Path(path).name,'filename':filename})
            tags=sorted({r.tag for r in value});tagsets['|'.join(tags)]+=1
            width=int(value.findtext('size/width'));height=int(value.findtext('size/height'))
            shapes[(width,height)]+=1
            metadata.append({'image':basename,'filename_matches_XML_basename':filename==basename,'width':width,'height':height,
                             'objects':len(value.findall('object')),'has_source_field':value.find('source') is not None,
                             'has_path_field':value.find('path') is not None})
        folds=json.loads(archive.read(prefix+'10-fold-CV.json'))
        fold_records=[]
        for key,value in folds.items():
            assert set(value)=={'train','test'}
            train,test=set(value['train']),set(value['test'])
            assert len(train)==len(value['train']) and len(test)==len(value['test'])
            assert not train&test and train|test==set(by_name)
            cross=[]
            for h,names in duplicates:
                a=sorted(train.intersection(names));b=sorted(test.intersection(names))
                if a and b:cross.append({'image_sha256':h,'train_filenames':a,'test_filenames':b})
            fold_records.append({'fold':key,'train_images':len(train),'test_images':len(test),
                                 'train_synthetic_images':sum(by_name[n]['synthetic_by_readme'] for n in train),
                                 'test_synthetic_images':sum(by_name[n]['synthetic_by_readme'] for n in test),
                                 'identical_bytes_groups_crossing_supplied_train_test':len(cross),'cross_groups':cross})
        cv_digest=hashlib.sha256(archive.read(prefix+'10-fold-CV.json')).hexdigest()
    out=ROOT/'results/archive_metadata';out.mkdir(parents=True,exist_ok=False)
    (out/'XML_metadata.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    result={'status':'ALL_7043_XML_AND_10_SUPPLIED_FOLDS_REVIEWED_METADATA_ONLY','archive_bytes':ARCHIVE.stat().st_size,
            'existing_verified_archive_sha256':'53c437eb2e383092967d218655afac74a20403850ab9dde1d136a570d948362c',
            'prior_image_manifest_sha256':hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            'XML_count':len(metadata),'XML_root_tag_sets':dict(tagsets),'XML_filename_mismatches':mismatches,
            'XML_with_source_fields':sum(r['has_source_field'] for r in metadata),
            'XML_with_path_fields':sum(r['has_path_field'] for r in metadata),
            'image_dimensions_metadata':[{ 'width':w,'height':h,'count':n} for (w,h),n in sorted(shapes.items())],
            'supplied_CV_sha256':cv_digest,'supplied_folds':fold_records,
            'synthetic_parent_or_capture_session_linkage_resolved':False,
            'current_training_split_modified':False,'held_out_image_pixels_opened':False,
            'scope':'Current distributed archive metadata; does not establish what files or splits were used for all experiments in the publication'}
    (out/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({'status':result['status'],'root_tags':result['XML_root_tag_sets'],
                      'filename_mismatches':len(mismatches),'source_fields':result['XML_with_source_fields'],
                      'path_fields':result['XML_with_path_fields'],
                      'supplied_fold_cross_duplicate_groups':[r['identical_bytes_groups_crossing_supplied_train_test'] for r in fold_records]}),flush=True)


if __name__=='__main__':main()
