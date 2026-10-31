from pathlib import Path
ROOT=Path(__file__).resolve().parent
text=(ROOT/'collect_media.sh').read_text().replace('130563','130564').replace('results/media','results/media_v2').replace('tools/render_media.py','tools/render_media_v2.py')
text=text.replace("root/'media.slurm'","root/'media_v2.slurm'").replace('20261029_media.tar.gz','20261029_media_v2.tar.gz').replace('20261029_media_transfer.json','20261029_media_v2_transfer.json')
file=ROOT/'collect_media_v2.sh';assert not file.exists();file.write_text(text,newline='\n')
