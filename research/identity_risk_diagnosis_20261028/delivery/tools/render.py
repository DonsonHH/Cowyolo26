from pathlib import Path
from collections import Counter
import hashlib, json, math, os, tarfile
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont, ImageOps

ROOT = Path('/share/home/renly/projects/idcoo_research_20261026/identity_risk_diagnosis_20261028')
PROJECT = ROOT.parent
def sha(path): return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path): return json.loads(Path(path).read_text())


def main():
    assert os.environ.get('SLURM_JOB_ID') and __import__('socket').gethostname() != 'mu01'
    manifest = load(ROOT / 'input_manifest.json')
    for row in manifest:
        p = ROOT / row['path']
        assert sha(p) == row['sha256']
    checked = load(ROOT / 'input/independent_verification.json')
    assert checked['query_condition_rows'] == 660 and checked['new_inference_training_or_adopted_thresholds'] is False
    rows = load(ROOT / 'input/per_query660.json')
    primary = [r for r in rows if r['condition'] in ['paired_float_continuation', 'integer_forward_qat']]
    assert len(primary) == 330
    figures = ROOT / 'figures'
    samples = ROOT / 'samples'
    figures.mkdir(exist_ok=False)
    samples.mkdir(exist_ok=False)
    colors = {'C': '#18794e', 'W': '#c43136', 'U_rank_correct': '#ba7600', 'U_rank_wrong': '#e25b25',
              'unknown_reject': '#6651a6', 'unknown_false_accept': '#8d2399'}
    markers = {'C': 'o', 'W': 'X', 'U_rank_correct': 'o', 'U_rank_wrong': 'x',
               'unknown_reject': '^', 'unknown_false_accept': '^'}
    lo = math.floor(min(r['top1_score'] for r in primary) * 20) / 20
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10})
    fig, axes = plt.subplots(3, 2, figsize=(13.5, 8), sharex=True)
    for i, seed in enumerate([26, 27, 28]):
        for j, condition in enumerate(['paired_float_continuation', 'integer_forward_qat']):
            ax = axes[i, j]
            values = [r for r in primary if r['seed'] == seed and r['condition'] == condition]
            assert len(values) == 55
            for row in values:
                y = (1 if row['known'] else 0) + ((row['query_index'] * 7 % 11) - 5) * .021
                kw = dict(marker=markers[row['outcome']], color=colors[row['outcome']], s=32, linewidths=1.)
                if row['outcome'] in ['U_rank_correct', 'unknown_reject']:
                    kw.update(facecolors='none', edgecolors=colors[row['outcome']])
                ax.scatter(row['top1_score'], y, **kw)
            ax.axvline(values[0]['threshold'], color='#333333', linestyle='--', linewidth=1)
            counts = Counter(r['outcome'] for r in values)
            name = 'Float continuation' if j == 0 else 'Integer-forward QAT'
            ax.set_title(f'{name} | seed {seed} | C={counts["C"]}, W={counts["W"]}, unknown FA={counts["unknown_false_accept"]}', loc='left', fontsize=10)
            ax.set_yticks([0, 1], ['Unknown (30)', 'Registered (25)'])
            ax.set_ylim(-.24, 1.26)
            ax.set_xlim(lo, 1.01)
            ax.grid(axis='x', color='#dddddd', linewidth=.6)
            for spine in ['top', 'right']: ax.spines[spine].set_visible(False)
            if i == 2: ax.set_xlabel('Top-1 gallery identity cosine similarity')
    handles = [Line2D([], [], marker=markers[k], linestyle='none', color=colors[k], markersize=7,
                       markerfacecolor='none' if k in ['U_rank_correct', 'unknown_reject'] else colors[k], label=label)
               for k, label in [('C', 'Correct accepted'), ('W', 'Wrong accepted'), ('U_rank_correct', 'Rank-correct rejected'),
                                ('U_rank_wrong', 'Rank-wrong rejected'), ('unknown_reject', 'Unknown rejected'),
                                ('unknown_false_accept', 'Unknown accepted')]]
    handles.append(Line2D([], [], color='#333333', linestyle='--', label='Frozen threshold'))
    fig.suptitle('Frozen development query scores: acceptance and ranking are separate', fontsize=14, y=.98)
    fig.legend(handles=handles, loc='lower center', ncol=4, frameon=False, bbox_to_anchor=(.5, .005))
    fig.subplots_adjust(left=.105, right=.985, top=.91, bottom=.16, wspace=.29, hspace=.53)
    png, svg = figures / 'frozen_query_score_overlap.png', figures / 'frozen_query_score_overlap.svg'
    fig.savefig(png, dpi=200, facecolor='white')
    fig.savefig(svg, facecolor='white')
    plt.close(fig)
    errors = [r for r in load(ROOT / 'input/all_wrong_and_unknown_accepts.json') if r['condition'] == 'integer_forward_qat']
    assert len(errors) == 5 and Counter(r['outcome'] for r in errors) == {'W': 2, 'unknown_false_accept': 3}
    font_path = font_manager.findfont('DejaVu Sans')
    font = ImageFont.truetype(font_path, 18)
    small = ImageFont.truetype(font_path, 16)
    canvas = Image.new('RGB', (1320, 5 * 276 + 66), 'white')
    draw = ImageDraw.Draw(canvas)
    draw.text((16, 14), 'All QAT accepted errors: anonymous dataset IDs; existing development images', font=font, fill='#111111')
    records = []
    for i, row in enumerate(errors):
        y = 62 + i * 276
        outcome = 'registered mismatch' if row['outcome'] == 'W' else 'unknown false acceptance'
        draw.text((16, y), f'Seed {row["seed"]} | {outcome} | score {row["top1_score"]:.4f} | top1-top2 margin {row["top1_top2_margin"]:.4f}', font=font, fill='#111111')
        sources = [('query_source', 'Query'), ('predicted_gallery_source', 'Retrieved gallery'), ('true_gallery_source', 'True-identity best gallery')]
        for j, (key, label) in enumerate(sources):
            x = j * 440 + 16
            if key not in row:
                draw.text((x, y + 100), 'Unknown ID: no registered true gallery', font=small, fill='#666666')
                continue
            metadata = row[key]
            assert metadata['split'] in ['validation_query', 'validation_gallery']
            path = (PROJECT / 'identity_training' / metadata['relative_path']).resolve()
            assert path.is_relative_to((PROJECT / 'identity_training').resolve()) and sha(path) == metadata['sha256']
            with Image.open(path) as im:
                im.load()
                picture = ImageOps.contain(im.convert('RGB'), (408, 196), method=Image.Resampling.LANCZOS)
                origin_size = im.size
            draw.rectangle((x, y + 52, x + 408, y + 248), fill='#eeeeee')
            canvas.paste(picture, (x + (408 - picture.width) // 2, y + 52 + (196 - picture.height) // 2))
            draw.text((x, y + 29), f'{label}: ID {metadata["identity"]}', font=small, fill='#333333')
            records.append({'case_index': i, 'seed': row['seed'], 'outcome': row['outcome'],
                            'role': key, 'relative_path': metadata['relative_path'],
                            'sha256': metadata['sha256'], 'source_size': origin_size})
    contact = samples / 'all5_QAT_accepted_errors.jpg'
    canvas.save(contact, quality=92)
    record = {'status': 'FROZEN_SCORES_AND_ALL5_QAT_ACCEPTED_ERRORS_RENDERED', 'job_id': os.environ['SLURM_JOB_ID'],
              'input_independent_verification_sha256': sha(ROOT / 'input/independent_verification.json'),
              'score_plot_query_condition_points': 330, 'cases': 5, 'image_panels': len(records),
              'case_selection': 'AllQATregisteredwrongaccepts2 andunknownfalseaccepts3; no case omitted or chosenbyappearance',
              'source_images': records,
              'files': [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in [png, svg, contact]],
              'new_model_inference_or_training': False, 'whole_goal_complete': False}
    output = ROOT / 'results'
    output.mkdir(exist_ok=True)
    record_path = output / 'render_record.json'
    record_path.write_text(json.dumps(record, indent=2), encoding='utf-8')
    paths = []
    for folder in ['input', 'figures', 'samples', 'tools', 'protocol']:
        paths.extend(p for p in (ROOT / folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    paths.extend([record_path, ROOT / 'input_manifest.json'])
    archive_manifest = [{'path': p.relative_to(ROOT).as_posix(), 'bytes': p.stat().st_size, 'sha256': sha(p)} for p in sorted(set(paths))]
    manifest_path = output / 'delivery_manifest.json'
    manifest_path.write_text(json.dumps(archive_manifest, indent=2), encoding='utf-8')
    archive = output / 'delivery.tar.gz'
    assert not archive.exists()
    with tarfile.open(archive, 'w:gz') as tf:
        for p in sorted(set(paths)): tf.add(p, arcname=p.relative_to(ROOT).as_posix())
        tf.add(manifest_path, arcname='delivery_manifest.json')
    delivery = {'manifest_files': len(archive_manifest), 'archive_members': len(archive_manifest) + 1,
                'bytes': archive.stat().st_size, 'sha256': sha(archive), 'manifest_sha256': sha(manifest_path),
                'active_logs_excluded': True, 'whole_goal_complete': False}
    (output / 'delivery_record.json').write_text(json.dumps(delivery, indent=2), encoding='utf-8')
    print(json.dumps(delivery), flush=True)


if __name__ == '__main__': main()
