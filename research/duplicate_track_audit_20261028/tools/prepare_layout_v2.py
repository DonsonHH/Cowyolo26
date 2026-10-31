from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
source=(ROOT/'tools/render.py').read_text(encoding='utf-8')
source=source.replace("'results/figures'","'results/figures_v2'")
source=source.replace("'results/render_record.json'","'results/render_record_v2.json'")
source=source.replace("'results/render_manifest.json'","'results/render_manifest_v2.json'")
source=source.replace("'results/render_delivery.tar.gz'","'results/render_v2_delivery.tar.gz'")
source=source.replace("'results/render_delivery_record.json'","'results/render_v2_delivery_record.json'")
source=source.replace("'tools/render.py'","'tools/render_v2.py'").replace("'tools/render.slurm'","'tools/render_v2.slurm'")
source=source.replace("(1920,790)","(1920,820)").replace("y=(i//3)*395","y=(i//3)*410")
source=source.replace("max(0,b[1]-26)","max(0,b[1]-26)")
source=source.replace("(b[0],b[1]+12)","(b[0],b[1]+12+(32 if key=='xyxy_b' else 0))")
path=ROOT/'tools/render_v2.py';assert not path.exists();path.write_text(source,encoding='utf-8')
script=(ROOT/'tools/render.slurm').read_text(encoding='utf-8').replace('tools/render.py','tools/render_v2.py').replace('logs/render-%j','logs/render_v2-%j')
path=ROOT/'tools/render_v2.slurm';assert not path.exists();path.write_text(script,encoding='utf-8',newline='\n')
record={'prior_job':130297,'original_source_sha256':sha(ROOT/'tools/render.py'),'corrected_source_sha256':sha(ROOT/'tools/render_v2.py'),
        'changes':['Increase contact sheet rows from395 to410px to prevent caption clipping','Offset second predictedID label vertically'],
        'case_selection_or_chart_data_changed':False,'audit_changed':False,'original_outputs_preserved':True}
path=ROOT/'results/layout_correction_record.json';assert not path.exists();path.write_text(json.dumps(record,indent=2),encoding='utf-8')
print(json.dumps(record))
