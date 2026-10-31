from pathlib import Path
import hashlib,json
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    value={'name':'RF stream outcome and causal shared-window figures',
        'source_protocol_sha256':sha(ROOT/'protocol/stream_v1.json'),
        'source_summary_sha256':sha(ROOT/'delivery/results/summary.json'),
        'independent_verification_sha256':sha(ROOT/'results/independent_verification.json'),
        'case_id_for_timeline':'S01_single','focus_event_id':'E007_f9465_tid96',
        'figure_scope':'Software states on repeated12source events and synthetic RF; not identity accuracy or board performance.'}
    p=ROOT/'protocol/plots_v1.json';assert not p.exists();p.write_text(json.dumps(value,indent=2)+'\n',encoding='utf-8');print(sha(p))
if __name__=='__main__':main()
