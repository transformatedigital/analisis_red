#Requires -RunAsAdministrator
<#
═══════════════════════════════════════════════════════════════════════════
 NETWORK SCANNER - WINDOWS VERSION
 Análisis automático de red para Windows
═══════════════════════════════════════════════════════════════════════════

 USO:
   PowerShell como Administrador:
   .\network_scan_windows.ps1

 REQUISITOS:
   - Windows 10/11
   - PowerShell 5.1 o superior
   - Permisos de Administrador

═══════════════════════════════════════════════════════════════════════════
#>

$ErrorActionPreference = "Continue"

# Colores
function Write-ColorOutput($ForegroundColor) {
    $fc = $host.UI.RawUI.ForegroundColor
    $host.UI.RawUI.ForegroundColor = $ForegroundColor
    if ($args) {
        Write-Output $args
    }
    $host.UI.RawUI.ForegroundColor = $fc
}

# Banner
Write-Host ""
Write-ColorOutput Cyan "╔══════════════════════════════════════════════════════════════════╗"
Write-ColorOutput Cyan "║                                                                  ║"
Write-ColorOutput Cyan "║          NETWORK SCANNER - Windows PowerShell Version            ║"
Write-ColorOutput Cyan "║                                                                  ║"
Write-ColorOutput Cyan "╚══════════════════════════════════════════════════════════════════╝"
Write-Host ""

# Variables
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$hostname = $env:COMPUTERNAME
$outputDir = "diagnostico_${hostname}_${timestamp}"
$zipFile = "${outputDir}.zip"

# Crear directorio de salida
Write-ColorOutput Green "[1/6] Creando directorio de salida..."
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

# Función para obtener información de red
function Get-NetworkInfo {
    Write-ColorOutput Green "[2/6] Obteniendo información de red..."

    # Obtener interfaz activa
    $activeInterface = Get-NetIPConfiguration | Where-Object {
        $_.IPv4DefaultGateway -ne $null -and $_.NetAdapter.Status -eq "Up"
    } | Select-Object -First 1

    if (-not $activeInterface) {
        Write-ColorOutput Red "Error: No se encontró interfaz de red activa"
        exit 1
    }

    $gateway = $activeInterface.IPv4DefaultGateway.NextHop
    $myIP = $activeInterface.IPv4Address.IPAddress
    $subnet = $activeInterface.IPv4Address.PrefixLength

    $networkInfo = @{
        gateway = $gateway
        myIP = $myIP
        subnet = $subnet
        interface = $activeInterface.InterfaceAlias
        rango = "$myIP/$subnet"
    }

    Write-Host "   Gateway: $gateway"
    Write-Host "   Mi IP: $myIP"
    Write-Host "   Subnet: /$subnet"

    return $networkInfo
}

# Función para escanear dispositivos con ARP
function Get-NetworkDevices {
    param($networkInfo)

    Write-ColorOutput Green "[3/6] Escaneando dispositivos en la red..."
    Write-Host "   Esto puede tardar 2-5 minutos..."

    $devices = @()

    # Método 1: ARP table
    $arpOutput = arp -a | Select-String "dinámica|dynamic"
    $arpFile = Join-Path $outputDir "arp_scan.txt"
    arp -a | Out-File -FilePath $arpFile

    # Método 2: Ping sweep + ARP
    $ipParts = $networkInfo.myIP -split '\.'
    $networkBase = "$($ipParts[0]).$($ipParts[1]).$($ipParts[2])"

    Write-Host "   Escaneando rango: $networkBase.1-254"

    # Ping rápido a toda la red (paralelo)
    1..254 | ForEach-Object -Parallel {
        $ip = "$using:networkBase.$_"
        $ping = Test-Connection -ComputerName $ip -Count 1 -Quiet -TimeoutSeconds 1
        if ($ping) {
            [PSCustomObject]@{
                IP = $ip
                Status = "Alive"
            }
        }
    } -ThrottleLimit 50 | ForEach-Object {
        $devices += $_.IP
    }

    Write-Host "   ✓ Dispositivos encontrados: $($devices.Count)"

    return $devices
}

# Función para obtener detalles de dispositivos
function Get-DeviceDetails {
    param($devices, $networkInfo)

    Write-ColorOutput Green "[4/6] Obteniendo detalles de dispositivos..."

    $deviceList = @()
    $counter = 0

    foreach ($ip in $devices) {
        $counter++
        Write-Progress -Activity "Analizando dispositivos" -Status "$counter de $($devices.Count)" -PercentComplete (($counter / $devices.Count) * 100)

        # Obtener MAC del ARP
        $arpEntry = arp -a $ip | Select-String $ip
        $mac = "Unknown"
        if ($arpEntry) {
            $mac = ($arpEntry -split '\s+')[1]
        }

        # Intentar resolver hostname
        $hostname = "Unknown"
        try {
            $dnsResult = [System.Net.Dns]::GetHostEntry($ip)
            $hostname = $dnsResult.HostName
        } catch {}

        # Detectar vendor (primeros 3 octetos del MAC)
        $vendor = "Unknown"
        if ($mac -ne "Unknown") {
            $macPrefix = ($mac -replace '-',':').Substring(0,8).ToUpper()
            $vendor = Get-VendorFromMAC $macPrefix
        }

        # Intentar detectar puertos abiertos (solo puertos comunes)
        $openPorts = @()
        $commonPorts = @(80, 443, 22, 23, 21, 25, 3389, 445, 139, 161)

        foreach ($port in $commonPorts) {
            try {
                $tcpClient = New-Object System.Net.Sockets.TcpClient
                $connect = $tcpClient.BeginConnect($ip, $port, $null, $null)
                $wait = $connect.AsyncWaitHandle.WaitOne(100, $false)
                if ($wait -and $tcpClient.Connected) {
                    $openPorts += $port
                }
                $tcpClient.Close()
            } catch {}
        }

        # Inferir tipo de dispositivo
        $tipo = Get-DeviceType -openPorts $openPorts -vendor $vendor -ip $ip -gateway $networkInfo.gateway

        $device = [PSCustomObject]@{
            ip = $ip
            mac = $mac
            hostname = $hostname
            vendor = $vendor
            tipo = $tipo
            velocidad = "1 Gbps"  # Estimado para dispositivos cableados
            puertos_abiertos = $openPorts
            trafico_total = "N/A"
        }

        $deviceList += $device
    }

    Write-Progress -Activity "Analizando dispositivos" -Completed
    Write-Host "   ✓ Análisis completado"

    return $deviceList
}

# Función para detectar vendor por MAC
function Get-VendorFromMAC {
    param($macPrefix)

    $vendors = @{
        "00:1A:A0" = "Cisco Systems"
        "00:1B:D5" = "Cisco Systems"
        "00:24:A5" = "Cisco Systems"
        "00:25:9C" = "Telmex"
        "00:1E:58" = "Telmex"
        "F4:CA:E5" = "Huawei"
        "00:E0:FC" = "Huawei"
        "48:F8:B3" = "ZTE"
        "50:BD:5F" = "ZTE"
        "00:1A:4A" = "Dell Inc."
        "00:50:56" = "VMware"
        "00:1C:0E" = "Hewlett Packard"
        "00:11:85" = "Hewlett Packard"
        "00:1B:63" = "Lenovo"
        "3C:07:54" = "Apple"
        "00:12:FB" = "Axis Communications"
        "BC:16:F5" = "Hikvision"
        "30:CD:A7" = "Canon"
        "00:26:B9" = "Synology"
    }

    if ($vendors.ContainsKey($macPrefix)) {
        return $vendors[$macPrefix]
    }

    return "Unknown"
}

# Función para inferir tipo de dispositivo
function Get-DeviceType {
    param($openPorts, $vendor, $ip, $gateway)

    # Gateway
    if ($ip -eq $gateway) {
        return "gateway"
    }

    # Por vendor
    if ($vendor -like "*Cisco*" -or $vendor -like "*HP*" -or $vendor -like "*Juniper*") {
        if ($openPorts -contains 161) {
            return "switch"
        }
        return "router"
    }

    if ($vendor -like "*Telmex*" -or $vendor -like "*Huawei*" -or $vendor -like "*ZTE*") {
        return "modem"
    }

    if ($vendor -like "*Axis*" -or $vendor -like "*Hikvision*") {
        return "camera"
    }

    if ($vendor -like "*Canon*" -or $vendor -like "*Epson*" -or $vendor -like "*HP*") {
        if ($openPorts -contains 9100 -or $openPorts -contains 515) {
            return "printer"
        }
    }

    # Por puertos
    if ($openPorts -contains 3389) {
        return "workstation"
    }

    if ($openPorts -contains 445 -or $openPorts -contains 139) {
        return "workstation"
    }

    if (($openPorts -contains 80 -or $openPorts -contains 443) -and ($openPorts -contains 22 -or $openPorts -contains 3306)) {
        return "server"
    }

    return "workstation"
}

# Función para test de velocidad
function Get-InternetSpeed {
    Write-ColorOutput Green "[5/6] Midiendo velocidad de internet..."

    try {
        # Usar Fast.com API o Speedtest
        $speedInfo = @{
            download = "N/A"
            upload = "N/A"
            ping = "N/A"
        }

        # Intentar ping a Google DNS
        $pingResult = Test-Connection -ComputerName 8.8.8.8 -Count 4
        if ($pingResult) {
            $avgPing = ($pingResult | Measure-Object -Property ResponseTime -Average).Average
            $speedInfo.ping = "$([Math]::Round($avgPing)) ms"
        }

        Write-Host "   Ping: $($speedInfo.ping)"
        Write-Host "   ⚠️  Para velocidad completa, usa speedtest.net manualmente"

        $speedInfo | ConvertTo-Json | Out-File -FilePath (Join-Path $outputDir "speedtest.txt")

        return $speedInfo

    } catch {
        Write-ColorOutput Yellow "   ⚠️  No se pudo medir velocidad automáticamente"
        return @{ download = "N/A"; upload = "N/A"; ping = "N/A" }
    }
}

# Main execution
try {
    $networkInfo = Get-NetworkInfo
    $devices = Get-NetworkDevices -networkInfo $networkInfo
    $deviceDetails = Get-DeviceDetails -devices $devices -networkInfo $networkInfo
    $speedInfo = Get-InternetSpeed

    Write-ColorOutput Green "[6/6] Generando archivos de salida..."

    # Crear metadata.json
    $metadata = @{
        timestamp = (Get-Date -Format "yyyy-MM-ddTHH:mm:ss")
        velocidad_internet = $speedInfo
        red = @{
            gateway = $networkInfo.gateway
            rango = $networkInfo.rango
            mascara = "255.255.255.0"
        }
        dispositivos = @($deviceDetails)
        conexiones = @()
    }

    # Generar conexiones (todos conectados al gateway)
    foreach ($device in $deviceDetails) {
        if ($device.ip -ne $networkInfo.gateway) {
            $metadata.conexiones += @{
                desde = $networkInfo.gateway
                hasta = $device.ip
            }
        }
    }

    $metadataFile = Join-Path $outputDir "metadata_simple.json"
    $metadata | ConvertTo-Json -Depth 10 | Out-File -FilePath $metadataFile -Encoding UTF8

    # Detectar módems y crear areas_config_auto.json
    $modems = $deviceDetails | Where-Object { $_.tipo -eq "modem" }

    if ($modems.Count -gt 0) {
        $areasConfig = @{}
        $modemCounter = 1

        foreach ($modem in $modems) {
            $areasConfig[$modem.ip] = @{
                area = "Enlace Internet #$modemCounter"
                modem_info = "Módem $($modem.vendor) #$modemCounter"
                modem_sla = "100 Mbps contratados"
                contacto = "Administrador TI"
                notas = "Detectado automáticamente - Verificar SLA real"
            }
            $modemCounter++
        }

        $areasConfigFile = Join-Path $outputDir "areas_config_auto.json"
        $areasConfig | ConvertTo-Json -Depth 10 | Out-File -FilePath $areasConfigFile -Encoding UTF8

        Write-Host "   ✓ Módems detectados: $($modems.Count)"
    }

    # Crear resumen
    $summary = @"
═══════════════════════════════════════════════════════════════════════════
 RESUMEN DEL ESCANEO
═══════════════════════════════════════════════════════════════════════════

Fecha: $(Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Red: $($networkInfo.rango)
Gateway: $($networkInfo.gateway)

DISPOSITIVOS ENCONTRADOS: $($deviceDetails.Count)

Por Tipo:
$( ($deviceDetails | Group-Object tipo | ForEach-Object { "  - $($_.Name): $($_.Count)" }) -join "`n" )

Módems Detectados: $($modems.Count)
$( if ($modems.Count -gt 0) { ($modems | ForEach-Object { "  - $($_.ip) ($($_.vendor))" }) -join "`n" } else { "  (ninguno)" } )

═══════════════════════════════════════════════════════════════════════════
"@

    $summary | Out-File -FilePath (Join-Path $outputDir "RESUMEN.txt")
    Write-Host ""
    Write-ColorOutput Cyan $summary

    # Crear ZIP
    Write-ColorOutput Green "Creando archivo ZIP..."
    Compress-Archive -Path $outputDir -DestinationPath $zipFile -Force

    Write-Host ""
    Write-ColorOutput Green "═══════════════════════════════════════════════════════════════════════════"
    Write-ColorOutput Green "✅ ESCANEO COMPLETADO EXITOSAMENTE"
    Write-ColorOutput Green "═══════════════════════════════════════════════════════════════════════════"
    Write-Host ""
    Write-Host "Archivo generado: " -NoNewline
    Write-ColorOutput Cyan $zipFile
    Write-Host ""
    Write-Host "Tamaño: " -NoNewline
    Write-ColorOutput Cyan "$([Math]::Round((Get-Item $zipFile).Length / 1KB, 2)) KB"
    Write-Host ""
    Write-ColorOutput Yellow "📧 ENVÍA ESTE ARCHIVO A TU PROVEEDOR DE ANÁLISIS"
    Write-Host ""
    Write-ColorOutput Green "═══════════════════════════════════════════════════════════════════════════"
    Write-Host ""

    # Abrir carpeta
    Start-Process explorer.exe -ArgumentList "/select,`"$((Get-Item $zipFile).FullName)`""

} catch {
    Write-ColorOutput Red "❌ Error durante el escaneo: $($_.Exception.Message)"
    Write-ColorOutput Red $_.ScriptStackTrace
    exit 1
}
