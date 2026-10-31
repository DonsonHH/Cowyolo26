"""Bounded read-only discovery: exact previous address, router control, host names."""
from pathlib import Path
from datetime import datetime, timezone
from ctypes import wintypes
import ctypes, hashlib, json, socket, subprocess, time

ROOT=Path(__file__).resolve().parents[1]
PROJECT=ROOT.parent
target=ROOT/"evidence/router_static_probe_v1.json"
assert not target.exists()
network=json.loads((PROJECT/"pynq_lowres_20261029/evidence/network_after_power01.json").read_text())
old=next(r for r in network["ethernet_neighbors"] if r["IPAddress"]=="192.168.2.99")
source="192.168.3.13"
function=ctypes.WinDLL("iphlpapi").SendARP
function.argtypes=[wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,ctypes.POINTER(wintypes.ULONG)]
function.restype=wintypes.DWORD
def address(value):
    return int.from_bytes(socket.inet_aton(value),"little")
arps=[]
for dest in ["192.168.3.1","192.168.2.99"]:
    buffer=(wintypes.ULONG*2)()
    length=wintypes.ULONG(ctypes.sizeof(buffer))
    start=time.monotonic()
    code=int(function(address(dest),address(source),buffer,ctypes.byref(length)))
    mac="-".join(f"{v:02X}" for v in bytes(buffer)[:length.value]) if code==0 else None
    arps.append({"destination":dest,"source_interface_IP":source,"return_code":code,
                 "returned_bytes":length.value,"MAC":mac,"elapsed_s":time.monotonic()-start,
                 "matches_prior_board_MAC":mac==old["LinkLayerAddress"] if mac else None})
dns=[]
for name in ["pynq","pynq.local"]:
    command=["pwsh","-NoProfile","-NonInteractive","-Command",
             "try { Resolve-DnsName -Name '"+name+"' -Type A -Server 192.168.3.1 -DnsOnly -QuickTimeout -ErrorAction Stop | Select-Object Name,IPAddress,Type | ConvertTo-Json -Compress } catch { [Console]::Error.WriteLine($_.Exception.Message); exit 1 }"]
    try:
        proc=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,encoding="utf-8",errors="replace",timeout=15)
        dns.append({"name":name,"server":"192.168.3.1","exit_code":proc.returncode,
                    "stdout":proc.stdout.strip(),"stderr":proc.stderr.strip()})
    except subprocess.TimeoutExpired:
        dns.append({"name":name,"server":"192.168.3.1","status":"timeout15s"})
result={"status":"PRIOR_STATIC_ADDRESS_AND_TWO_HOSTNAMES_ONLY_NO_NETWORK_CONFIGURATION_CHANGE",
        "created_UTC":datetime.now(timezone.utc).isoformat(),"ARP":arps,"DNS":dns,
        "prior_board_MAC_not_assumed_stable":old["LinkLayerAddress"],
        "network_configuration_changed":False,"credentials_sent":False,"new_model_forwards":0,
        "scope":"SendARP cannot exclude a device with an off-subnet address; failure does not prove board power or service state.",
        "source_documentation":"https://learn.microsoft.com/en-us/windows/win32/api/iphlpapi/nf-iphlpapi-sendarp"}
target.write_text(json.dumps(result,ensure_ascii=False,indent=2)+chr(10),encoding="utf-8")
print(json.dumps(result,ensure_ascii=False,indent=2))
