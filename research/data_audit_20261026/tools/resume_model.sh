set -e
ROOT=/share/home/renly/projects/idcoo_research_20261026
curl --proxy http://127.0.0.1:27831 -sS -fL -C - --connect-timeout 10 --max-time 600 --retry 2 -o "$ROOT/models/yolo26n.pt.partial" 'https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo26n.pt'
printf '%s  %s\n' 9b09cc8bf347f0fc8a5f7657480587f25db09b34bf33b0652110fb03a8ad4fef "$ROOT/models/yolo26n.pt.partial" | sha256sum -c -
mv -n "$ROOT/models/yolo26n.pt.partial" "$ROOT/models/yolo26n.pt"
