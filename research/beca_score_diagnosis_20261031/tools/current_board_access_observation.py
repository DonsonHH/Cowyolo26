from pathlib import Path
from datetime import datetime,timezone
from concurrent.futures import ThreadPoolExecutor
import json,socket,subprocess,time
ROOT=Path(__file__).resolve().parents[1];out=ROOT/"evidence/current_board_access_observation.json";assert not out.exists()
cmd="@(Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -eq '以太网'} | Select-Object IPAddress,PrefixLength,InterfaceIndex) | ConvertTo-Json -Compress"
proc=subprocess.run(["pwsh","-NoProfile","-NonInteractive","-Command",cmd],capture_output=True,text=True,encoding="utf-8",timeout=15)
assert proc.returncode==0
addresses=json.loads(proc.stdout)
addresses=addresses if isinstance(addresses,list)else[addresses]
assert any(r["IPAddress"]=="192.168.3.13"and r["PrefixLength"]==24 for r in addresses)
cmd="@(Get-CimInstance Win32_SerialPort | Select-Object DeviceID,Name) | ConvertTo-Json -Compress"
ports=subprocess.run(["pwsh","-NoProfile","-NonInteractive","-Command",cmd],capture_output=True,text=True,encoding="utf-8",timeout=15)
assert ports.returncode==0
serial=json.loads(ports.stdout)if ports.stdout.strip()else[]
serial=serial if isinstance(serial,list)else[serial]
def probe(task):
    host,port=task
    with socket.socket()as s:
        s.settimeout(.35)
        try:
            s.connect((host,port));return{"host":host,"port":port}
        except OSError:return None
start=time.monotonic()
tasks=[(f"192.168.3.{i}",port)for i in range(1,255)if i!=13 for port in[22,9090]]
with ThreadPoolExecutor(max_workers=32)as pool:found=[r for r in pool.map(probe,tasks)if r]
result={"status":"FRESH_LOCAL_LAN22_9090_AND_SERIAL_ENUMERATION_ONLY_NO_CONFIGURATION_CHANGE",
        "created_UTC":datetime.now(timezone.utc).isoformat(),"PC_IPv4":addresses,"serial_devices":serial,
        "COM6_enumerated":any(r["DeviceID"]=="COM6"for r in serial),"open_candidates":found,
        "subnet":"192.168.3.0/24","ports":[22,9090],"elapsed_s":time.monotonic()-start,
        "credentials_sent":False,"hardware_reset_or_serial_commands":False,
        "network_configuration_changed":False,"new_model_forwards":0,
        "scope":"No candidate in this observation does not prove SD data loss, power state or another subnet absence."}
out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps(result,ensure_ascii=False))
