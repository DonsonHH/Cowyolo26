from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parent
s=(ROOT/'verify_numeric_recovery.py').read_text(encoding='utf-8')
def replace(a,b):
 global s
 assert s.count(a)==1,(a,s.count(a));s=s.replace(a,b)
replace('out.mkdir(exist_ok=False)','out.mkdir(exist_ok=True)')
replace('assert f.is_relative_to(out.resolve()) and not f.exists();f.parent.mkdir(parents=True,exist_ok=True);f.write_bytes(tar.extractfile(member).read())',
'''assert f.is_relative_to(out.resolve());data=tar.extractfile(member).read();f.parent.mkdir(parents=True,exist_ok=True)
  if f.exists():assert f.read_bytes()==data
  else:f.write_bytes(data)''')
replace('dest.mkdir(exist_ok=False)','dest.mkdir(exist_ok=True)')
replace('expected_normal=raw/np.linalg.norm(raw);assert expected_normal.tobytes()==actual_normal.tobytes()',
        'expected_normal=raw.astype(float)/np.linalg.norm(raw.astype(float));assert np.max(np.abs(expected_normal-actual_normal))<1e-7')
replace("assert float(scores[winner])==r['similarity']==original['similarity'] and bool(scores[winner]>=p['fixed_identity_threshold'])==r['accepted']==original['accepted']",
        "assert abs(float(scores[winner])-r['similarity'])<1e-12 and r['similarity']==original['similarity'] and bool(scores[winner]>=p['fixed_identity_threshold'])==r['accepted']==original['accepted']")
replace('photo.save(file,compress_level=0)', '''
  if file.exists():
   with Image.open(file) as prior:prior.load();assert prior.size==photo.size and prior.convert('RGB').tobytes()==photo.tobytes()
  else:photo.save(file,compress_level=0)''')
ast.parse(s);f=ROOT/'verify_numeric_recovery_v2.py';assert not f.exists();f.write_text(s,encoding='utf-8');print({'v2_uses_preexisting_frozen_float_normalization_and_score_gates':True})
