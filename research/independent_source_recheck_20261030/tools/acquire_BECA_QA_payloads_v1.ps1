$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$plan=Get-Content -LiteralPath (Join-Path $taskRoot 'results/BECA_QA_payload_ranges_v1.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($member in $plan.members) {
    & (Join-Path $PSScriptRoot 'fetch_BECA_range_v1.ps1') -Start $member.payload_request_start -Length $member.payload_request_length -Name ("BECA_"+$member.alias+"_payload_v1")
    $report=Get-Content -LiteralPath (Join-Path $taskRoot ("evidence/BECA_"+$member.alias+"_payload_v1.json")) -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $report.strict_range_received) { throw "Payload not received for $($member.alias)" }
}
