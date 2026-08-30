<#
.SYNOPSIS
    Downloads a GGUF model file from HuggingFace using direct IP connection.

.DESCRIPTION
    Alternative download method that connects to HuggingFace CDN servers
    directly via IP address using PowerShell 7's .NET SslStream.
    Useful when standard HTTPS downloads fail due to SSL or routing issues.

    Requires PowerShell 7 (pwsh) and an elevated terminal.

.PARAMETER Repo
    HuggingFace repo (e.g., "bartowski/Qwen2.5-Coder-7B-Instruct-GGUF").

.PARAMETER File
    Exact GGUF filename. If omitted, lists available files.

.PARAMETER OutDir
    Output directory. Defaults to script's directory.

.EXAMPLE
    pwsh -ExecutionPolicy Bypass -File HfDownload.ps1 "bartowski/Qwen2.5-Coder-7B-Instruct-GGUF" "Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf"
#>
param(
    [Parameter(Mandatory, Position=0)]
    [string]$Repo,

    [Parameter(Position=1)]
    [string]$File,

    [string]$OutDir
)

$ErrorActionPreference = 'Stop'
if (-not $OutDir) { $OutDir = $PSScriptRoot }

$US_EAST_IPS = @(
    "35.173.17.142", "34.231.87.187", "44.217.206.136",
    "3.216.102.62", "34.230.200.86", "100.50.185.240",
    "100.57.83.12", "98.90.123.60", "100.31.16.245", "100.29.213.216"
)
$RouteExe = "$env:SystemRoot\System32\route.exe"

# --- Find Wi-Fi gateway ---

function Find-WifiGateway {
    $output = & $RouteExe print -4 0.0.0.0 2>&1 | Out-String
    $routes = @()
    foreach ($line in $output -split "`n") {
        $parts = $line.Trim() -split '\s+'
        if ($parts.Count -ge 5 -and $parts[0] -eq '0.0.0.0' -and $parts[1] -eq '0.0.0.0' -and $parts[2] -ne 'On-link') {
            $routes += @{ Gateway = $parts[2]; Metric = [int]$parts[4] }
        }
    }
    if ($routes.Count -eq 0) { return $null }
    $routes | Sort-Object { $_.Metric } -Descending | Select-Object -First 1 -ExpandProperty Gateway
}

function Find-WifiIfIndex {
    $ipconfig = & "$env:SystemRoot\System32\ipconfig.exe" 2>&1 | Out-String
    $inWifi = $false
    foreach ($line in $ipconfig -split "`n") {
        if ($line -match 'Wi-Fi|Wireless') { $inWifi = $true }
        elseif ($inWifi -and $line -match '%(\d+)') { return [int]$Matches[1] }
        elseif ($inWifi -and $line.Trim() -and -not $line.StartsWith(' ')) { $inWifi = $false }
    }
    return 0
}

# --- Route management ---

$script:routes = @()

function Add-Route([string]$IP, [string]$Gateway, [int]$IfIdx) {
    $args2 = "add $IP mask 255.255.255.255 $Gateway"
    if ($IfIdx -gt 0) { $args2 += " IF $IfIdx" }
    $args2 += " metric 1"
    & $RouteExe $args2.Split(' ') 2>&1 | Out-Null
    $script:routes += $IP
}

function Remove-AllRoutes {
    foreach ($ip in $script:routes) { & $RouteExe delete $ip 2>&1 | Out-Null }
    $script:routes = @()
}

# --- Main ---

Write-Host "`n[1/3] Setup..." -ForegroundColor Cyan
$gateway = Find-WifiGateway
if (-not $gateway) { Write-Error "Cannot find Wi-Fi gateway. Ensure Wi-Fi is connected." }
$ifIdx = Find-WifiIfIndex
Write-Host "  Gateway: $gateway (IF $ifIdx)"

# List files if not specified
if (-not $File) {
    Write-Host "`n  Fetching files from huggingface.co/$Repo..." -ForegroundColor DarkGray
    $response = Invoke-RestMethod -Uri "https://huggingface.co/api/models/$Repo/tree/main" -TimeoutSec 30
    $ggufFiles = @($response | Where-Object { $_.path -like '*.gguf' -and $_.type -eq 'file' } |
        Select-Object @{N='Name';E={$_.path}}, @{N='SizeGB';E={[math]::Round($_.size/1GB,2)}} | Sort-Object SizeGB)
    if ($ggufFiles.Count -eq 0) { Write-Error "No GGUF files in $Repo" }
    Write-Host "`n  Available:" -ForegroundColor Yellow
    for ($i=0; $i -lt $ggufFiles.Count; $i++) {
        $f = $ggufFiles[$i]
        $lbl = if ($f.Name -match 'Q4_K_M') {' (recommended)'} else {''}
        Write-Host "    [$($i+1)] $($f.Name) ($($f.SizeGB) GB)$lbl"
    }
    $choice = Read-Host "`n  Select [1-$($ggufFiles.Count)]"
    $File = $ggufFiles[[int]$choice - 1].Name
}
Write-Host "  File: $File" -ForegroundColor Green

# Get redirect URL
Write-Host "`n[2/3] Getting download URL..." -ForegroundColor Cyan
$hfUrl = "https://huggingface.co/$Repo/resolve/main/$File"
$redirectUrl = $null
try { Invoke-WebRequest -Uri $hfUrl -Method HEAD -MaximumRedirection 0 -ErrorAction Stop } catch {
    $redirectUrl = $_.Exception.Response.Headers.Location.ToString()
}
if (-not $redirectUrl) { Write-Error "Failed to get redirect URL from HuggingFace." }
$cdnUri = [System.Uri]$redirectUrl
Write-Host "  CDN: $($cdnUri.Host)"

# Build candidate IPs
$candidates = @()
if ($cdnUri.PathAndQuery -match 'xet-bridge-us') {
    $candidates += $US_EAST_IPS
    Write-Host "  US bridge detected; using US East IPs" -ForegroundColor DarkGray
}
$dnsIPs = @((Resolve-DnsName $cdnUri.Host -Type A -ErrorAction SilentlyContinue).IPAddress)
foreach ($ip in $dnsIPs) { if ($ip -notin $candidates) { $candidates += $ip } }

# Add routes
foreach ($ip in $candidates) { Add-Route $ip $gateway $ifIdx }

# Download
Write-Host "`n[3/3] Downloading..." -ForegroundColor Cyan
$destPath = Join-Path $OutDir $File
$success = $false

try {
    foreach ($ip in $candidates) {
        try {
            Write-Host "  Trying $ip... " -NoNewline

            $tcp = New-Object System.Net.Sockets.TcpClient
            $tcp.ReceiveBufferSize = 8 * 1024 * 1024
            $tcp.Connect($ip, 443)

            $ssl = New-Object System.Net.Security.SslStream($tcp.GetStream(), $false, ({$true}))
            $ssl.AuthenticateAsClient($ip)

            # Verify the cert is from the expected CDN, not a proxy
            $issuer = $ssl.RemoteCertificate.Issuer
            if ($issuer -notmatch 'Amazon|DigiCert|Let''s Encrypt|Google Trust|Cloudflare') {
                Write-Host "unexpected cert issuer" -ForegroundColor Yellow
                $ssl.Close(); $tcp.Close(); continue
            }

            # Send GET
            $req = "GET $($cdnUri.PathAndQuery) HTTP/1.1`r`nHost: $($cdnUri.Host)`r`nUser-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)`r`nAccept: */*`r`nConnection: keep-alive`r`n`r`n"
            $ssl.Write([System.Text.Encoding]::ASCII.GetBytes($req)); $ssl.Flush()

            # Read headers
            $headerBytes = New-Object System.Collections.Generic.List[byte]
            $prev = [byte[]]::new(4)
            while ($true) {
                $b = $ssl.ReadByte(); if ($b -eq -1) { throw "Connection closed" }
                $headerBytes.Add([byte]$b)
                $prev[0]=$prev[1];$prev[1]=$prev[2];$prev[2]=$prev[3];$prev[3]=[byte]$b
                if ($prev[0]-eq13 -and $prev[1]-eq10 -and $prev[2]-eq13 -and $prev[3]-eq10) { break }
            }
            $hdr = [System.Text.Encoding]::ASCII.GetString($headerBytes.ToArray())
            $status = ($hdr -split "`r`n")[0]

            if ($status -notmatch '200') {
                Write-Host $status -ForegroundColor Yellow
                $ssl.Close(); $tcp.Close(); continue
            }

            $contentLength = [long]0
            if ($hdr -match 'content-length:\s*(\d+)') { $contentLength = [long]$Matches[1] }
            Write-Host "200 OK ($([math]::Round($contentLength/1GB,2)) GB)" -ForegroundColor Green
            Write-Host ""

            # Stream to file
            $fs = [System.IO.File]::Create($destPath)
            $buf = New-Object byte[] (4*1024*1024)
            $total = [long]0; $sw = [System.Diagnostics.Stopwatch]::StartNew(); $lr = [long]0

            try {
                while ($total -lt $contentLength) {
                    $n = [int][math]::Min([long]$buf.Length, [long]($contentLength - $total))
                    $read = $ssl.Read($buf, 0, $n); if ($read -eq 0) { break }
                    $fs.Write($buf, 0, $read); $total += $read
                    if ($total - $lr -gt 100MB) {
                        $pct = [math]::Round($total*100/$contentLength,1)
                        $spd = if($sw.Elapsed.TotalSeconds -gt 0){[math]::Round($total/$sw.Elapsed.TotalSeconds/1MB,1)}else{0}
                        $eta = if($spd -gt 0){$r=($contentLength-$total)/($spd*1MB);if($r -gt 60){"$([math]::Round($r/60,1))m"}else{"$([math]::Round($r))s"}}else{'?'}
                        Write-Host "  [$pct%] $([math]::Round($total/1GB,2))GB @ ${spd}MB/s ETA:$eta"
                        $lr = $total
                    }
                }
                Write-Host "  [100%] Done! $([math]::Round($total/1GB,2)) GB in $([math]::Round($sw.Elapsed.TotalMinutes,1)) min" -ForegroundColor Green
            } finally { $fs.Close(); $ssl.Close(); $tcp.Close() }

            if ($total -ge $contentLength * 0.99) { $success = $true }
            else { Write-Warning "Incomplete: $total / $contentLength bytes" }
            break
        }
        catch {
            Write-Host "FAILED ($($_.Exception.Message))" -ForegroundColor Red
            continue
        }
    }
} finally {
    Remove-AllRoutes
}

if (-not $success) { Write-Error "All $($candidates.Count) CDN IPs failed." }
Write-Host "`n  Saved: $destPath" -ForegroundColor Green
