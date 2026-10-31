"""Parse actual Linux process CPU ticks without touching its scheduling policy."""
from pathlib import Path
import time,os
def parse_stat(text):
 end=text.rfind(')');assert end>=0
 prefix=text[:end+1];fields=text[end+1:].split();assert len(fields)>=20
 return {'PID':int(prefix.split(' ',1)[0]),'state':fields[0],'utime_ticks':int(fields[11]),
         'stime_ticks':int(fields[12]),'total_CPU_ticks':int(fields[11])+int(fields[12]),
         'nice':int(fields[16]),'starttime_ticks':int(fields[19])}
def snapshot(pid):
 started=time.monotonic_ns();text=(Path('/proc')/str(pid)/'stat').read_text();finished=time.monotonic_ns()
 return {**parse_stat(text),'snapshot_started_monotonic_ns':started,'snapshot_finished_monotonic_ns':finished,
         'clock_ticks_per_second':os.sysconf('SC_CLK_TCK')}
