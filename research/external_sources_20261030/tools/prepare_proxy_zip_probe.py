from pathlib import Path
import ast
ROOT=Path(__file__).resolve().parent
s=(ROOT/'probe_COLO_zip_metadata.py').read_text(encoding='utf-8')
assert s.count("OUT=ROOT/'evidence/COLO_zip_metadata'")==1
s=s.replace("OUT=ROOT/'evidence/COLO_zip_metadata'","OUT=ROOT/'evidence/COLO_zip_metadata_v2'")
s=s.replace('with urllib.request.urlopen(req,timeout=18) as r:',"opener=urllib.request.build_opener(urllib.request.ProxyHandler({'http':'http://127.0.0.1:7897','https':'http://127.0.0.1:7897'}))\n with opener.open(req,timeout=18) as r:")
s=s.replace("'COLO_zip_metadata_probe.json'","'COLO_zip_metadata_probe_v2.json'")
ast.parse(s);out=ROOT/'probe_COLO_zip_metadata_v2.py';assert not out.exists();out.write_text(s,encoding='utf-8');print({'per_request_existing_loopback_only':True,'prior_failed_response_preserved':True})
