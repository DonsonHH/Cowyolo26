from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
source=ROOT/'tools/verify_crop_independent.py';target=ROOT/'tools/verify_crop_independent_v2.py'
assert not target.exists();text=source.read_text();old="ROOT/'results/summary.json'";assert old in text
target.write_text(text.replace(old,"ROOT/'crop_results_v2/summary.json'"),newline='\n')
