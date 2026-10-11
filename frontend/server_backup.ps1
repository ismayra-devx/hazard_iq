# ==============================================================================
# Delhi Smart City - Built-in Local HTTP Server (Zero Dependencies)
# Runs natively on Windows PowerShell using the .NET HttpListener API
# ==============================================================================

$port = 9090
$listener = New-Object System.Net.HttpListener
$listener.Prefixes.Add("http://localhost:$port/")

try {
    $listener.Start()
} catch {
    Write-Error "Failed to start listener on port $port. Check if port is already in use."
    exit 1
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Delhi Smart City Map Server" -ForegroundColor Green
Write-Host " URL: http://localhost:$port/" -ForegroundColor White
Write-Host " Serving files from: $PSScriptRoot" -ForegroundColor Gray
Write-Host " Press Ctrl+C in this terminal to stop the server." -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

# Open default browser automatically
Start-Process "http://localhost:$port/index.html"

try {
    while ($listener.IsListening) {
        $context = $listener.GetContext()
        $request = $context.Request
        $response = $context.Response

        $path = $request.Url.LocalPath.TrimStart('/')
        if ([string]::IsNullOrWhiteSpace($path)) {
            $path = "index.html"
        }

        $fullPath = Join-Path $PSScriptRoot $path

        if (Test-Path $fullPath -PathType Leaf) {
            $bytes = [System.IO.File]::ReadAllBytes($fullPath)
            $ext = [System.IO.Path]::GetExtension($fullPath).ToLower()

            $contentType = switch ($ext) {
                ".html" { "text/html; charset=utf-8" }
                ".css"  { "text/css; charset=utf-8" }
                ".js"   { "application/javascript; charset=utf-8" }
                ".json" { "application/json; charset=utf-8" }
                default { "application/octet-stream" }
            }

            $response.ContentType = $contentType
            $response.ContentLength64 = $bytes.Length
            $response.OutputStream.Write($bytes, 0, $bytes.Length)
        } else {
            $response.StatusCode = 404
            $errBytes = [System.Text.Encoding]::UTF8.GetBytes("404 Not Found")
            $response.ContentLength64 = $errBytes.Length
            $response.OutputStream.Write($errBytes, 0, $errBytes.Length)
        }

        $response.Close()
    }
} finally {
    $listener.Stop()
    Write-Host "Server stopped." -ForegroundColor Red
}
