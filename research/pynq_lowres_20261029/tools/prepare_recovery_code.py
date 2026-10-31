from pathlib import Path
root=Path(__file__).resolve().parents[1]
target=root/'tools/board_recovery_inventory.py';assert not target.exists()
source=(root/'tools/board_recovery_root_read.sh').read_text().split("<<'PY'\n",1)[1].rsplit('\nPY',1)[0]
target.write_text(source+'\n',newline='\n')
