"""Make browser-compatible derivatives without replacing verified source previews."""
from pathlib import Path
from PIL import Image, ImageDraw
import hashlib
import json
import shutil
import subprocess

ROOT = Path(__file__).resolve().parents[1]
FFMPEG, FFPROBE = shutil.which('ffmpeg'), shutil.which('ffprobe')
assert FFMPEG and FFPROBE
OUT = ROOT/'previews'
OUT.mkdir(exist_ok=True)
source_checks = json.loads((ROOT/'delivery/counting_evaluation/evidence/preview_video_checks.json').read_text())
checks = []
for item in source_checks['videos']:
    source = ROOT/'delivery/counting_evaluation/media'/item['file']
    dest = OUT/item['file']
    if not dest.exists():
        subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-nostdin',
                        '-i', str(source), '-an', '-c:v', 'libx264', '-preset', 'fast',
                        '-crf', '23', '-pix_fmt', 'yuv420p', '-movflags', '+faststart',
                        '-n', str(dest)], check=True)
    probe = json.loads(subprocess.check_output([FFPROBE, '-v', 'error', '-count_frames',
                      '-show_streams', '-show_format', '-of', 'json', str(dest)]))
    stream = next(s for s in probe['streams'] if s['codec_type'] == 'video')
    assert stream['codec_name'] == 'h264'
    assert int(stream['nb_read_frames']) == item['frame_count']
    subprocess.run([FFMPEG, '-hide_banner', '-v', 'error', '-nostdin', '-xerror',
                    '-i', str(dest), '-f', 'null', '-'], check=True,
                   stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
    thumbnail = OUT/(dest.stem+'_last.jpg')
    if not thumbnail.exists():
        subprocess.run([FFMPEG, '-hide_banner', '-loglevel', 'error', '-nostdin',
                        '-ss', str(float(stream['duration'])-.25), '-i', str(dest),
                        '-frames:v', '1', '-q:v', '2', '-n', str(thumbnail)], check=True)
    with dest.open('rb') as f:
        digest = hashlib.file_digest(f, 'sha256').hexdigest()
    row = {'file': str(dest.relative_to(ROOT)), 'codec': stream['codec_name'],
           'width': stream['width'], 'height': stream['height'],
           'fps': stream['avg_frame_rate'], 'frames': int(stream['nb_read_frames']),
           'duration_s': float(stream['duration']), 'bytes': dest.stat().st_size,
           'sha256': digest, 'full_decode_passed': True,
           'source_relative_path': str(source.relative_to(ROOT))}
    checks.append(row)
    print(json.dumps(row), flush=True)
sheet = Image.new('RGB', (1280, 2*395), 'white')
draw = ImageDraw.Draw(sheet)
for i, row in enumerate(checks):
    img = Image.open(OUT/(Path(row['file']).stem+'_last.jpg'))
    sheet.paste(img, ((i%2)*640, (i//2)*395+30))
    draw.text(((i%2)*640+10, (i//2)*395+8), Path(row['file']).name, fill='black')
sheet.save(OUT/'preview_verification_sheet.jpg', quality=92)
(ROOT/'results/local_preview_checks.json').write_text(json.dumps({
    'status': 'PASS', 'local_ffmpeg': FFMPEG, 'videos': checks,
    'scope': 'H264 derivatives preserve frame count and timing; detection was not rerun locally'
}, indent=2))
