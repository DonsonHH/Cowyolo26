set -euo pipefail
ROOT=/share/home/renly/projects/idcoo_research_20261026/deployment_audit
mkdir -p "$ROOT/logs"
test ! -e "$ROOT/dependencies"
test ! -e "$ROOT/logs/runtime_stage_pid.txt"
nohup /share/home/renly/projects/idcoo_research_20261026/env/bin/python -m pip --isolated --disable-pip-version-check --no-input install --index-url https://pypi.org/simple --only-binary=:all: --target "$ROOT/dependencies" onnx==1.19.0 onnxruntime==1.23.2 numpy==2.2.6 > "$ROOT/logs/runtime_stage.out" 2> "$ROOT/logs/runtime_stage.err" < /dev/null &
echo "$!" | tee "$ROOT/logs/runtime_stage_pid.txt"
