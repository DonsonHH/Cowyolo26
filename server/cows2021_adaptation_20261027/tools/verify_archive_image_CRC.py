"""Slurm-only independent byte reconciliation with official ZIP member CRCs."""
from pathlib import Path
from collections import Counter
import hashlib,json,os,socket,zlib,time

ROOT=Path(__file__).resolve().parents[1]


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    started=time.perf_counter()
    source=ROOT/'results/archive_index_probe/selected_members.json'
    members=json.loads(source.read_text());assert len(members)==8380
    expected={r['file_name']:r for r in members};assert len(expected)==8380
    folder=ROOT/'results/download_attempt_02'
    summary=json.loads((folder/'summary.json').read_text())
    assert summary['status']=='ALL_8380_DEVELOPMENT_IMAGE_BYTES_STAGED_DECODE_PENDING'
    manifest_path=folder/'image_manifest.json'
    assert sha(manifest_path)==summary['image_manifest_sha256']
    images=json.loads(manifest_path.read_text());assert len(images)==8380
    assert {r['file_name'] for r in images}==set(expected)
    records=[];mismatches=[]
    for row in images:
        member=expected[row['file_name']]
        path=ROOT/row['relative_image_path'];assert path.resolve().is_relative_to(ROOT/'raw_images')
        data=path.read_bytes();native_crc=zlib.crc32(data)&0xffffffff
        ok=(native_crc==member['CRC32'] and len(data)==member['uncompressed_size']
            and hashlib.sha256(data).hexdigest()==row['sha256'])
        record={'file_name':row['file_name'],'development_role':row['development_role'],
                'native_bytes':len(data),'official_ZIP_bytes':member['uncompressed_size'],
                'native_CRC32':native_crc,'official_ZIP_CRC32':member['CRC32'],'match':ok}
        records.append(record)
        if not ok:mismatches.append(record)
    assert len(records)==8380
    result={'status':'ALL_8380_NATIVE_JPEGS_MATCH_OFFICIAL_ZIP_MEMBER_CRC_AND_SIZE' if not mismatches else 'OFFICIAL_ZIP_IMAGE_BYTE_MISMATCHES_PRESERVED',
            'job_id':os.environ['SLURM_JOB_ID'],'source_selected_member_manifest_sha256':sha(source),
            'native_byte_manifest_sha256':sha(manifest_path),'images_checked':len(records),
            'roles':dict(Counter(r['development_role'] for r in images)),
            'mismatches':mismatches,'native_total_bytes':sum(r['native_bytes'] for r in records),
            'official_ZIP_total_bytes':sum(r['official_ZIP_bytes'] for r in records),
            'CRC_is_byte_integrity_check_not_a_cryptographic_signature':True,
            'image_pixels_decoded_or_model_forward':False,'candidate_final_payload_read':False,
            'elapsed_s':time.perf_counter()-started,'records':records,'whole_goal_complete':False}
    target=ROOT/'results/source_archive_CRC_audit.json';assert not target.exists()
    target.write_text(json.dumps(result,indent=2));print(json.dumps({k:v for k,v in result.items() if k!='records'}),flush=True)
    raise SystemExit(0 if not mismatches else 2)


if __name__=='__main__':main()
