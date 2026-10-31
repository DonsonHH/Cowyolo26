from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
for size in [192,256,320]:
    source=ROOT/'tools'/('launch_formal'+str(size)+'.sh')
    text=source.read_text();assert "Path('/proc'/str(prior['PID']))" in text
    target=source.with_name(source.stem+'_v2.sh');assert not target.exists()
    target.write_text(text.replace("Path('/proc'/str(prior['PID']))","(Path('/proc')/str(prior['PID']))"),newline='\n')
print('Onlylocalpriorprocesspathguardcorrected;originalfailedlaunchpreserved')
