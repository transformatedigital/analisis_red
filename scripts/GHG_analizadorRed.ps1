#Requires -Version 5.1
<#
═══════════════════════════════════════════════════════════════════════════
 GHG_analizadorRed.ps1  ·  Escaneo de red MULTI-VLAN (PowerShell nativo)
 - No requiere Python / nmap / instalar nada
 - Ping asíncrono (.NET) + caché ARP (atrapa hosts que bloquean ICMP)
 - Genera metadata_simple.json + areas_config_auto.json + ZIP
   compatible con enriquecer_metadata_kais.py / visualizador_triple_vista.py
═══════════════════════════════════════════════════════════════════════════
#>

# ─────────────────  CONFIG (editar si cambian las VLAN)  ─────────────────
$Empresa   = "Grupo Hernandez Garza"
$Prefijos  = @("10.69.1", "10.69.2")     # las dos VLAN (/24)
$Gateway   = "10.69.1.250"               # puerta de enlace principal
$Interfaz  = "Ethernet0"                  # NIC real (informativo)
$TimeoutMs = 600
# ─────────────────────────────────────────────────────────────────────────

$ErrorActionPreference = "Continue"
$ts      = Get-Date
$tsIso   = $ts.ToString("s")
$tsName  = $ts.ToString("yyyyMMdd_HHmmss")

Write-Host ("=" * 64) -ForegroundColor Cyan
Write-Host "  ESCANEO DE RED  ·  $Empresa" -ForegroundColor Cyan
Write-Host "  VLANs: $($Prefijos -join ', ').0/24   Gateway: $Gateway" -ForegroundColor Cyan
Write-Host ("=" * 64) -ForegroundColor Cyan

# 1) Lista de IPs y ping asíncrono
$ips = foreach ($p in $Prefijos) { 1..254 | ForEach-Object { "$p.$_" } }
Write-Host "[1/4] Ping a $($ips.Count) direcciones (async, ~30-60s)..." -ForegroundColor Green

$pingMap = @{}
foreach ($ip in $ips) {
    $ping = New-Object System.Net.NetworkInformation.Ping
    $pingMap[$ip] = $ping.SendPingAsync($ip, $TimeoutMs)
}
try { [System.Threading.Tasks.Task]::WaitAll([System.Threading.Tasks.Task[]]@($pingMap.Values)) } catch {}

$alive = @{}
foreach ($ip in $ips) {
    try {
        $r = $pingMap[$ip].Result
        if ($r.Status -eq 'Success') { $alive[$ip] = [string]$r.RoundtripTime }
    } catch {}
}
Write-Host "      -> $($alive.Count) respondieron a ping" -ForegroundColor Gray

# 2) Tabla ARP (atrapa hosts que bloquean ICMP en la VLAN local)
Write-Host "[2/4] Leyendo tabla ARP..." -ForegroundColor Green
$arp = @{}
foreach ($line in (arp -a)) {
    if ($line -match '(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F]{2}(?:[-:][0-9a-fA-F]{2}){5})') {
        $mac = $Matches[2].Replace('-', ':').ToUpper()
        if ($mac -notmatch '^(FF:FF|01:00:5E|00:00:00)') { $arp[$Matches[1]] = $mac }
    }
}
$extra = 0
foreach ($ip in $arp.Keys) {
    $pfx = ($ip -split '\.')[0..2] -join '.'
    if (($Prefijos -contains $pfx) -and (-not $alive.ContainsKey($ip))) { $alive[$ip] = "0"; $extra++ }
}
if ($extra -gt 0) { Write-Host "      -> $extra host(s) extra por ARP" -ForegroundColor Gray }

# 3) Construir dispositivos (formato 'simple')
Write-Host "[3/4] Resolviendo nombres de $($alive.Count) host(s)..." -ForegroundColor Green
function Get-HostNameSafe($ip) {
    try {
        $t = [System.Net.Dns]::GetHostEntryAsync($ip)
        if ($t.Wait(700)) { return $t.Result.HostName } else { return "" }
    } catch { return "" }
}

$ordenadas = $alive.Keys | Sort-Object { [version]$_ }
$dispositivos = @()
foreach ($ip in $ordenadas) {
    $mac    = if ($arp.ContainsKey($ip)) { $arp[$ip] } else { "N/A" }
    $ms     = [double]($alive[$ip])
    $latSeg = "{0}" -f [math]::Round($ms / 1000.0, 4)
    $esGw   = $ip.EndsWith(".1") -or $ip.EndsWith(".250") -or ($ip -eq $Gateway)
    $mi     = if ($esGw) { @{ prioridad = "CRITICAL" } } else { @{} }
    $dispositivos += [ordered]@{
        ip         = $ip
        mac        = $mac
        vendor     = ""                       # lo completa enriquecer por OUI/MAC
        hostname   = (Get-HostNameSafe $ip)
        latencia   = $latSeg
        estado     = "up"
        es_modem   = $esGw
        modem_info = $mi
    }
}

$nModems = ($dispositivos | Where-Object { $_.es_modem }).Count
$metadata = [ordered]@{
    timestamp               = $tsIso
    empresa                 = $Empresa
    red                     = [ordered]@{ rango = (($Prefijos | ForEach-Object { "$_.0/24" }) -join ', '); gateway = $Gateway; interfaz = $Interfaz }
    velocidad_internet      = [ordered]@{ download = "N/A"; upload = "N/A"; ping_ms = "N/A" }
    total_dispositivos      = $dispositivos.Count
    total_modems_detectados = $nModems
    dispositivos            = $dispositivos
}

$areas = [ordered]@{ "_README" = "Generado automaticamente - revisar"; "_EMPRESA" = $Empresa; "_GENERADO" = $tsIso }
$n = 1
foreach ($d in $dispositivos) {
    if ($d.es_modem) {
        $areas[$d.ip] = [ordered]@{
            area        = "Segmento/VLAN - por definir"
            modem_info  = "Gateway/Router #$n"
            modem_sla   = "Por confirmar"
            mac_address = $d.mac
            notas       = "Detectado como gateway/router (.1/.250)"
        }
        $n++
    }
}

# 4) Guardar (UTF-8 sin BOM) + comprimir
Write-Host "[4/4] Generando archivos..." -ForegroundColor Green
$folder = "diagnostico_$(($Empresa -replace ' ','_'))_$tsName"
New-Item -ItemType Directory -Force -Path $folder | Out-Null
$enc = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText("$folder\metadata_simple.json",  ($metadata | ConvertTo-Json -Depth 6), $enc)
[System.IO.File]::WriteAllText("$folder\areas_config_auto.json",($areas    | ConvertTo-Json -Depth 6), $enc)
$txt = "IP`tMAC`tHostname`tLatencia(s)`r`n" + (($dispositivos | ForEach-Object { "$($_.ip)`t$($_.mac)`t$($_.hostname)`t$($_.latencia)" }) -join "`r`n")
[System.IO.File]::WriteAllText("$folder\hosts_vivos.txt", $txt, $enc)

$zip = "$folder.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $folder -DestinationPath $zip -Force

# Resumen
Write-Host ("=" * 64) -ForegroundColor Cyan
foreach ($p in $Prefijos) {
    $c = ($dispositivos | Where-Object { $_.ip.StartsWith("$p.") }).Count
    Write-Host ("  {0,-14} -> {1} host(s)" -f "$p.0/24", $c)
}
Write-Host "  TOTAL host(s):    $($dispositivos.Count)"
Write-Host "  Gateways/routers: $nModems"
Write-Host "  ZIP generado:     $((Resolve-Path $zip).Path)" -ForegroundColor Yellow
Write-Host ("=" * 64) -ForegroundColor Cyan
Write-Host "  Envia ese .zip para generar el dashboard." -ForegroundColor Green
