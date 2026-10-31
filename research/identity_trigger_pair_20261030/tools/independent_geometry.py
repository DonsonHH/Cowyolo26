"""Separate batch reconstruction, not calling the online selector."""
import math
def reconstruct_candidate(frame,tid,byframe):
 rows=byframe.get(frame,[]);target=next(r for r in rows if r['track_id']==tid)
 x1,y1,x2,y2=target['xyxy']
 a=max(870.,min(1920.,x1));b=max(0.,min(1440.,y1));c=max(870.,min(1920.,x2));d=max(0.,min(1440.,y2))
 visible=max(c-a,0)*max(d-b,0);intersections=[]
 for other in rows:
  if other['track_id'] is None or other['track_id']==tid:continue
  ox,oy,oz,ow=other['xyxy'];ox=max(870.,min(1920.,ox));oz=max(870.,min(1920.,oz));oy=max(0.,min(1440.,oy));ow=max(0.,min(1440.,ow))
  intersections.append(max(min(c,oz)-max(a,ox),0)*max(min(d,ow)-max(b,oy),0))
 overlap=max(intersections,default=0.)/visible if visible else 0.
 margin=min(a-870,b,1920-c,1440-d);factor=max(0,min(margin/16,1))
 return {'frame0':frame,'track_id':tid,'xyxy':list(target['xyxy']),'clipped_xyxy':[a,b,c,d],
  'visible_box_area_px2':visible,'minimum_edge_margin_px':margin,'max_other_box_overlap_fraction':overlap,'selection_score':visible*(1-overlap)*factor}

def verify_selection(selection,processed,byframe):
 frame=selection['event_frame0'];tid=selection['track_id'];available=[f for f in processed if frame-25<=f<=frame][-6:]
 choices=[reconstruct_candidate(f,tid,byframe) for f in available if any(r['track_id']==tid for r in byframe.get(f,[]))]
 assert [c['frame0'] for c in choices]==[c['frame0'] for c in selection['candidates']]
 for expected,actual in zip(choices,selection['candidates']):
  for key in ['frame0','track_id','xyxy','clipped_xyxy']:assert expected[key]==actual[key],key
  for key in ['visible_box_area_px2','minimum_edge_margin_px','max_other_box_overlap_fraction','selection_score']:assert math.isclose(expected[key],actual[key],rel_tol=1e-12,abs_tol=1e-9),(key,expected[key],actual[key])
 best=sorted(choices,key=lambda x:(x['selection_score'],x['frame0']))[-1]
 assert best['frame0']==selection['selected']['frame0'] and best['xyxy']==selection['selected']['xyxy']
 assert selection['current']['frame0']==frame and 0<=selection['selected_age_frames']<=25
 assert selection['selected_age_frames']==frame-best['frame0']
 if 'used_candidate' in selection:
  expected=selection['selected'] if selection['policy'] in ['idle_gate','low_priority_parallel'] else selection['current']
  assert selection['used_candidate']==expected
 return len(choices)
