$ErrorActionPreference='Stop'
$taskRoot=Split-Path -Parent $PSScriptRoot
$taskSource=Join-Path $taskRoot 'inputs\multicam_original.mp4'
$taskProxy=Join-Path $taskRoot 'inputs\multicam_annotation.webm'
$taskExpected='5d1d8c197abbebfd98d11b7900fe2655013acc43cf5e01bebc7c72a3bcde95a1'
if ((Get-FileHash -LiteralPath $taskSource -Algorithm SHA256).Hash.ToLowerInvariant() -ne $taskExpected) { throw 'Source checksum mismatch' }
if (-not (Test-Path -LiteralPath $taskProxy)) {
    & ffmpeg -hide_banner -loglevel error -nostdin -i $taskSource -map 0:v:0 -an -vf scale=1280:720 -c:v libvpx-vp9 -deadline realtime -cpu-used 8 -row-mt 1 -threads 4 -crf 32 -b:v 0 -n $taskProxy
    if ($LASTEXITCODE -ne 0) { throw 'Proxy encoding failed' }
}
& ffprobe -v error -count_frames -show_entries stream=codec_name,width,height,avg_frame_rate,nb_read_frames -show_entries format=duration -of json $taskProxy
if ($LASTEXITCODE -ne 0) { throw 'Proxy probe failed' }
& ffmpeg -hide_banner -v error -nostdin -threads 4 -xerror -i $taskProxy -an -f null NUL
if ($LASTEXITCODE -ne 0) { throw 'Proxy decode failed' }
Write-Output 'Proxy readable; preserve the separate original-source terminal decoding defect record.'
