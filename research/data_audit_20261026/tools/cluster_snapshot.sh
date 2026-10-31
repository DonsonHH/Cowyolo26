set -e
id -un
hostname
printenv HOME
sinfo -o '%P|%a|%l|%D|%t|%N|%G'
squeue -u renly -o '%.18i|%.9P|%.24j|%.8T|%.10M|%.10l|%.6D|%R'
scontrol show partition -o
df -hT /share/home/renly
command -v python python3 conda ffmpeg ffprobe curl wget mihomo || true
find /share/home/renly -maxdepth 2 -type d \( -iname '*cow*' -o -iname '*yolo*' -o -iname '*audit*' -o -iname '*env*' \) -print
python - <<'PY'
import importlib.util,sys,json
print(json.dumps({'python':sys.version,'packages':{k:bool(importlib.util.find_spec(k)) for k in ('torch','cv2','numpy','PIL','ultralytics','yaml')}}))
PY
curl --noproxy '*' -IL --connect-timeout 10 --max-time 20 'https://data.bris.ac.uk/datasets/2inu67jru7a6821kkgehxg3cv2/readme.txt'
