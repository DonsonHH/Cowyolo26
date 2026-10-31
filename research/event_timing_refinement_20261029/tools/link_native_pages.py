from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
doc=ROOT/'完成时间细化与复核重点.md';text=doc.read_text(encoding='utf-8')
for i in range(1,13):
    ID=f'R{i:02d}';first=ROOT/'results/native_timing'/f'{ID}_page_01.jpg';second=first.with_name(f'{ID}_page_02.jpg');assert first.exists()
    label=f'[{ID}](<{first.as_posix()}>)'
    if second.exists():label+=f'（[续页](<{second.as_posix()}>)）'
    token='| '+ID+' |';assert text.count(token)==1;text=text.replace(token,'| '+label+' |')
doc.write_bytes(text.encode('utf-8'))
