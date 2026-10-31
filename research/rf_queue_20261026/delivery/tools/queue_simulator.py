"""Discrete-time cost model, explicitly not a real-time FPGA runtime."""
from collections import deque,Counter
import math

def simulate(arrivals,policy,service=20,horizon=1200,period=10,frontend_cost=3,capacity=4,ttl=120):
    if policy not in ['disabled','nonpreemptive','fits_next_gap','cooperative']:raise ValueError('Unknown policy')
    if min(service,horizon,period,frontend_cost,capacity,ttl)<=0 or frontend_cost>period:raise ValueError('Invalid budget')
    if len({r['job_id'] for r in arrivals})!=len(arrivals):raise ValueError('Duplicate job')
    bytime={}
    for row in arrivals:
        if not 0<=row['ready_tick']<horizon:raise ValueError('Arrival outside session')
        bytime.setdefault(row['ready_tick'],[]).append(row)
    jobs={r['job_id']:{**r,'deadline_tick':r['ready_tick']+ttl,'remaining':service,'work_ticks':0,
          'started_tick':None,'finished_tick':None,'status':'NOT_ARRIVED'} for r in arrivals}
    waiting=deque();front=deque();current_front=None;active=None;front_records=[]
    resource=Counter();max_waiting=0;timeline=[]
    def expire_waiting(t):
        nonlocal waiting
        kept=deque()
        for identity in waiting:
            job=jobs[identity]
            if t>=job['deadline_tick']:job.update(status='EXPIRED_WAITING',finished_tick=t)
            else:kept.append(identity)
        waiting=kept
    for t in range(horizon):
        if t%period==0:front.append({'release_tick':t,'deadline_tick':t+period,'remaining':frontend_cost,'status':'WAITING'})
        expire_waiting(t)
        if active is not None and policy=='cooperative' and t>=jobs[active]['deadline_tick']:
            jobs[active].update(status='EXPIRED_PARTIAL',finished_tick=t);active=None
        for arrival in bytime.get(t,[]):
            job=jobs[arrival['job_id']]
            if policy=='disabled':job.update(status='DISABLED',finished_tick=t)
            elif len(waiting)>=capacity:job.update(status='REJECTED_CAPACITY',finished_tick=t)
            else:job['status']='WAITING';waiting.append(job['job_id'])
        max_waiting=max(max_waiting,len(waiting));assert len(waiting)<=capacity
        blocked=active is not None and policy=='nonpreemptive'
        if not blocked and current_front is None:
            while front and front[0]['deadline_tick']<=t:
                old=front.popleft();old.update(status='EXPIRED',finished_tick=t);front_records.append(old)
            if front:current_front=front.popleft();current_front['status']='RUNNING'
        if blocked:
            kind='background'
        elif current_front is not None:
            kind='frontend'
        else:
            if active is None and waiting:
                remaining_gap=period-t%period
                if policy!='fits_next_gap' or service<=remaining_gap:
                    active=waiting.popleft();jobs[active].update(status='RUNNING',started_tick=t)
            kind='background' if active is not None else 'idle'
        if kind=='frontend':
            current_front['remaining']-=1
            if current_front['remaining']==0:
                current_front.update(status='ON_TIME' if t+1<=current_front['deadline_tick'] else 'LATE',finished_tick=t+1)
                front_records.append(current_front);current_front=None
        elif kind=='background':
            job=jobs[active];job['remaining']-=1;job['work_ticks']+=1
            if job['remaining']==0:
                job.update(status='COMPLETED' if t+1<=job['deadline_tick'] else 'COMPLETED_LATE',finished_tick=t+1);active=None
        resource[kind]+=1;timeline.append(kind)
    for job in jobs.values():
        if job['status'] in ['WAITING','RUNNING']:job['status']='PENDING_AT_HORIZON'
        assert job['status']!='NOT_ARRIVED'
    if current_front is not None:current_front.update(status='PENDING_AT_HORIZON');front_records.append(current_front)
    while front:
        row=front.popleft();row['status']='PENDING_AT_HORIZON';front_records.append(row)
    generated=(horizon-1)//period+1
    assert len(front_records)==generated and sum(resource.values())==horizon
    assert sum(j['work_ticks'] for j in jobs.values())==resource['background']
    assert all(0<=j['work_ticks']<=service for j in jobs.values())
    status_counts=dict(Counter(j['status'] for j in jobs.values()))
    completed=[j for j in jobs.values() if j['status']=='COMPLETED']
    late=sum(f['status']=='LATE' or f['status']=='EXPIRED' or f['status']=='PENDING_AT_HORIZON' and f['deadline_tick']<=horizon for f in front_records)
    latencies=sorted(f['finished_tick']-f['release_tick'] for f in front_records if f['status'] in ['ON_TIME','LATE'])
    def percentile(q):return latencies[max(0,math.ceil(len(latencies)*q)-1)] if latencies else None
    return {'policy':policy,'background_cost_ticks':service,'horizon_ticks':horizon,'resource_ticks':dict(resource),
            'max_waiting':max_waiting,'capacity':capacity,'background_status_counts':status_counts,
            'jobs_total':len(jobs),'jobs_on_time':len(completed),'foreground_frames':generated,'foreground_deadline_misses':int(late),
            'foreground_response_p95_ticks':percentile(.95),'foreground_response_p99_ticks':percentile(.99),
            'jobs':list(jobs.values()),'foreground_records':front_records,'resource_timeline':timeline,
            'scope':'Abstract fixed-cost tick model; no hardware measurement, no conversion to counting recall'}
