"""Independent complete-XML hash/provenance check, without trusting a progress file."""
from pathlib import Path
from collections import Counter,defaultdict
from datetime import date,datetime
import hashlib,json,re,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    summary_path=ROOT/'results/source_recovery_summary.json'
    assert summary_path.exists(),'Complete recovery result not available; keep observing the existing process'
    source=json.loads((ROOT/'results/source_metadata_all.json').read_text(encoding='utf-8'))
    summary=json.loads(summary_path.read_text(encoding='utf-8'))
    assert summary['status']=='ALL_10402_PUBLIC_XML_SOURCE_METADATA_RECOVERED' and len(source)==10402
    assert len({r['file_name'] for r in source})==10402
    metadata={};by_name={r['file_name']:r for r in source}
    observed_dates=defaultdict(Counter);observed_blocks=defaultdict(Counter);bad_dates=[];original_names=defaultdict(list)
    for role,filename in [('train','train_annotations.json'),('validation','validation_annotations.json'),('reserved_test','reserved_test_annotations.json')]:
        data=json.loads((ROOT/'catalog'/filename).read_text(encoding='utf-8'))
        listing={'train':'train_train_image_listing.html.record.json',
                 'validation':'train_val_image_listing.html.record.json',
                 'reserved_test':'reserved_test_image_listing.html.record.json'}[role]
        observed_links=json.loads((ROOT/'catalog'/listing).read_text(encoding='utf-8'))['links']
        expected_urls={u.rsplit('/',1)[-1]:u for u in observed_links if u.endswith('.xml')}
        for image in data['images']:
            name=image['file_name'];row=by_name[name]
            assert row['role']==role
            assert row['XML_url']==expected_urls[Path(name).with_suffix('.xml').name]
            path=ROOT/'source_XML'/role/Path(name).with_suffix('.xml')
            assert path.is_file() and path.stat().st_size==row['XML_bytes'] and digest(path)==row['XML_sha256']
            root=ET.parse(path).getroot();original=root.findtext('filename') or ''
            assert original==row['original_filename'] and root.findtext('folder')==row['source_block']
            assert int(root.findtext('size/width'))==row['width']==image['width']
            assert int(root.findtext('size/height'))==row['height']==image['height']
            actual_types=Counter((obj.findtext('type') or 'unspecified')+':'+(obj.findtext('name') or '') for obj in root.findall('object'))
            assert dict(actual_types)==row['object_types']
            # Independent component parsing of the source filename.
            pieces=original.removesuffix('.jpg').split('_')
            extracted=None
            if len(pieces)==4 and pieces[0]=='image' and pieces[1].isdigit():
                day=pieces[2];time_parts=pieces[3].split('-')
                if re.fullmatch(r'\d{4}-\d{2}-\d{2}',day) and len(time_parts)==3 and all(p.isdigit() for p in time_parts):
                    normalized=day+'T'+':'.join(f'{int(p):02d}' for p in time_parts)
                    extracted=(int(pieces[1]),day,normalized)
            if extracted:
                assert extracted==(row['original_frame_index'],row['capture_date'],row['capture_timestamp'])
                try:datetime.fromisoformat(extracted[2])
                except ValueError:bad_dates.append({'file_name':name,'capture_timestamp':extracted[2]})
            else:
                assert row['capture_date'] is None and row['capture_timestamp'] is None and row['original_frame_index'] is None
            assert row['session_ID_verified'] is False
            original_names[original].append({'role':role,'file_name':name,'date':row['capture_date']})
            observed_dates[row['capture_date']][role]+=1;observed_blocks[row['source_block']][role]+=1
            metadata[name]={'XML_sha256':row['XML_sha256'],'role':role,'capture_date':row['capture_date']}
    assert len(metadata)==10402 and Counter(r['role'] for r in source)==summary['roles']
    actual_dates={str(k):dict(v) for k,v in observed_dates.items()}
    expected_dates={str(k):v for k,v in summary['dates'].items()}
    assert actual_dates==expected_dates
    assert {str(k):dict(v) for k,v in observed_blocks.items()}=={str(k):v for k,v in summary['blocks'].items()}
    overlaps={str(k):dict(v) for k,v in observed_dates.items() if len(v)>1}
    assert overlaps=={str(k):v for k,v in summary['dates_shared_across_published_roles'].items()}
    source_duplicates={k:v for k,v in original_names.items() if len(v)>1}
    result={'status':'ALL_10402_XML_HASHES_FIELDS_AND_ROLE_OVERLAPS_INDEPENDENTLY_VERIFIED',
            'XML_count':10402,'source_metadata_sha256':digest(ROOT/'results/source_metadata_all.json'),
            'source_summary_sha256':digest(summary_path),'roles':dict(Counter(r['role'] for r in source)),
            'capture_dates':actual_dates,'dates_shared_across_published_roles':overlaps,
            'source_name_duplicate_groups':source_duplicates,'bad_ISO_capture_timestamps':bad_dates,
            'missing_capture_dates':sum(r['capture_date'] is None for r in source),
            'source_block_verified_as_video_session':False,'image_pixels_examined_by_this_check':False,
            'new_model_forward_or_training':False,'whole_goal_complete':False}
    target=ROOT/'results/source_recovery_independent_verification.json'
    assert not target.exists();target.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['capture_dates','source_name_duplicate_groups']}),flush=True)


if __name__=='__main__':main()
