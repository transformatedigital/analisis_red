#Requires -Version 5.1
<#
═══════════════════════════════════════════════════════════════════════════
 GHG_analizadorRed.ps1  ·  Escaneo de red MULTI-VLAN (PowerShell nativo) v3
 - PING + ARP (verdad de la VLAN local) + PUERTOS TCP (solo conexiones
   REALMENTE abiertas, para no contar falsos positivos de firewall)
 - Filtra subredes "saturadas" (un firewall que responde por todo el rango)
 - Genera metadata_simple.json + areas_config_auto.json + ZIP
   compatible con enriquecer_metadata_kais.py / visualizador_triple_vista.py
═══════════════════════════════════════════════════════════════════════════
#>

# ─────────────────  CONFIG  ─────────────────
$Empresa        = "Grupo Hernandez Garza"
# Subredes /24 EXTRA (además de la local auto-detectada). Agrega las VLAN reales.
$ExtraPrefijos  = @("10.69.2")
$GatewayPref    = "10.69.1.250"
$PingTimeoutMs  = 1000
$TcpTimeoutMs   = 600
$Puertos        = @(445, 3389, 135, 139, 9100, 80, 443, 22, 8080, 515, 23)
$SaturacionMax  = 230   # si una /24 supera esto via TCP => artefacto de firewall (se descarta)
# ────────────────────────────────────────────

$ErrorActionPreference = "Continue"
$ts     = Get-Date
$tsIso  = $ts.ToString("s")
$tsName = $ts.ToString("yyyyMMdd_HHmmss")

# Auto-detectar subred(es) local(es) /24 (excluye loopback/APIPA/WSL 172.x)
$localPrefijos = @()
try {
    foreach ($a in (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue).IPAddress) {
        if ($a -notmatch '^(127\.|169\.254\.|172\.)') {
            $p = ($a -split '\.')[0..2] -join '.'
            if ($localPrefijos -notcontains $p) { $localPrefijos += $p }
        }
    }
} catch {}
$Prefijos  = @($localPrefijos + $ExtraPrefijos | Select-Object -Unique)
$localSet  = @{}; foreach ($p in $localPrefijos) { $localSet[$p] = $true }

Write-Host ("=" * 64) -ForegroundColor Cyan
Write-Host "  ESCANEO DE RED v3  ·  $Empresa" -ForegroundColor Cyan
Write-Host "  Subredes: $(($Prefijos | ForEach-Object { "$_.0/24" }) -join ', ')" -ForegroundColor Cyan
Write-Host "  Local (ARP confiable): $(($localPrefijos | ForEach-Object { "$_.0/24" }) -join ', ')" -ForegroundColor Cyan
Write-Host ("=" * 64) -ForegroundColor Cyan

$ips    = foreach ($p in $Prefijos) { 1..254 | ForEach-Object { "$p.$_" } }
$alive  = @{}    # ip -> latencia(ms) string
$metodo = @{}    # ip -> 'ping' | 'arp' | 'tcp'

# ── 1) PING (por lotes) ──
Write-Host "[1/5] Ping a $($ips.Count) direcciones..." -ForegroundColor Green
$batch = 64
for ($i = 0; $i -lt $ips.Count; $i += $batch) {
    $chunk = $ips[$i..([Math]::Min($i + $batch - 1, $ips.Count - 1))]
    $map = @{}
    foreach ($ip in $chunk) {
        $pg = New-Object System.Net.NetworkInformation.Ping
        try { $map[$ip] = $pg.SendPingAsync($ip, $PingTimeoutMs) } catch {}
    }
    try { [System.Threading.Tasks.Task]::WaitAll([System.Threading.Tasks.Task[]]@($map.Values)) } catch {}
    foreach ($ip in $chunk) {
        if (-not $map.ContainsKey($ip)) { continue }
        try { $r = $map[$ip].Result; if ($r.Status -eq 'Success') { $alive[$ip] = [string]$r.RoundtripTime; $metodo[$ip] = 'ping' } } catch {}
    }
}
Write-Host "      -> $($alive.Count) por ping" -ForegroundColor Gray

# ── 2) ARP (leído enseguida; verdad de la VLAN local, no se puede falsear) ──
Write-Host "[2/5] Leyendo tabla ARP..." -ForegroundColor Green
$arp = @{}
foreach ($line in (arp -a)) {
    if ($line -match '(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F]{2}(?:[-:][0-9a-fA-F]{2}){5})') {
        $mac = $Matches[2].Replace('-', ':').ToUpper()
        if ($mac -notmatch '^(FF:FF|01:00:5E|00:00:00)') { $arp[$Matches[1]] = $mac }
    }
}
$prefSet = @{}; foreach ($p in $Prefijos) { $prefSet[$p] = $true }
foreach ($ip in $arp.Keys) {
    $pfx = ($ip -split '\.')[0..2] -join '.'
    if ($prefSet.ContainsKey($pfx) -and -not $alive.ContainsKey($ip)) { $alive[$ip] = "0"; $metodo[$ip] = 'arp' }
}
Write-Host "      -> total tras ARP: $($alive.Count)" -ForegroundColor Gray

# ── 3) PUERTOS TCP: SOLO conexiones realmente abiertas (RanToCompletion) ──
Write-Host "[3/5] Probando puertos TCP (solo puertos ABIERTOS reales)..." -ForegroundColor Green
$pendientes = New-Object System.Collections.Generic.List[string]
foreach ($ip in $ips) { if (-not $alive.ContainsKey($ip)) { $pendientes.Add($ip) } }
foreach ($port in $Puertos) {
    if ($pendientes.Count -eq 0) { break }
    $restantes = @($pendientes); $chunk = 128
    for ($i = 0; $i -lt $restantes.Count; $i += $chunk) {
        $grp = $restantes[$i..([Math]::Min($i + $chunk - 1, $restantes.Count - 1))]
        $cl = @{}
        foreach ($ip in $grp) {
            $c = New-Object System.Net.Sockets.TcpClient
            try { $cl[$ip] = @{ c = $c; t = $c.ConnectAsync($ip, $port) } } catch { try { $c.Close() } catch {} }
        }
        Start-Sleep -Milliseconds $TcpTimeoutMs
        foreach ($ip in $grp) {
            if (-not $cl.ContainsKey($ip)) { continue }
            # SOLO 'RanToCompletion' = puerto ABIERTO real (no cuenta RST/rechazo)
            if ($cl[$ip].t.Status -eq 'RanToCompletion') {
                if (-not $alive.ContainsKey($ip)) { $alive[$ip] = "0"; $metodo[$ip] = 'tcp' }
                [void]$pendientes.Remove($ip)
            }
            try { $cl[$ip].c.Close() } catch {}
        }
    }
    Write-Host ("      puerto {0,-5} -> total vivos: {1}" -f $port, $alive.Count) -ForegroundColor DarkGray
}

# ── 3b) Filtro anti-artefacto: descartar /24 saturadas por TCP (firewall que responde por todo el rango) ──
$tcpPorPref = @{}
foreach ($ip in $alive.Keys) { if ($metodo[$ip] -eq 'tcp') { $pfx = ($ip -split '\.')[0..2] -join '.'; $tcpPorPref[$pfx] = 1 + ([int]$tcpPorPref[$pfx]) } }
foreach ($pfx in @($tcpPorPref.Keys)) {
    if ($tcpPorPref[$pfx] -ge $SaturacionMax -and -not $localSet.ContainsKey($pfx)) {
        Write-Host "      [!] Subred $pfx.0/24 descartada: $($tcpPorPref[$pfx]) hosts via TCP = artefacto de firewall" -ForegroundColor Yellow
        foreach ($ip in @($alive.Keys)) {
            if ($metodo[$ip] -eq 'tcp' -and (($ip -split '\.')[0..2] -join '.') -eq $pfx) { $alive.Remove($ip); $metodo.Remove($ip) }
        }
    }
}

# ── 4) Reverse DNS en paralelo ──
Write-Host "[4/5] Resolviendo nombres ($($alive.Count) host)..." -ForegroundColor Green
$dns = @{}
foreach ($ip in $alive.Keys) { try { $dns[$ip] = [System.Net.Dns]::GetHostEntryAsync($ip) } catch {} }
Start-Sleep -Milliseconds 1500
$names = @{}
foreach ($ip in $alive.Keys) { try { if ($dns[$ip].Status -eq 'RanToCompletion') { $names[$ip] = $dns[$ip].Result.HostName } } catch {} }

# ── 5) Construir metadata + ZIP ──
Write-Host "[5/5] Generando archivos..." -ForegroundColor Green
$ordenadas = $alive.Keys | Sort-Object { [version]$_ }
$dispositivos = @()
foreach ($ip in $ordenadas) {
    $mac = if ($arp.ContainsKey($ip)) { $arp[$ip] } else { "N/A" }
    $latSeg = "0"; try { $latSeg = "{0}" -f [math]::Round([double]$alive[$ip] / 1000.0, 4) } catch {}
    $esGw = ($ip -match '\.1$') -or ($ip -eq $GatewayPref)
    $hn = if ($names.ContainsKey($ip)) { $names[$ip] } else { "" }
    $mi = if ($esGw) { @{ prioridad = "CRITICAL" } } else { @{} }
    $dispositivos += [ordered]@{
        ip = $ip; mac = $mac; vendor = ""
        hostname = $hn; latencia = $latSeg; estado = "up"
        es_modem = $esGw; modem_info = $mi; metodo = $metodo[$ip]
    }
}

$nModems  = ($dispositivos | Where-Object { $_.es_modem }).Count
$metadata = [ordered]@{
    timestamp = $tsIso; empresa = $Empresa
    red = [ordered]@{ rango = (($Prefijos | ForEach-Object { "$_.0/24" }) -join ', '); gateway = $GatewayPref; interfaz = ($localPrefijos -join ',') }
    velocidad_internet = [ordered]@{ download = "N/A"; upload = "N/A"; ping_ms = "N/A" }
    total_dispositivos = $dispositivos.Count; total_modems_detectados = $nModems
    dispositivos = $dispositivos
}
$areas = [ordered]@{ "_README" = "Generado automaticamente - revisar"; "_EMPRESA" = $Empresa; "_GENERADO" = $tsIso }
$n = 1
foreach ($d in $dispositivos) { if ($d.es_modem) { $areas[$d.ip] = [ordered]@{ area = "Segmento/VLAN - por definir"; modem_info = "Gateway/Router #$n"; modem_sla = "Por confirmar"; mac_address = $d.mac; notas = "Detectado como gateway (.1)" }; $n++ } }

$folder = "diagnostico_$(($Empresa -replace ' ','_'))_$tsName"
New-Item -ItemType Directory -Force -Path $folder | Out-Null
$enc = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText("$folder\metadata_simple.json",   ($metadata | ConvertTo-Json -Depth 6), $enc)
[System.IO.File]::WriteAllText("$folder\areas_config_auto.json", ($areas    | ConvertTo-Json -Depth 6), $enc)
$txt = "IP`tMAC`tHostname`tMetodo`tLatencia(s)`r`n" + (($dispositivos | ForEach-Object { "$($_.ip)`t$($_.mac)`t$($_.hostname)`t$($_.metodo)`t$($_.latencia)" }) -join "`r`n")
[System.IO.File]::WriteAllText("$folder\hosts_vivos.txt", $txt, $enc)

$zip = "$folder.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $folder -DestinationPath $zip -Force

Write-Host ("=" * 64) -ForegroundColor Cyan
foreach ($p in $Prefijos) {
    $c = ($dispositivos | Where-Object { $_.ip.StartsWith("$p.") }).Count
    $tag = if ($localSet.ContainsKey($p)) { " (local/ARP)" } else { "" }
    Write-Host ("  {0,-14} -> {1} host(s){2}" -f "$p.0/24", $c, $tag)
}
Write-Host "  TOTAL host(s):    $($dispositivos.Count)" -ForegroundColor White
Write-Host "  ZIP generado:     $((Resolve-Path $zip).Path)" -ForegroundColor Yellow
Write-Host ("=" * 64) -ForegroundColor Cyan
Write-Host "  Envia ese .zip para generar el dashboard." -ForegroundColor Green
