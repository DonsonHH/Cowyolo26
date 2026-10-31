$ErrorActionPreference = 'Stop'
$taskRoot = Split-Path -Parent $PSScriptRoot
$bodyPath = Join-Path $taskRoot 'evidence/BECA_zip_tail_dotnet_v1.bin'
$reportPath = Join-Path $taskRoot 'evidence/BECA_zip_tail_dotnet_v1.json'
if ((Test-Path -LiteralPath $bodyPath) -or (Test-Path -LiteralPath $reportPath)) { throw 'New paths required' }
$articlePath = Join-Path $taskRoot 'evidence/BECA_article_32070171_version1_powershell.json'
$article = Get-Content -LiteralPath $articlePath -Raw -Encoding UTF8 | ConvertFrom-Json
if ($article.version -ne 1 -or $article.files[0].id -ne 63928608 -or $article.files[0].size -ne 20309712996) { throw 'Unexpected source' }
$uri = [Uri]$article.files[0].download_url
if ($uri.AbsoluteUri -ne 'https://ndownloader.figshare.com/files/63928608') { throw 'Unexpected endpoint' }
$record = [ordered]@{
    status = 'STRICT_RANGE_NOT_ADMITTED'
    created_UTC = [DateTime]::UtcNow.ToString('o')
    requested_URL = $uri.AbsoluteUri
    client = '.NET HttpClient ResponseHeadersRead with system defaults'
    requested_range = 'bytes=-131072'
    archive_declared_bytes = 20309712996
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
$null = $request.Headers.TryAddWithoutValidation('Range','bytes=-131072')
$null = $request.Headers.TryAddWithoutValidation('Accept-Encoding','identity')
try {
    $response = $client.SendAsync($request,[Net.Http.HttpCompletionOption]::ResponseHeadersRead).GetAwaiter().GetResult()
    $record.HTTP_status = [int]$response.StatusCode
    $record.content_range = [string]$response.Content.Headers.ContentRange
    $record.content_length = $response.Content.Headers.ContentLength
    $record.final_host = $response.RequestMessage.RequestUri.Host
    $record.final_path = $response.RequestMessage.RequestUri.AbsolutePath
    $expectedRange = 'bytes 20309581924-20309712995/20309712996'
    $strict = $record.HTTP_status -eq 206 -and $record.content_range -eq $expectedRange
    $limit = if ($strict) { 131073 } else { 4096 }
    $stream = $response.Content.ReadAsStream()
    $memory = [IO.MemoryStream]::new()
    $buffer = [byte[]]::new(8192)
    while ($memory.Length -lt $limit) {
        $count = $stream.Read($buffer,0,[int][Math]::Min($buffer.Length,$limit-$memory.Length))
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
    $record.strict_range_received = $strict -and $data.Length -eq 131072
    if ($record.strict_range_received) { $record.status = 'STRICT_ZIP_TAIL_RANGE_RECEIVED' }
} catch {
    $record.error_type = $_.Exception.GetType().FullName
    $record.error = $_.Exception.Message
} finally {
    $request.Dispose()
    $client.Dispose()
    $handler.Dispose()
}
$record | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath $reportPath -Encoding UTF8
[pscustomobject]$record | Select-Object status,HTTP_status,content_range,saved_bytes,strict_range_received,error | ConvertTo-Json -Compress
