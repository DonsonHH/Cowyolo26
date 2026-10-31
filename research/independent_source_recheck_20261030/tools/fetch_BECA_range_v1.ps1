param(
    [Parameter(Mandatory=$true)][long]$Start,
    [Parameter(Mandatory=$true)][int]$Length,
    [Parameter(Mandatory=$true)][string]$Name
)
$ErrorActionPreference = 'Stop'
if ($Name -notmatch '^[A-Za-z0-9_-]+$' -or $Start -lt 0 -or $Length -lt 1 -or $Length -gt 16777216) { throw 'Unsafe or excessive range' }
$taskRoot = Split-Path -Parent $PSScriptRoot
$bodyPath = Join-Path $taskRoot "evidence/$Name.bin"
$reportPath = Join-Path $taskRoot "evidence/$Name.json"
if ((Test-Path -LiteralPath $bodyPath) -or (Test-Path -LiteralPath $reportPath)) { throw 'New paths required' }
$articlePath = Join-Path $taskRoot 'evidence/BECA_article_32070171_version1_powershell.json'
$article = Get-Content -LiteralPath $articlePath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($article.version -ne 1 -or $article.files[0].id -ne 63928608 -or $article.files[0].size -ne 20309712996) { throw 'Unexpected source' }
[long]$total = $article.files[0].size
[long]$end = $Start + $Length - 1
if ($end -ge $total) { throw 'Range exceeds archive' }
$uri = [Uri]$article.files[0].download_url
if ($uri.AbsoluteUri -ne 'https://ndownloader.figshare.com/files/63928608') { throw 'Unexpected endpoint' }
$range = "bytes=$Start-$end"
$expected = "bytes $Start-$end/$total"
$record = [ordered]@{
    status = 'STRICT_BOUNDED_RANGE_NOT_ADMITTED'
    created_UTC = [DateTime]::UtcNow.ToString('o')
    requested_URL = $uri.AbsoluteUri
    requested_range = $range
    archive_declared_bytes = $total
    client = '.NET HttpClient ResponseHeadersRead with system defaults'
    complete_archive_downloaded = $false
    image_or_video_decodes = 0
    new_model_forwards = 0
    network_or_proxy_configuration_changed = $false
}
$handler = [Net.Http.HttpClientHandler]::new()
$handler.AllowAutoRedirect = $true
$handler.AutomaticDecompression = [Net.DecompressionMethods]::None
$client = [Net.Http.HttpClient]::new($handler)
$client.Timeout = [TimeSpan]::FromSeconds(25)
$request = [Net.Http.HttpRequestMessage]::new([Net.Http.HttpMethod]::Get, $uri)
$null = $request.Headers.TryAddWithoutValidation('Range',$range)
$null = $request.Headers.TryAddWithoutValidation('Accept-Encoding','identity')
$null = $request.Headers.TryAddWithoutValidation('Cache-Control','no-cache')
$cancel = [Threading.CancellationTokenSource]::new([TimeSpan]::FromSeconds(40))
try {
    $response = $client.SendAsync($request,[Net.Http.HttpCompletionOption]::ResponseHeadersRead,$cancel.Token).GetAwaiter().GetResult()
    $record.HTTP_status = [int]$response.StatusCode
    $record.content_range = [string]$response.Content.Headers.ContentRange
    $record.content_length = $response.Content.Headers.ContentLength
    $record.etag = [string]$response.Headers.ETag
    $record.last_modified = [string]$response.Content.Headers.LastModified
    $record.final_host = $response.RequestMessage.RequestUri.Host
    $record.final_path = $response.RequestMessage.RequestUri.AbsolutePath
    $strict = $record.HTTP_status -eq 206 -and $record.content_range -eq $expected
    $limit = if ($strict) { $Length+1 } else { 4096 }
    $stream = $response.Content.ReadAsStream()
    $memory = [IO.MemoryStream]::new()
    $buffer = [byte[]]::new(65536)
    while ($memory.Length -lt $limit) {
        $count = $stream.ReadAsync($buffer,0,[int][Math]::Min($buffer.Length,$limit-$memory.Length),$cancel.Token).GetAwaiter().GetResult()
        if ($count -eq 0) { break }
        $memory.Write($buffer,0,$count)
    }
    $stream.Dispose()
    $response.Dispose()
    $data = $memory.ToArray()
    $memory.Dispose()
    [IO.File]::WriteAllBytes($bodyPath,$data)
    $record.saved_bytes = $data.Length
    $record.sha256 = (Get-FileHash -LiteralPath $bodyPath -Algorithm SHA256).Hash.ToLowerInvariant()
    $record.saved_file = $bodyPath
    $record.strict_range_received = $strict -and $data.Length -eq $Length
    if ($record.strict_range_received) { $record.status = 'STRICT_BOUNDED_RANGE_RECEIVED' }
} catch {
    $record.error_type = $_.Exception.GetType().FullName
    $record.error = $_.Exception.Message
} finally {
    $cancel.Dispose()
    $request.Dispose()
    $client.Dispose()
    $handler.Dispose()
}
$record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reportPath -Encoding UTF8
[pscustomobject]$record | Select-Object status,HTTP_status,content_range,saved_bytes,strict_range_received,error | ConvertTo-Json -Compress
