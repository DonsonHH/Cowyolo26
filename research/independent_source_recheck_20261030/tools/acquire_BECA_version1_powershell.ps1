$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$rawPath = Join-Path $taskRoot 'evidence/BECA_article_32070171_version1_powershell.json'
$reportPath = Join-Path $taskRoot 'evidence/BECA_version1_powershell_acquisition.json'
if ((Test-Path -LiteralPath $rawPath) -or (Test-Path -LiteralPath $reportPath)) {
    throw 'New artifact paths required'
}
$record = [ordered]@{
    created_UTC = [DateTime]::UtcNow.ToString('o')
    requested_URL = 'https://api.figshare.com/v2/articles/32070171/versions/1'
    transport = 'PowerShell Invoke-WebRequest defaults; no proxy or network changes'
    new_model_forwards = 0
    image_or_video_decodes = 0
}
try {
    $response = Invoke-WebRequest -Uri $record.requested_URL -OutFile $rawPath -PassThru -TimeoutSec 25 -MaximumRedirection 5
    $record.HTTP_status = [int]$response.StatusCode
    $record.saved_bytes = (Get-Item -LiteralPath $rawPath).Length
    $record.sha256 = (Get-FileHash -LiteralPath $rawPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $record.raw_file = $rawPath
    $article = Get-Content -LiteralPath $rawPath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($article.version -ne 1 -or $article.files.Count -ne 1 -or $article.files[0].id -ne 63928608) {
        throw 'Unexpected fixed version or file'
    }
    $record.status = 'FIXED_VERSION1_OFFICIAL_JSON_SAVED'
    $record.version = $article.version
    $record.file_id = $article.files[0].id
    $record.archive_bytes_declared = $article.files[0].size
    $record.license = $article.license
} catch {
    $record.status = 'FIXED_VERSION1_GET_NOT_ADMITTED'
    $record.error = $_.Exception.Message
}
$record | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath $reportPath -Encoding UTF8
[pscustomobject]$record | Select-Object status,HTTP_status,saved_bytes,file_id,archive_bytes_declared,error | ConvertTo-Json -Compress
