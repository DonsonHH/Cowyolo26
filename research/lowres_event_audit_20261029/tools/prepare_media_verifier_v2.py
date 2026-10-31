from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
original=(ROOT/'tools/verify_media_and_reference.py').read_text();before=original.split('checks=[]',1)[0];after=original.split("cache=next(",1)[1]
middle='''timestamp_record=load(ROOT/'results/actual_frame_timestamps.json')
actual_pts={r['frame0']:r['PTS'] for r in timestamp_record['requested_frames']}
tickvalues=[round(actual_pts[r['source_frame0']]*90000) for r in native['frames']]
expression='+'.join('eq(pts\\\\,'+str(v)+')' for v in tickvalues)
command=['ffmpeg','-v','error','-threads','2','-copyts','-i',str(source),'-vf','select='+expression,'-fps_mode','vfr','-f','rawvideo','-pix_fmt','rgb24','pipe:1']
process=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,check=True)
bytes_per_frame=1440*2560*3;assert len(process.stdout)==18*bytes_per_frame
checks=[]
for index,row in enumerate(native['frames']):
    frame=row['source_frame0'];assert 8912<=frame<=10873
    raw=process.stdout[index*bytes_per_frame:(index+1)*bytes_per_frame]
    with Image.open(row['file']) as image:actual=np.asarray(image.convert('RGB'))
    assert actual.shape==(1440,2560,3) and actual.tobytes()==raw and sha(row['file'])==row['sha256']
    checks.append({'source_frame0':frame,'actual_absolute_PTS_seconds':actual_pts[frame],'actual_PTS_ticks_90000Hz':tickvalues[index],
     'RGB_pixel_sha256':hashlib.sha256(raw).hexdigest(),'independent_absolute_PTS_selection_matches_frame_select_exact':True})
del process
cache=next('''
after=after.replace('ALL12_REFERENCE_EVENTS_AND18_TIMESTAMP_SEEKS36_PANEL_METADATA_VERIFIED','ALL12_REFERENCE_EVENTS_AND18_ABSOLUTE_PTS_SELECTIONS36_PANEL_METADATA_VERIFIED')
target=ROOT/'tools/verify_media_and_reference_v2.py';assert not target.exists();target.write_text(before+middle+after,newline='\n')
print('IndependentabsolutePTSselectiongateprepared;failedrelative-seekgatepreserved')
