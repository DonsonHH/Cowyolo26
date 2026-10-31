from process_cpu import parse_stat
import json
text='4321 (worker with ) name) S 1 2 3 4 5 6 7 8 9 10 31 7 0 0 20 10 1 0 123456 4096 2'
r=parse_stat(text)
assert r=={'PID':4321,'state':'S','utime_ticks':31,'stime_ticks':7,'total_CPU_ticks':38,'nice':10,'starttime_ticks':123456}
print(json.dumps({'status':'PROCESS_CPU_FIELD_POSITIONS_AND_PARENTHESES_COMM_PASS','actual_proc_read_or_model_forward':False}))
