$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$protocol=Get-Content -LiteralPath (Join-Path $taskRoot 'protocol/BECA_visual_QA_v1.json') -Raw -Encoding UTF8 | ConvertFrom-Json
foreach ($member in $protocol.new_acquisition_members) {
    & (Join-Path $PSScriptRoot 'fetch_BECA_range_v1.ps1') -Start $member.header_request_start -Length 30 -Name ("BECA_"+$member.alias+"_header_v1")
    $report=Get-Content -LiteralPath (Join-Path $taskRoot ("evidence/BECA_"+$member.alias+"_header_v1.json")) -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $report.strict_range_received) { throw "Header not received for $($member.alias)" }
}
