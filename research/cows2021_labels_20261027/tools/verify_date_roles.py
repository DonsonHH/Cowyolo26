"""Independently reconcile every proposed date role with the source XML."""
from pathlib import Path
from collections import Counter, defaultdict
from datetime import date, datetime
import csv, hashlib, json, xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    folder = ROOT / 'results/date_roles_v1'
    summary = json.loads((folder / 'summary.json').read_text(encoding='utf-8'))
    rows = json.loads((folder / 'manifest.json').read_text(encoding='utf-8'))
    csv_rows = list(csv.DictReader((folder / 'manifest.csv').open(encoding='utf-8-sig', newline='')))
    assert len(rows) == len(csv_rows) == 10402
    assert len({r['file_name'] for r in rows}) == 10402
    assert summary['manifest_sha256'] == sha(folder / 'manifest.json')
    assert summary['metadata_sha256'] == sha(ROOT / 'results/source_metadata_all.json')
    assert summary['protocol_sha256'] == sha(ROOT / 'protocol/date_grouping_candidate_v1.json')
    dates = defaultdict(set)
    sources = defaultdict(set)
    counts = Counter()
    for row, csv_row in zip(rows, csv_rows):
        assert row['file_name'] == csv_row['file_name']
        assert row['candidate_date_role'] == csv_row['candidate_date_role']
        xml = ROOT / 'source_XML' / row['published_role'] / Path(row['file_name']).with_suffix('.xml')
        assert sha(xml) == row['XML_sha256']
        original = ET.parse(xml).getroot().findtext('filename')
        assert original == row['original_filename']
        parts = original.removesuffix('.jpg').split('_')
        expected = 'quarantine_metadata'
        if len(parts) == 4 and parts[0] == 'image':
            try:
                day = date.fromisoformat(parts[2])
                hour, minute, second = map(int, parts[3].split('-'))
                datetime(day.year, day.month, day.day, hour, minute, second)
                if date(2020, 2, 5) <= day < date(2020, 2, 28): expected = 'train_candidate'
                elif date(2020, 2, 28) <= day < date(2020, 3, 5): expected = 'validation_development_candidate'
                elif date(2020, 3, 5) <= day < date(2020, 3, 10): expected = 'development_reserve'
                elif date(2020, 3, 10) <= day < date(2020, 3, 12): expected = 'candidate_final_date_holdout'
            except (ValueError, TypeError):
                pass
        assert row['candidate_date_role'] == expected
        assert row['image_bytes_verified'] is False and row['final_test_eligibility_verified'] is False
        counts[expected] += 1
        if row['capture_date']: dates[row['capture_date']].add(expected)
        sources[original].add(expected)
    assert dict(counts) == summary['counts']
    assert all(len(v) == 1 for v in dates.values()) and all(len(v) == 1 for v in sources.values())
    assert summary['final_independent_test_certified'] is False
    out = ROOT / 'results/date_roles_independent_verification.json'
    assert not out.exists()
    result = {'status': 'ALL_10402_DATE_ROLES_RECONCILED_DIRECTLY_WITH_SOURCE_XML',
              'manifest_sha256': sha(folder / 'manifest.json'), 'summary_sha256': sha(folder / 'summary.json'),
              'records': len(rows), 'counts': dict(counts), 'date_groups': len(dates),
              'date_or_original_name_crosses_roles': False,
              'image_bytes_or_final_independence_certified': False,
              'new_model_forward_or_training': False, 'whole_goal_complete': False}
    out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
