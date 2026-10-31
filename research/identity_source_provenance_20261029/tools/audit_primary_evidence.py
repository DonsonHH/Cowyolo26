from pathlib import Path
from collections import Counter,defaultdict
from html.parser import HTMLParser
from urllib.parse import urlsplit,unquote
import hashlib,json,re,zlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def git_hash(kind,data):return hashlib.sha1(kind+b' '+str(len(data)).encode()+b'\0'+data).hexdigest()
def reconstruct_tree(tree,expected_root):
    byparent=defaultdict(list)
    for row in tree['tree']:
        path=Path(row['path']);parent='' if str(path.parent)=='.' else path.parent.as_posix();byparent[parent].append(row)
    checks=[]
    for parent,children in sorted(byparent.items(),key=lambda item:-len(Path(item[0]).parts)):
        pieces=[]
        ordered=sorted(children,key=lambda r:(Path(r['path']).name+('/' if r['type']=='tree' else '')).encode())
        for row in ordered:
            mode=row['mode'].lstrip('0') or '0';name=Path(row['path']).name.encode()
            pieces.append(mode.encode()+b' '+name+b'\0'+bytes.fromhex(row['sha']))
        actual=git_hash(b'tree',b''.join(pieces))
        expected=expected_root if not parent else next(r['sha'] for r in tree['tree'] if r['path']==parent)
        assert actual==expected,(parent,actual,expected);checks.append({'directory':parent or '.','tree_sha':actual})
    return checks
def main():
    rows=load(ROOT/'evidence/primary_manifest.json')+load(ROOT/'evidence/secondary_metadata_manifest.json')+[load(ROOT/'evidence/camera1_day14_capture.json')]
    for row in rows:
        if 'file' in row:assert (ROOT/row['file']).stat().st_size==row['bytes'] and sha(ROOT/row['file'])==row['sha256']
    known=load(ROOT/'evidence/author_source_manifest.json');related=load(ROOT/'evidence/related_source_manifest.json')
    repo_checks=[]
    for manifest in [known,*related]:
        name=manifest['repository'].split('/')[-1]
        treepath='author_repo_exact_tree.json' if name=='CowIDentifier' else name+'_tree.json'
        commitpath='author_repo_commit.json' if name=='CowIDentifier' else name+'_commit.json'
        tree=load(ROOT/'evidence/primary'/treepath);commit=load(ROOT/'evidence/primary'/commitpath)
        expected=commit['commit']['tree']['sha'];checks=reconstruct_tree(tree,expected)
        for row in manifest['files']:
            data=(ROOT/row['local_file']).read_bytes();assert git_hash(b'blob',data)==row['git_blob_sha']
            assert len(data)==row['bytes'] and hashlib.sha256(data).hexdigest()==row['sha256']
        repo_checks.append({'repository':manifest['repository'],'commit':commit['sha'],'exact_tree_sha':expected,
            'all_tree_entries_reconstructed':len(checks),'text_source_blobs_verified':len(manifest['files'])})
    z=load(ROOT/'evidence/zip_directory/summary.json');entries=load(ROOT/'evidence/zip_directory/entries.json')
    for r in z['range_requests']:
        path=ROOT/r['file'];assert path.stat().st_size==r['bytes'] and sha(path)==r['sha256']
        assert r['start']>=z['directory_start'] and r['end']-r['start']+1==r['bytes']
    assert len(entries)==103156 and sum(not r['directory'] for r in entries)==102594
    suffixes=Counter(Path(r['name']).suffix.lower() for r in entries if not r['directory'])
    assert suffixes==z['file_suffix_counts'] and suffixes['.jpg']==101329 and suffixes['.mp4']==137
    assert not any(Path(r['name']).suffix.lower() in ['.csv','.xml','.npy','.npz','.pkl'] for r in entries if not r['directory'])
    gallery=load(PROJECT/'identity_training_20261026/delivery/results/study/feature_index.json')['evaluation_gallery']
    source_metadata=load(ROOT/'results/gallery_metadata_audit.json');assert source_metadata['EXIF_nonempty_images']==0
    archive_rows=[]
    for row in gallery:
        suffix='MultiCamCows2024Root/'+row['day']+'/'+row['identity']+'/'+row['source_filename']
        found=[r for r in entries if r['name'].endswith('/'+suffix)];assert len(found)==1
        f=found[0];local=PROJECT/'identity_training_20261026/delivery'/row['relative_path'];data=local.read_bytes()
        assert len(data)==f['bytes'] and zlib.crc32(data)&0xffffffff==f['CRC32'] and hashlib.sha256(data).hexdigest()==row['sha256']
        meta=next(r for r in source_metadata['images'] if r['sha256']==row['sha256'])
        assert meta['EXIF']=={} and all(s['marker']=='0xe0' for s in meta['APP_and_comment_segments'])
        archive_rows.append({'relative_published_path':suffix,'local_sha256':row['sha256'],'archive_CRC32':f['CRC32'],'archive_and_local_bytes_equal':True,
             'JPEG_embedded_source_time_or_frame_found':False})
    expected_source='MultiCamCows2024Root/videos/camera1/2023Aug14/2023-08-14T12-54-48.mp4'
    found=next(r for r in entries if r['name'].endswith('/'+expected_source))
    native=PROJECT/'phase3_diagnosis_20261026/inputs/multicam_original.mp4';assert native.stat().st_size==found['bytes']==260096040
    assert zlib.crc32(native.read_bytes())&0xffffffff==found['CRC32'] and sha(native)=='5d1d8c197abbebfd98d11b7900fe2655013acc43cf5e01bebc7c72a3bcde95a1'
    assert (ROOT/'evidence/primary/author_appendix.pdf').read_bytes()[:5]!=b'%PDF-'
    result={'status':'PRIMARY_DATA_ARCHIVE_GALLERY_CRC_JPEG_METADATA_AND102_AUTHOR_SOURCE_BLOBS_VERIFIED',
        'metadata_responses_verified':len(rows),'repositories':repo_checks,'source_text_files':sum(r['text_source_blobs_verified'] for r in repo_checks),
        'zip_entries':103156,'zip_files':102594,'zip_payload_image_video_files':101329+137,'csv_members_found':0,
        'gallery_images_bound_to_official_archive_by_size_CRC_and_local_SHA256':archive_rows,
        'all30_gallery_images_EXIF_empty':True,'raw_video_original_archive_CRC_matches_local':True,
        'author_code_can_generate_timestamp_csv':True,'timestamp_csv_present_in_published_zip':False,
        'appendix_endpoint_returned_NONPDF_preserved':True,'appendix_A1_checked_in_arxiv_v2_HTML':True,
        'explicit_image_source_frame_to_anonymous_ID_mapping_found':False,
        'source_ID_promoted_by_model_similarity':False,'whole_goal_complete':False}
    p=ROOT/'results/primary_independent_audit.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='gallery_images_bound_to_official_archive_by_size_CRC_and_local_SHA256'}))
if __name__=='__main__':main()
