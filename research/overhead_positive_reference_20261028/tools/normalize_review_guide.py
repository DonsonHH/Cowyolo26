from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
path=ROOT/'逐事件草案复核入口.md';body=path.read_bytes();assert b'\r\r\n' in body
backup=ROOT/'results/review_bundle/guide_before_lineending_fix.md';assert not backup.exists();backup.write_bytes(body)
text=body.decode('utf-8').replace('\r\r\n','\n').replace('\r\n','\n').replace('\r','\n')
assert '\r' not in text
lines=text.splitlines();header=next(i for i,l in enumerate(lines) if l.startswith('| ID |'))
assert lines[header+1].startswith('| ---') and all(lines[header+i].startswith('| R') for i in range(2,14))
path.write_bytes(text.encode('utf-8'))
record={'status':'REVIEW_GUIDE_LINE_ENDINGS_NORMALIZED_TO_PRESERVE_MARKDOWN_TABLE','before_sha256':sha(backup),'after_sha256':sha(path),
        'CRCRLF_sequences_repaired':body.count(b'\r\r\n'),'table_rows_contiguous':12,'candidate_data_or_images_changed':False,
        'repair':'Write UTF8 bytes directly; preserve old marked-guide text separately.'}
(ROOT/'results/review_bundle/guide_lineending_repair.json').write_text(json.dumps(record,indent=2),encoding='utf-8');print(json.dumps(record),flush=True)
