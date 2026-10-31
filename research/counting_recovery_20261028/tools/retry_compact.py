from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'tools/compact_media.py').read_text(encoding='utf-8')
source=source.replace('/envs/sd/bin/ffmpeg','/envs/pid310_gpu/bin/ffmpeg').replace("f'compact-{source.parent.name}.log'","f'compact_v2-{source.parent.name}.log'")
path=ROOT/'tools/compact_media_v2.py';assert not path.exists();path.write_text(source,encoding='utf-8')
source=(ROOT/'tools/compact.slurm').read_text(encoding='utf-8').replace('tools/compact_media.py','tools/compact_media_v2.py')
path=ROOT/'tools/compact_v2.slurm';assert not path.exists();path.write_text(source,encoding='utf-8')
