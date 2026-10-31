"""Slurm-only native still extraction from bounded MPEG-PS fragments, no model."""
from pathlib import Path,PurePosixPath
import hashlib,json,os,re,socket,subprocess,tarfile
from PIL import Image,ImageDraw,ImageFont
ROOT=Path('/share/home/renly/projects/idcoo_research_20261026/overhead_long_session_20261028')
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    assert os.environ.get('SLURM_JOB_ID') and socket.gethostname()!='mu01'
    archive=ROOT/'next_probes_input.tar';stage=ROOT/'next_probes_staged';stage.mkdir(exist_ok=False)
    with tarfile.open(archive) as t:
        for m in t.getmembers():
            n=PurePosixPath(m.name);assert m.isfile() and not n.is_absolute() and '..' not in n.parts
        t.extractall(stage,filter='data')
    manifest=json.loads((stage/'input/next_file_probes/manifest.json').read_text());out=ROOT/'results/next_native_probes';out.mkdir(parents=True,exist_ok=False)
    ffmpeg='/share/home/renly/miniconda3/envs/pid310_gpu/bin/ffmpeg';rows=[];panels=[];font=ImageFont.load_default(size=22)
    for entry in manifest['files']:
        for part in entry['range_reads']:
            assert sha(stage/part['file'])==part['sha256']
        for part in [r for r in entry['range_reads'] if 'fraction' in r]:
            tag=entry['filename'].replace('.mp4','')+f"_fraction_{int(part['fraction']*100):02d}";dest=out/(tag+'.jpg')
            command=[ffmpeg,'-hide_banner','-v','warning','-threads','1','-skip_frame','nokey','-probesize','8388608','-analyzeduration','10000000',
                     '-f','mpeg','-i',str(stage/part['file']),'-an','-vf','scale=1280:720','-frames:v','1','-update','1',str(dest)]
            proc=subprocess.run(command,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE);log=out/(tag+'.log');log.write_bytes(proc.stderr)
            valid=proc.returncode==0 and dest.is_file()
            if valid:
                with Image.open(dest) as im:im.load();assert im.size==(1280,720);image=im.convert('RGB').resize((640,360))
            else:image=Image.new('RGB',(640,360),'#374151')
            panel=Image.new('RGB',(640,420),'#111827');d=ImageDraw.Draw(panel)
            d.text((8,5),entry['filename'],font=font,fill='white');d.text((8,31),f"Byte fraction {part['fraction']:.0%} | Native probe | {'decoded' if valid else 'failed'}",font=font,fill='#fbbf24')
            panel.paste(image,(0,60));panels.append(panel)
            rows.append({'source_filename':entry['filename'],'byte_fraction':part['fraction'],'fragment_source_byte_start':part['start'],
                         'native_still_decoded':valid,'ffmpeg_exit_code':proc.returncode,'file':dest.name if valid else None,
                         'image_sha256':sha(dest) if valid else None,'log':log.name,'log_sha256':sha(log),
                         'fragment_start_warnings_expected':'Ranges start within a file; missing previous packets/SPS errors can arise. This does not certify full-source quality.',
                         'scene_visual_review':'PENDING'})
    assert len(rows)==18
    sheet=Image.new('RGB',(1920,420*6))
    for i,panel in enumerate(panels):sheet.paste(panel,((i%3)*640,(i//3)*420))
    sheet.save(out/'six_files_native_fraction_overview.jpg',quality=94)
    result={'status':'SIX_REMAINING_FILES_EIGHTEEN_PREDICTION_FREE_NATIVE_PROBES_PREPARED','job_id':os.environ['SLURM_JOB_ID'],
            'protocol_sha256':manifest['protocol_sha256'],'input_archive_sha256':sha(archive),'HTTP_bytes':manifest['successful_HTTP_bytes'],
            'source_files':6,'native_probe_attempts':18,'decoded_stills':sum(r['native_still_decoded'] for r in rows),'probes':rows,
            'whole_source_decode_or_clock_validated':False,'new_model_predictions':0,'event_reference_available':False,'whole_goal_complete':False}
    (out/'summary.json').write_text(json.dumps(result,indent=2))
    output=ROOT/'next_native_probes_delivery.tar.gz'
    with tarfile.open(output,'w:gz') as t:
        for f in out.iterdir():t.add(f,arcname=f.relative_to(ROOT))
    print(json.dumps({k:v for k,v in result.items() if k!='probes'}),flush=True)
    print(json.dumps({'archive_bytes':output.stat().st_size,'archive_sha256':sha(output)}),flush=True)
if __name__=='__main__':main()
