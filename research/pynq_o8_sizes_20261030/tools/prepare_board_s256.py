from pathlib import Path
import json,shutil,hashlib
ROOT=Path(__file__).resolve().parents[1];PROJECT=ROOT.parent
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
old=PROJECT/'pynq_rot192_compile_20261029'
script=(old/'tools/board_cow_vectors.py').read_text().replace('192','256')
file=ROOT/'tools/board_s256_vectors.py';file.write_text(script,newline='\n')
prepare=(old/'tools/prepare_board_vectors.py').read_text().replace("q=ROOT/'delivery/results/qualification'","q=ROOT/'delivery/s256/results/qualification'")
prepare=prepare.replace('board_cow_vectors.py','board_s256_vectors.py').replace('board_vectors_v1.json','board_s256_v1.json')
prepare=prepare.replace("'size':192","'size':256").replace('board_payload','board_payload_s256').replace('board_vectors_payload','board_s256_payload').replace('FROZEN_BEFORE_NEW_ROT192_ACTUAL_BOARD_VECTOR_QUALIFICATION','FROZEN_BEFORE_SAME_ENGINE_S256_ACTUAL_BOARD_VECTOR_QUALIFICATION')
file=ROOT/'tools/prepare_s256_payload_generated.py';file.write_text(prepare,newline='\n')
print(json.dumps({'script_sha256':sha(ROOT/'tools/board_s256_vectors.py'),'size':256,'new_firmware_programming':False}))
