"""Apply the metadata-only date rules after full recovery verification, never train."""
from pathlib import Path
from collections import Counter,defaultdict
from datetime import date,datetime
import csv,hashlib,json
ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    verified=ROOT/'results/source_recovery_independent_verification.json'
    assert verified.exists(),'Complete XML provenance verification required before date grouping'
    verification=json.loads(verified.read_text(encoding='utf-8'))
    assert verification['status']=='ALL_10402_XML_HASHES_FIELDS_AND_ROLE_OVERLAPS_INDEPENDENTLY_VERIFIED'
    path=ROOT/'results/source_metadata_all.json';assert sha(path)==verification['source_metadata_sha256']
    source=json.loads(path.read_text(encoding='utf-8'))
    pp=ROOT/'protocol/date_grouping_candidate_v1.json';p=json.loads(pp.read_text(encoding='utf-8'))
    rows=[];date_roles=defaultdict(set);by_source=defaultdict(set);counts=Counter();published=defaultdict(Counter)
    by_date=defaultdict(Counter)
    for row in source:
        role='quarantine_metadata';day=row['capture_date']
        if day:
            try:
                date.fromisoformat(day);datetime.fromisoformat(row['capture_timestamp'])
                hits=[r['role'] for r in p['rules_in_order'] if r['first_date']<=day<=r['last_date']]
                assert len(hits)<=1
                if hits:role=hits[0]
            except (ValueError,TypeError):pass
        rows.append({'file_name':row['file_name'],'published_role':row['role'],'candidate_date_role':role,
                     'capture_date':day,'capture_timestamp':row['capture_timestamp'],'source_block':row['source_block'],
                     'original_filename':row['original_filename'],'original_frame_index':row['original_frame_index'],
                     'XML_sha256':row['XML_sha256'],'image_bytes_verified':False,'final_test_eligibility_verified':False})
        counts[role]+=1;published[row['role']][role]+=1;by_date[str(day)][role]+=1
        if day:date_roles[day].add(role)
        by_source[row['original_filename']].add(role)
    assert len(rows)==10402 and all(len(r)==1 for r in date_roles.values())
    assert all(len(r)==1 for r in by_source.values()),'A repeated original filename crosses proposed roles'
    final_dates={r['capture_date'] for r in rows if r['candidate_date_role']=='candidate_final_date_holdout'}
    assert final_dates and final_dates.issubset({'2020-03-10','2020-03-11'})
    assert not final_dates.intersection(p['previously_observed_raw_video_dates'])
    out=ROOT/'results/date_roles_v1';out.mkdir(exist_ok=False)
    (out/'manifest.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    with (out/'manifest.csv').open('w',newline='',encoding='utf-8-sig') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    result={'status':'DATE_GROUPED_CANDIDATE_ROLES_FIXED_METADATA_ONLY','protocol_sha256':sha(pp),
            'metadata_sha256':sha(path),'provenance_verification_sha256':sha(verified),'manifest_sha256':sha(out/'manifest.json'),
            'counts':dict(counts),'dates':{k:dict(v) for k,v in sorted(by_date.items())},
            'published_to_candidate_roles':{k:dict(v) for k,v in published.items()},
            'dates_shared_across_candidate_roles':False,'same_original_filename_crosses_candidate_roles':False,
            'candidate_final_dates':sorted(final_dates),'prior_development_raw_dates_excluded_from_candidate_final':True,
            'image_integrity_and_cross_dataset_source_overlap_verified':False,'final_independent_test_certified':False,
            'model_training_or_forward_performed':False,'whole_goal_complete':False}
    (out/'summary.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ['dates','published_to_candidate_roles']}),flush=True)


if __name__=='__main__':main()
