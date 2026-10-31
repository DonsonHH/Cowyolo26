from pathlib import Path,PurePosixPath
from PIL import Image
import hashlib,json,tarfile,xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1]
def load(p):return json.loads(p.read_text(encoding='utf-8'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    record=load(ROOT/'evidence/plots_delivery_record.json');archive=ROOT/'plot_delivery.tar.gz';dest=ROOT/'plot_delivery'
    assert archive.stat().st_size==record['archive_bytes'] and sha(archive)==record['archive_sha256'] and not dest.exists()
    with tarfile.open(archive,'r:gz') as tf:
        rows=json.loads(tf.extractfile('plot_delivery_manifest.json').read())['files'];expected={r['file']:r for r in rows};members=tf.getmembers()
        assert len(rows)==len(expected)==8 and len(members)==record['files']==9
        assert {m.name for m in members}==set(expected)|{'plot_delivery_manifest.json'}
        for m in members:
            name=PurePosixPath(m.name);assert m.isfile() and not name.is_absolute() and '..' not in name.parts and ':' not in m.name
            target=dest.joinpath(*name.parts).resolve();assert target.is_relative_to(dest.resolve());data=tf.extractfile(m).read()
            if m.name in expected:assert len(data)==expected[m.name]['bytes'] and hashlib.sha256(data).hexdigest()==expected[m.name]['sha256']
            target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
    assert sha(dest/'protocol/plots_v1.json')==sha(ROOT/'protocol/plots_v1.json')
    assert sha(dest/'tools/render_plots.py')==sha(ROOT/'tools/render_plots.py')
    plots=dest/'results/plots';d=load(plots/'plot_data.json');summary=load(ROOT/'delivery/results/summary.json')
    assert d['source_summary_sha256']==sha(ROOT/'delivery/results/summary.json')
    assert d['case_states']==[{'case_id':c['case_id'],'terminal_status_counts':c['terminal_status_counts']} for c in summary['cases']]
    trace=load(ROOT/'delivery/results/cases/S01_single/stream_linker_trace.json')
    slots={r['event_id']:r for r in trace['slots'] if r['event_id'] is not None};outputs={r['event_id']:r for r in trace['outputs']}
    assert len(d['counted_intervals'])==12 and d['uncounted_visual_reservations']==13
    for r in d['counted_intervals']:
        slot=slots[r['event_id']];out=outputs[r['event_id']]
        assert r['track_id']==slot['track_id'] and r['opened_frame0']==slot['opened_frame0'] and r['closed_frame0']==slot['closed_frame0']
        assert r['decision_frame0']==out['decision_frame0'] and r['RF_status']==out['rf_status']
        assert r['injected_read_capture_frame0']==r['closed_frame0']-5
    context=next(r for r in trace['audit'] if r['kind']=='RF_CAUSAL_CONTEXT' and r['event_id']=='E007_f9465_tid96')
    assert d['focus_context']==context and d['focus_read']['captured']==9460 and context['frame0']==9480
    assert len(d['focus_matching_passages'])==2 and sum(r['closed']>9480 for r in d['focus_matching_passages'])==1
    files=[]
    for path in sorted(plots.iterdir()):
        if path.suffix=='.png':
            with Image.open(path) as im:im.load();dimensions=list(im.size)
        elif path.suffix=='.svg':assert ET.parse(path).getroot().tag.endswith('svg');dimensions=None
        else:continue
        files.append({'path':str(path.resolve()),'sha256':sha(path),'dimensions':dimensions})
    assert len(files)==4
    result={'status':'FOUR_PLOT_FILES_AND_ALL_SCENARIO_COUNTS_WINDOW_COORDINATES_VERIFIED','archive_members':9,
            'software_case_rows':12,'counted_interval_rows':12,'focus_incident_passages':2,'files':files,
            'actual_visual_review_required':True,'source_cow_identity_accuracy':None,'whole_goal_complete':False}
    p=ROOT/'results/plot_verification.json';assert not p.exists();p.write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k!='files'}))
if __name__=='__main__':main()
