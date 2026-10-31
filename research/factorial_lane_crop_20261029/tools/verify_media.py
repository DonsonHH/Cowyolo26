"""Independent cached-count, SVG geometry and full video decode checks."""
from pathlib import Path
from datetime import datetime, timezone
from PIL import Image
import json, hashlib, tarfile, gzip, re, subprocess
import xml.etree.ElementTree as ET
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'media_delivery'
PROJECT = ROOT.parent

def load(p): return json.loads(p.read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def gz(p): return json.loads(gzip.decompress(p.read_bytes()))

transfer = load(ROOT/'evidence/media_transfer.json')
archive = ROOT/'media_delivery.tar.gz'
assert archive.stat().st_size == transfer['bytes'] and sha(archive) == transfer['sha256']
OUT.mkdir(exist_ok=False)
with tarfile.open(archive) as tar:
    members = tar.getmembers()
    assert len(members) == transfer['members']
    for member in members:
        assert member.isfile() and not member.name.startswith('/') and '..' not in Path(member.name).parts
        path = (OUT/member.name).resolve()
        assert path.is_relative_to(OUT.resolve()) and not path.exists()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(tar.extractfile(member).read())
MEDIA = OUT/'results/media_v2'
for row in load(MEDIA/'manifest.json'):
    path = OUT/row['relative_file']
    assert path.stat().st_size == row['bytes'] and sha(path) == row['sha256']
for rel in ['protocol/media_v1.json', 'tools/render_media_v2.py', 'media_v2.slurm']:
    assert sha(OUT/rel) == sha(ROOT/rel)

def locator(size, variant, seed, mode):
    if size == 320 and variant == 'plain':
        base = PROJECT/('lowres_baseline_20261029/delivery/results/baseline' if mode == 'full' else 'lowres_roi_20261029/delivery/results/roi')
        condition = 'seed'+str(seed)+'_s320'
    else:
        base = PROJECT/'detector_factorial_20261029/delivery/results/evaluation' if mode == 'full' else ROOT/'delivery/results/roi'
        condition = f'S{size}_{variant}_seed{seed}'
    return base/'original'/condition

data = load(MEDIA/'plot_data.json')
ns = {'s': 'http://www.w3.org/2000/svg'}
xml = ET.parse(MEDIA/'all18_full_crop_counts.svg')
bars, max_error = 0, 0.
for panel in range(6):
    axis = xml.find('.//s:g[@id="axes_'+str(panel+1)+'"]', ns)
    assert axis is not None
    paths = []
    for element in axis:
        if element.attrib.get('id', '').startswith('patch_'):
            path = element.find('s:path', ns)
            if path is not None and 'clip-path' in path.attrib: paths.append(path)
    rows = [r for r in data['bars'] if r['panel'] == panel]
    assert len(paths) == len(rows) == 6
    for path, row in zip(paths, rows):
        summary = next(x for x in load(locator(row['size'], row['variant'], row['seed'], row['mode'])/'stride5_summary.json') if x['counter'] == 'handoff_events')
        assert row['value'] == summary['down']
        assert row['historical_control'] == (row['size'] == 320 and row['variant'] == 'plain')
        clipid = re.search(r'#([^\)]+)', path.attrib['clip-path']).group(1)
        rect = xml.find('.//s:clipPath[@id="'+clipid+'"]/s:rect', ns)
        values = [float(x) for x in re.findall(r'[-+]?(?:\d*\.\d+|\d+)(?:[eE][-+]?\d+)?', path.attrib['d'])]
        points = np.asarray(values).reshape(-1, 2)
        assert len(points) in [4, 5]
        height = np.ptp(points[:, 1])/float(rect.attrib['height'])*14
        xpos = (points[0, 0]-float(rect.attrib['x']))/float(rect.attrib['width'])*3.2-.6
        error = max(abs(height-row['value']), abs(xpos-row['bar_x']))
        assert error < 2e-5
        max_error = max(max_error, error)
        bars += 1

gate, meta = load(ROOT/'protocol/media_v1.json'), load(MEDIA/'media_metadata.json')
assert meta['scope_frame0_inclusive'] == gate['movie_scope_frame0_inclusive'] == [8912, 10873]
assert meta['source_decoded_frames'] == 10874 and meta['sample_Hz'] == 5 and meta['playback_fps'] == 25
assert meta['dimensions'] == [1280, 1120] and meta['science_bar_count'] == bars == 36
assert len(meta['movies']) == 2 and len(meta['preview_frames']) == 8
anchors = ROOT/'results/decoded_video_anchors'
anchors.mkdir(exist_ok=False)
checks, frames_total, panel_checks = [], 0, 0
for movie in meta['movies']:
    path = OUT/movie['path']
    assert sha(path) == movie['sha256'] and movie['frames'] == 1962
    probe = subprocess.run(['ffprobe', '-v', 'error', '-count_frames', '-select_streams', 'v:0', '-show_entries', 'stream=width,height,avg_frame_rate,nb_read_frames', '-of', 'json', str(path)], capture_output=True, text=True, check=True)
    stream = json.loads(probe.stdout)['streams'][0]
    assert [stream['width'], stream['height']] == [1280, 1120] and stream['avg_frame_rate'] == '25/1' and int(stream['nb_read_frames']) == 1962
    decoded = subprocess.run(['ffmpeg', '-v', 'error', '-xerror', '-err_detect', 'explode', '-i', str(path), '-f', 'null', '-'], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
    assert not decoded.stderr
    frames_total += 1962
    for row in [x for x in meta['preview_frames'] if x['variant'] == movie['variant']]:
        index = row['source_frame0']-8912
        assert index == row['video_index0'] and row['source_frame0'] in gate['source_anchors']
        file = anchors/(row['variant']+'_f'+str(row['source_frame0'])+'.png')
        subprocess.run(['ffmpeg', '-v', 'error', '-i', str(path), '-vf', 'select=eq(n\\,'+str(index)+')', '-frames:v', '1', '-fps_mode', 'vfr', str(file)], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, check=True)
        png = OUT/row['path']
        assert sha(png) == row['sha256']
        with Image.open(file) as image: a = np.asarray(image.convert('RGB'), dtype=np.int16)
        with Image.open(png) as image: b = np.asarray(image.convert('RGB'), dtype=np.int16)
        assert a.shape == b.shape == (1120, 1280, 3)
        delta = np.abs(a-b)
        mean, p95 = float(delta.mean()), float(np.quantile(delta, .95))
        assert mean < 6 and p95 < 20
        for panel in row['panels']:
            trace = gz(locator(panel['size'], row['variant'], 26, panel['mode'])/'stride5_counter_trace.json.gz')
            events = [e for e in trace['handoff_events'] if 8912 <= e['frame0'] <= 10873]
            assert panel['down'] == sum(e['direction'] == 'A->B' and e['frame0'] <= row['source_frame0'] for e in events)
            assert panel['up'] == sum(e['direction'] == 'B->A' and e['frame0'] <= row['source_frame0'] for e in events)
            assert panel['sample_frame0'] == row['source_frame0']-row['source_frame0']%5
            assert panel['post_tracker_boxes'] == sum(x['frame0'] == panel['sample_frame0'] for x in trace['post_tracker'])
            panel_checks += 1
        checks.append({'variant': row['variant'], 'source_frame0': row['source_frame0'], 'video_frame_index0': index, 'path': str(file.resolve()), 'sha256': sha(file), 'mean_RGB_delta': mean, 'p95_RGB_delta': p95, 'panels': 6})
record = {'status': '36_SVG_BARS3924_VIDEO_FRAMES_AND8_ANCHORS48_PANEL_COUNTS_INDEPENDENTLY_VERIFIED',
          'created_UTC': datetime.now(timezone.utc).isoformat(), 'archive_sha256': sha(archive), 'archive_members': len(members),
          'SVG_bars': bars, 'maximum_SVG_bar_data_error': max_error, 'strict_decoded_video_frames': frames_total,
          'movie_count': 2, 'anchor_checks': checks, 'independently_recomputed_anchor_panel_counts': panel_checks,
          'expected_visual_figures': 9, 'expected_visual_panels': 54, 'manual_visual_review_separate': True,
          'new_network_forwards': 0, 'new_training_updates': 0, 'PYNQ5FPS_proven': False, 'whole_goal_complete': False}
file = ROOT/'results/media_verification.json'
assert not file.exists()
file.write_text(json.dumps(record, indent=2)+'\n')
print(json.dumps({k: v for k, v in record.items() if k != 'anchor_checks'}))
