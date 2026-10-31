$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$protocol=Get-Content -LiteralPath (Join-Path $taskRoot 'protocol/run_v1.json') -Raw -Encoding UTF8 | ConvertFrom-Json
if ($protocol.image_count -ne 90 -or $protocol.source_file_id -ne 63928608) { throw 'Unexpected frozen protocol' }
$evidence=Join-Path $taskRoot 'evidence'
if (-not (Test-Path -LiteralPath $evidence)) { $null=New-Item -ItemType Directory -Path $evidence }
if (Test-Path -LiteralPath (Join-Path $evidence 'input_acquisition_complete_v1.json')) { throw 'No repeat of completed acquisition' }
$execution=Join-Path $taskRoot 'protocol/execution_v1.json'
if (-not (Test-Path -LiteralPath $execution)) { throw 'Execution and code must be frozen before selected input request' }
$reports=$protocol.images | ForEach-Object -Parallel {
    $ErrorActionPreference='Stop'
    $taskRoot=$using:taskRoot
    $member=$_
    $row=$member.source_record
    $alias=('BECA_img_{0:D2}' -f [int]$member.index)
    $helper=Join-Path $taskRoot 'tools/fetch_BECA_range_v1.ps1'
    & $helper -Start $row.local_header_offset -Length 30 -Name ($alias+'_header_v1') | Out-Null
    $headerReport=Get-Content -LiteralPath (Join-Path $taskRoot ('evidence/'+$alias+'_header_v1.json')) -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $headerReport.strict_range_received) { throw "Header response rejected: $alias" }
    $header=[IO.File]::ReadAllBytes((Join-Path $taskRoot ('evidence/'+$alias+'_header_v1.bin')))
    if ($header.Length -ne 30 -or [BitConverter]::ToUInt32($header,0) -ne 67324752) { throw "Bad local header: $alias" }
    $flags=[BitConverter]::ToUInt16($header,6)
    $method=[BitConverter]::ToUInt16($header,8)
    $crc=[BitConverter]::ToUInt32($header,14)
    $compressed=[BitConverter]::ToUInt32($header,18)
    $uncompressed=[BitConverter]::ToUInt32($header,22)
    $filenameBytes=[BitConverter]::ToUInt16($header,26)
    $extraBytes=[BitConverter]::ToUInt16($header,28)
    if ($flags -ne $row.flags -or $method -ne 8 -or $crc -ne $row.CRC32 -or $filenameBytes -ne $row.filename_bytes) { throw "Local-central mismatch: $alias" }
    if (($compressed -ne $row.compressed_size -and $compressed -ne 4294967295) -or ($uncompressed -ne $row.uncompressed_size -and $uncompressed -ne 4294967295)) { throw "Size mismatch: $alias" }
    $length=[int]($filenameBytes+$extraBytes+$row.compressed_size)
    & $helper -Start ($row.local_header_offset+30) -Length $length -Name ($alias+'_payload_v1') | Out-Null
    $payload=Get-Content -LiteralPath (Join-Path $taskRoot ('evidence/'+$alias+'_payload_v1.json')) -Raw -Encoding UTF8 | ConvertFrom-Json
    if (-not $payload.strict_range_received) { throw "Payload response rejected: $alias" }
    [pscustomobject]@{
        index=[int]$member.index
        status='TWO_STRICT_RANGES_RECEIVED'
        header_bytes=30
        payload_response_bytes=$payload.saved_bytes
        native_source_file=$row.name
    }
} -ThrottleLimit 4
if ($reports.Count -ne 90) { throw "Only $($reports.Count) member acquisition records completed" }
$value=[ordered]@{
    status='ALL90_FROZEN_MEMBERS_TWO_STRICT_RANGES_EACH_RECEIVED'
    completed_UTC=[DateTime]::UtcNow.ToString('o')
    protocol_sha256=(Get-FileHash -LiteralPath (Join-Path $taskRoot 'protocol/run_v1.json') -Algorithm SHA256).Hash.ToLowerInvariant()
    members=@($reports | Sort-Object index)
    image_or_video_decodes=0
    new_model_forwards=0
    network_configuration_changed=$false
}
$value | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $evidence 'input_acquisition_complete_v1.json') -Encoding UTF8
[pscustomobject]@{status=$value.status; members=$reports.Count; saved_range_bytes=($reports | Measure-Object payload_response_bytes -Sum).Sum+2700} | ConvertTo-Json -Compress
