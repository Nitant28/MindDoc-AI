param(
    [string]$DownloadUrl = $env:LLAMA_SERVER_DOWNLOAD_URL
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$destDir = Join-Path $scriptDir "..\llama_bin"
if (-not (Test-Path $destDir)) { New-Item -Path $destDir -ItemType Directory | Out-Null }
$outPath = Join-Path $destDir "server.exe"

Write-Host "Destination: $outPath"

if ($DownloadUrl) {
    Write-Host "Attempting download from: $DownloadUrl"
    try {
        Invoke-WebRequest -Uri $DownloadUrl -OutFile $outPath -UseBasicParsing -ErrorAction Stop
        Write-Host "Downloaded server to: $outPath"
        exit 0
    } catch {
        Write-Warning "Download failed: $($_.Exception.Message)"
    }
}

Write-Host "No download URL provided or automatic download failed."
Write-Host "Options:"
Write-Host "  1) Provide a direct download URL via environment variable LLAMA_SERVER_DOWNLOAD_URL or parameter -DownloadUrl"
Write-Host "     Example: .\download_llama_server.ps1 -DownloadUrl 'https://example.com/server.exe'"
Write-Host "  2) Manually place a prebuilt server binary at: $outPath"
Write-Host "     (create the 'llama_bin' folder if it doesn't exist)"
Write-Host "  3) Build from source by cloning https://github.com/ggerganov/llama.cpp and building the server on Windows (requires Visual Studio/CMake)"

Write-Host "If you place `server.exe` in the above path, I'll be able to start it automatically when you run the backend."
exit 1
