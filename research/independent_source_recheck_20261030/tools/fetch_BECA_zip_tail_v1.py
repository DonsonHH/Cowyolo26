"""One bounded native-client request to the declared public archive, no full download."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib, json, re, subprocess

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"evidence"
article_path=OUT/"BECA_article_32070171_version1_powershell.json"
article=json.loads(article_path.read_text(encoding="utf-8-sig"))
assert article["version"]==1 and len(article["files"])==1
file=article["files"][0]
assert file["id"]==63928608 and file["size"]==20309712996
assert file["download_url"]=="https://ndownloader.figshare.com/files/63928608"
assert file["supplied_md5"]==file["computed_md5"]=="8f4c06835a7d2dba1a6dbc74e34d38b3"
body_path=OUT/"BECA_zip_tail_native_v1.bin"
report=OUT/"BECA_zip_tail_native_v1.json"
assert not report.exists() and not body_path.exists()
template="|".join(["%{http_code}","%{size_download}","%{num_redirects}","%header{content-range}","%header{content-length}","%header{accept-ranges}"])
args=["curl.exe","--location","--fail-with-body","--silent","--show-error",
      "--connect-timeout","10","--max-time","25","--max-filesize","131072",
      "--header","Range: bytes=-131072","--header","Accept-Encoding: identity",
      "--output",str(body_path),"--write-out",template,file["download_url"]]
run=subprocess.run(args,capture_output=True,text=True,encoding="utf-8",errors="replace",timeout=35)
parts=run.stdout.split("|")
body=body_path.read_bytes()if body_path.exists()else b""
total=file["size"]
success=(run.returncode==0 and len(parts)==6 and parts[0]=="206"
         and parts[3]==f"bytes {total-131072}-{total-1}/{total}" and len(body)==131072)
def xml_field(tag):
    match=re.search(rb"<"+tag.encode()+rb">(.*?)</"+tag.encode()+rb">",body)
    return match[1].decode(errors="replace")[:200]if match else None
value={"status":"DECLARED_PUBLIC_ZIP_STRICT_TAIL_RANGE_RECEIVED" if success else "DECLARED_PUBLIC_ZIP_TAIL_NOT_ADMITTED",
       "created_UTC":datetime.now(timezone.utc).isoformat(),"requested_URL":file["download_url"],
       "request_range":"bytes=-131072","article_source_sha256":hashlib.sha256(article_path.read_bytes()).hexdigest(),
       "native_client_exit_code":run.returncode,"native_telemetry_no_URLs":run.stdout,
       "stderr":run.stderr[:800],"saved_file":str(body_path.resolve())if body_path.exists()else None,
       "saved_bytes":len(body),"sha256":hashlib.sha256(body).hexdigest(),
       "archive_declared_bytes":total,"strict_range_received":success,
       "response_error_code":xml_field("Code"),"response_error_message":xml_field("Message"),
       "no_entire_archive_download":True,"image_or_video_decodes":0,"new_model_forwards":0,
       "network_or_proxy_configuration_changed":False,"whole_goal_complete":False}
report.write_text(json.dumps(value,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({k:value[k]for k in ["status","native_client_exit_code","native_telemetry_no_URLs","saved_bytes","strict_range_received","response_error_code","response_error_message"]}))
