"""Save official JSON and a bounded ZIP-tail request; never downloads the full ZIP."""
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen, getproxies
from urllib.error import HTTPError
from urllib.parse import urlsplit
import hashlib, json, re

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"evidence";OUT.mkdir(parents=True,exist_ok=True)
manifest=OUT/"BECA_metadata_acquisition_v1.json"
assert not manifest.exists()
UA="CattleResearchMetadataAudit/1.0"

def sha(data):
    return hashlib.sha256(data).hexdigest()

def safe_url(url):
    parsed=urlsplit(url)
    return {"scheme":parsed.scheme,"host":parsed.hostname,"path":parsed.path,
            "query_present":bool(parsed.query)}

def acquire(url,name,limit,headers=None):
    path=OUT/name
    assert not path.exists()
    request=Request(url,headers={"User-Agent":UA,"Accept-Encoding":"identity",**(headers or {})})
    try:
        response=urlopen(request,timeout=25)
    except HTTPError as error:
        response=error
    with response:
        code=response.code
        selected={key:response.headers.get(key) for key in ["Content-Type","Content-Length","Content-Range","Accept-Ranges","Date","ETag","Last-Modified","x-webcache-source"] if response.headers.get(key) is not None}
        body=response.read(limit+1)
        exceeded=len(body)>limit
        body=body[:limit]
        final=safe_url(response.geturl())
    path.write_bytes(body)
    row={"requested_URL":url,"final_endpoint_without_query":final,"HTTP_status":code,"headers":selected,
         "saved_file":str(path.resolve()),"saved_bytes":len(body),"sha256":sha(body),
         "read_limit_bytes":limit,"body_exceeded_limit":exceeded}
    return row,body

records=[]
try:
    record,body=acquire("https://api.figshare.com/v2/articles/32070171","BECA_article_32070171_v1.json",2*1024*1024)
    records.append(record)
    assert record["HTTP_status"]==200 and not record["body_exceeded_limit"]
    article=json.loads(body)
    files=article["files"];assert len(files)==1
    file=files[0]
    assert file["id"]==63928608 and file["name"]=="BECA.zip" and file["size"]==20309712996
    assert article["version"]==1
    url=file["download_url"]
    assert urlsplit(url).hostname in {"ndownloader.figshare.com","api.figshare.com"}
    record,body=acquire(url,"BECA_archive_tail_response_v1.bin",131072,{"Range":"bytes=-131072"})
    records.append(record)
    if record["HTTP_status"]==403 and b"Request has expired" in body:
        stamp=datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        fresh=url+("&" if "?" in url else "?")+"metadata_audit="+stamp
        record,body=acquire(fresh,"BECA_archive_tail_response_fresh_v1.bin",131072,{"Range":"bytes=-131072","Cache-Control":"no-cache"})
        record["reason"]="Previous_public_download_redirect_returned_expired_signature_only_same_public_endpoint_refreshed"
        records.append(record)
    total=file["size"]
    match=re.fullmatch(r"bytes ([0-9]+)-([0-9]+)/([0-9]+)",record["headers"].get("Content-Range",""))
    success=(record["HTTP_status"]==206 and not record["body_exceeded_limit"] and match is not None
             and tuple(map(int,match.groups()))==(total-131072,total-1,total) and len(body)==131072)
    result={"status":"OFFICIAL_BECA_JSON_AND_VALID_ZIP_TAIL_RECEIVED" if success else "OFFICIAL_BECA_JSON_RECEIVED_ARCHIVE_RANGE_NOT_ADMITTED",
            "created_UTC":datetime.now(timezone.utc).isoformat(),"article_id":article["id"],"version":article["version"],
            "title":article["title"],"license":article.get("license"),"file":file,
            "records":records,"archive_tail_valid":success,"archive_total_declared_bytes":total,
            "complete_archive_downloaded":False,"image_or_video_decodes":0,"new_model_forwards":0,
            "new_training_updates":0,"existing_proxy_config_detected":bool(getproxies()),
            "proxy_or_network_configuration_changed":False,"whole_goal_complete":False}
except Exception as error:
    result={"status":"BOUNDED_METADATA_ACQUISITION_INCOMPLETE","created_UTC":datetime.now(timezone.utc).isoformat(),
            "records":records,"error_type":type(error).__name__,"error":str(error)[:300],
            "complete_archive_downloaded":False,"image_or_video_decodes":0,"new_model_forwards":0,"whole_goal_complete":False}
manifest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps({"status":result["status"],"HTTP_statuses":[r["HTTP_status"]for r in records],
                  "saved_bytes":sum(r["saved_bytes"]for r in records),"archive_tail_valid":result.get("archive_tail_valid"),
                  "error_type":result.get("error_type")},ensure_ascii=False))
