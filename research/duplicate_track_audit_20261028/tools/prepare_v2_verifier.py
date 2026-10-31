from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'tools/verify_render.py').read_text(encoding='utf-8')
for before,after in [('render_delivery_record.json','render_v2_delivery_record.json'),
                     ('render_delivery.tar.gz','render_v2_delivery.tar.gz'),
                     ("ROOT/'render_delivery'","ROOT/'render_v2_delivery'"),
                     ('results/render_record.json','results/render_record_v2.json'),
                     ('tools/render.py','tools/render_v2.py'),('results/figures','results/figures_v2'),
                     ('render_local_verification.json','render_v2_local_verification.json')]:
    assert before in source;source=source.replace(before,after)
target=ROOT/'tools/verify_render_v2.py';assert not target.exists();target.write_text(source,encoding='utf-8')
print('layout correction verifier generated')
