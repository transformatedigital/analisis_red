#!/bin/bash
#═══════════════════════════════════════════════════════════════════════════
#  NETWORK SCANNER CLIENT V2 - CON DETECCIÓN AUTOMÁTICA DE MÓDEMS
#═══════════════════════════════════════════════════════════════════════════
#
#  MEJORAS:
#  ✅ Detecta módems automáticamente por vendor
#  ✅ Intenta obtener velocidades vía SNMP
#  ✅ Hace speedtest por interfaz (si es posible)
#  ✅ Genera areas_config.json automáticamente
#  ✅ Identifica módems críticos por tráfico
#
#═══════════════════════════════════════════════════════════════════════════

set -e

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Banner
echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║     NETWORK SCANNER V2 - Detección Automática de Módems         ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}❌ ERROR: Este script debe ejecutarse como root${NC}"
    echo -e "${YELLOW}   Ejecuta: sudo bash $0${NC}"
    exit 1
fi

# Información del cliente
echo -e "${BLUE}📋 Información del Cliente${NC}"
read -p "   Nombre de la empresa: " EMPRESA_NOMBRE
EMPRESA_NOMBRE=${EMPRESA_NOMBRE:-"Cliente"}

# Crear carpeta
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
OUTPUT_DIR="diagnostico_${EMPRESA_NOMBRE// /_}_$TIMESTAMP"
mkdir -p "$OUTPUT_DIR"

log() {
    echo -e "${GREEN}[$(date +'%H:%M:%S')]${NC} $1"
}

# ═══════════════════════════════════════════════════════════════════════
#  VERIFICAR DEPENDENCIAS + INSTALAR SI FALTA
# ═══════════════════════════════════════════════════════════════════════
log "🔍 Verificando dependencias..."

install_if_missing() {
    if ! command -v $1 &> /dev/null; then
        echo "   📦 Instalando $1..."
        apt-get update -qq > /dev/null 2>&1
        apt-get install -y $2 > /dev/null 2>&1
        echo "   ✅ $1 instalado"
    else
        echo "   ✅ $1"
    fi
}

install_if_missing "nmap" "nmap"
install_if_missing "arp-scan" "arp-scan"
install_if_missing "speedtest-cli" "speedtest-cli"
install_if_missing "snmpwalk" "snmp"
install_if_missing "python3" "python3"
install_if_missing "jq" "jq"

# ═══════════════════════════════════════════════════════════════════════
#  DETECTAR RED LOCAL
# ═══════════════════════════════════════════════════════════════════════
log "🌐 Detectando red local..."

INTERFACE=$(ip route | grep default | awk '{print $5}' | head -1)
IP_LOCAL=$(ip -4 addr show $INTERFACE | grep -oP '(?<=inet\s)\d+(\.\d+){3}')
GATEWAY=$(ip route | grep default | awk '{print $3}' | head -1)
NETWORK_PREFIX=$(echo $IP_LOCAL | cut -d. -f1-3)
NETWORK_RANGE="${NETWORK_PREFIX}.0/24"

echo "   ✅ Interfaz: $INTERFACE"
echo "   ✅ IP local: $IP_LOCAL"
echo "   ✅ Gateway: $GATEWAY"
echo "   ✅ Rango: $NETWORK_RANGE"

# ═══════════════════════════════════════════════════════════════════════
#  ESCANEO BÁSICO
# ═══════════════════════════════════════════════════════════════════════
log "🔍 Escaneando red..."

# ARP Scan
arp-scan -l -I $INTERFACE > "$OUTPUT_DIR/arp_scan.txt" 2>&1 || true

# Nmap básico
nmap -sn -oN "$OUTPUT_DIR/nmap_ping.txt" $NETWORK_RANGE &> /dev/null

# ═══════════════════════════════════════════════════════════════════════
#  DETECCIÓN INTELIGENTE DE MÓDEMS
# ═══════════════════════════════════════════════════════════════════════
log "🎯 Detectando módems automáticamente..."

# Vendors comunes de módems en México/Latinoamérica
MODEM_VENDORS=(
    "Cisco"
    "Huawei"
    "ZTE"
    "Technicolor"
    "Arris"
    "Motorola"
    "Ubee"
    "Thomson"
    "Netgear"
    "D-Link"
    "TP-Link"
    "Sagemcom"
)

# Buscar dispositivos que parezcan módems
declare -A MODEMS_DETECTADOS

while IFS= read -r line; do
    # Parsear línea: IP MAC VENDOR
    if [[ $line =~ ^([0-9.]+)[[:space:]]+([0-9a-fA-F:]+)[[:space:]]+(.+)$ ]]; then
        IP="${BASH_REMATCH[1]}"
        MAC="${BASH_REMATCH[2]}"
        VENDOR="${BASH_REMATCH[3]}"

        # Verificar si es un vendor de módem conocido
        for modem_vendor in "${MODEM_VENDORS[@]}"; do
            if [[ "$VENDOR" == *"$modem_vendor"* ]]; then
                MODEMS_DETECTADOS[$IP]="$VENDOR"
                echo "   📡 Módem detectado: $IP - $VENDOR"
                break
            fi
        done

        # También detectar si es el gateway (suele ser módem)
        if [[ "$IP" == "$GATEWAY" ]]; then
            MODEMS_DETECTADOS[$IP]="$VENDOR (Gateway)"
            echo "   🚪 Gateway/Módem: $IP - $VENDOR"
        fi
    fi
done < "$OUTPUT_DIR/arp_scan.txt"

NUM_MODEMS=${#MODEMS_DETECTADOS[@]}
echo ""
echo "   ✅ Total módems detectados: $NUM_MODEMS"

# ═══════════════════════════════════════════════════════════════════════
#  PRUEBAS AVANZADAS EN MÓDEMS DETECTADOS
# ═══════════════════════════════════════════════════════════════════════
if [ $NUM_MODEMS -gt 0 ]; then
    log "🔬 Analizando módems en detalle..."

    mkdir -p "$OUTPUT_DIR/modems_detail"

    MODEM_NUM=1
    for MODEM_IP in "${!MODEMS_DETECTADOS[@]}"; do
        MODEM_VENDOR="${MODEMS_DETECTADOS[$MODEM_IP]}"

        echo ""
        echo "   📡 Módem #$MODEM_NUM: $MODEM_IP ($MODEM_VENDOR)"

        # 1. Ping avanzado (RTT, packet loss)
        echo "      → Midiendo latencia..."
        PING_RESULT=$(ping -c 10 -i 0.2 $MODEM_IP 2>&1 | tail -2)
        echo "$PING_RESULT" > "$OUTPUT_DIR/modems_detail/modem_${MODEM_NUM}_ping.txt"

        # 2. Intentar SNMP (community strings comunes)
        echo "      → Intentando SNMP..."
        SNMP_SUCCESS=0
        for COMMUNITY in "public" "private" "telmex" "admin"; do
            SNMP_OUTPUT=$(snmpwalk -v2c -c $COMMUNITY -t 2 $MODEM_IP system 2>&1)
            if [[ ! "$SNMP_OUTPUT" == *"Timeout"* ]] && [[ ! "$SNMP_OUTPUT" == *"No Such"* ]]; then
                echo "$SNMP_OUTPUT" > "$OUTPUT_DIR/modems_detail/modem_${MODEM_NUM}_snmp.txt"
                echo "      ✅ SNMP accesible (community: $COMMUNITY)"
                SNMP_SUCCESS=1

                # Intentar obtener velocidad de interfaz
                IF_SPEED=$(snmpwalk -v2c -c $COMMUNITY -t 2 $MODEM_IP ifSpeed 2>&1 | grep -oP '\d+' | head -1)
                if [ ! -z "$IF_SPEED" ]; then
                    IF_SPEED_MBPS=$((IF_SPEED / 1000000))
                    echo "      📊 Velocidad interfaz: ${IF_SPEED_MBPS} Mbps"
                    echo "$IF_SPEED_MBPS" > "$OUTPUT_DIR/modems_detail/modem_${MODEM_NUM}_speed.txt"
                fi
                break
            fi
        done

        if [ $SNMP_SUCCESS -eq 0 ]; then
            echo "      ⚠️  SNMP no accesible (normal en muchos módems)"
        fi

        # 3. Escaneo de puertos comunes en módems
        echo "      → Escaneando puertos de administración..."
        nmap -p 80,443,8080,8443,23,22 -T4 --open $MODEM_IP -oN "$OUTPUT_DIR/modems_detail/modem_${MODEM_NUM}_ports.txt" &> /dev/null

        OPEN_PORTS=$(grep "open" "$OUTPUT_DIR/modems_detail/modem_${MODEM_NUM}_ports.txt" | wc -l)
        if [ $OPEN_PORTS -gt 0 ]; then
            echo "      🔓 $OPEN_PORTS puertos abiertos (admin web posible)"
        fi

        # 4. Análisis de tráfico (prioridad por volumen)
        echo "      → Analizando tráfico..."
        # Capturar 30 segundos de tráfico
        timeout 5 tcpdump -i $INTERFACE host $MODEM_IP -c 100 -w "$OUTPUT_DIR/modems_detail/modem_${MODEM_NUM}_traffic.pcap" 2>&1 > /dev/null || true

        PACKET_COUNT=$(tcpdump -r "$OUTPUT_DIR/modems_detail/modem_${MODEM_NUM}_traffic.pcap" 2>/dev/null | wc -l || echo "0")
        if [ $PACKET_COUNT -gt 50 ]; then
            echo "      ⚡ ALTA actividad ($PACKET_COUNT paquetes en 5s) - Posible CRÍTICO"
            echo "CRITICAL" > "$OUTPUT_DIR/modems_detail/modem_${MODEM_NUM}_priority.txt"
        elif [ $PACKET_COUNT -gt 10 ]; then
            echo "      📊 Actividad media ($PACKET_COUNT paquetes)"
            echo "NORMAL" > "$OUTPUT_DIR/modems_detail/modem_${MODEM_NUM}_priority.txt"
        else
            echo "      💤 Baja actividad ($PACKET_COUNT paquetes)"
            echo "LOW" > "$OUTPUT_DIR/modems_detail/modem_${MODEM_NUM}_priority.txt"
        fi

        MODEM_NUM=$((MODEM_NUM + 1))
    done
fi

# ═══════════════════════════════════════════════════════════════════════
#  SPEEDTEST GENERAL
# ═══════════════════════════════════════════════════════════════════════
log "⚡ Midiendo velocidad de internet..."
speedtest-cli --simple > "$OUTPUT_DIR/speedtest.txt" 2>&1 || echo "No disponible" > "$OUTPUT_DIR/speedtest.txt"

# ═══════════════════════════════════════════════════════════════════════
#  GENERAR METADATA JSON CON INFO DE MÓDEMS
# ═══════════════════════════════════════════════════════════════════════
log "📊 Generando metadata con info de módems..."

python3 - <<PYEOF
import json
import re
import os
from datetime import datetime

# Parsear dispositivos
dispositivos = []
modems_info = {}

# Leer arp-scan
try:
    with open('$OUTPUT_DIR/arp_scan.txt', 'r') as f:
        for line in f:
            match = re.match(r'(\d+\.\d+\.\d+\.\d+)\s+([\w:]+)\s+(.*)', line)
            if match:
                ip = match.group(1)
                mac = match.group(2)
                vendor = match.group(3).strip()

                dispositivo = {
                    'ip': ip,
                    'mac': mac,
                    'vendor': vendor,
                    'hostname': '',
                    'latencia': '0',
                    'estado': 'up',
                    'es_modem': False,
                    'modem_info': {}
                }

                # Verificar si es módem detectado
                if os.path.exists(f'$OUTPUT_DIR/modems_detail'):
                    for i in range(1, 20):
                        ping_file = f'$OUTPUT_DIR/modems_detail/modem_{i}_ping.txt'
                        if os.path.exists(ping_file):
                            # Buscar IP en archivo de ping
                            with open(ping_file, 'r') as pf:
                                if ip in pf.read():
                                    dispositivo['es_modem'] = True

                                    # Leer info adicional del módem
                                    speed_file = f'$OUTPUT_DIR/modems_detail/modem_{i}_speed.txt'
                                    priority_file = f'$OUTPUT_DIR/modems_detail/modem_{i}_priority.txt'

                                    if os.path.exists(speed_file):
                                        with open(speed_file, 'r') as sf:
                                            speed = sf.read().strip()
                                            dispositivo['modem_info']['velocidad_interfaz'] = f"{speed} Mbps"

                                    if os.path.exists(priority_file):
                                        with open(priority_file, 'r') as prf:
                                            priority = prf.read().strip()
                                            dispositivo['modem_info']['prioridad'] = priority

                                    dispositivo['modem_info']['numero'] = i
                                    break

                dispositivos.append(dispositivo)
except:
    pass

# Parsear speedtest
velocidad = {'download': 'N/A', 'upload': 'N/A', 'ping_ms': 'N/A'}
try:
    with open('$OUTPUT_DIR/speedtest.txt', 'r') as f:
        content = f.read()
        download = re.search(r'Download:\s+([\d.]+)', content)
        upload = re.search(r'Upload:\s+([\d.]+)', content)
        ping = re.search(r'Ping:\s+([\d.]+)', content)
        if download:
            velocidad['download'] = f"{download.group(1)} Mbps"
        if upload:
            velocidad['upload'] = f"{upload.group(1)} Mbps"
        if ping:
            velocidad['ping_ms'] = f"{ping.group(1)} ms"
except:
    pass

# Crear metadata
metadata = {
    'timestamp': datetime.now().isoformat(),
    'empresa': '$EMPRESA_NOMBRE',
    'red': {
        'rango': '$NETWORK_RANGE',
        'gateway': '$GATEWAY',
        'interfaz': '$INTERFACE'
    },
    'velocidad_internet': velocidad,
    'total_dispositivos': len(dispositivos),
    'total_modems_detectados': sum(1 for d in dispositivos if d['es_modem']),
    'dispositivos': dispositivos
}

# Guardar metadata
with open('$OUTPUT_DIR/metadata_simple.json', 'w') as f:
    json.dump(metadata, f, indent=2)

# GENERAR AREAS_CONFIG.JSON AUTOMÁTICAMENTE
areas_config = {
    "_README": "Configuración generada automáticamente - Revisar y ajustar",
    "_GENERADO": datetime.now().isoformat(),
    "_EMPRESA": "$EMPRESA_NOMBRE"
}

modem_num = 1
for d in dispositivos:
    if d['es_modem']:
        modem_info = d.get('modem_info', {})
        priority = modem_info.get('prioridad', 'NORMAL')

        areas_config[d['ip']] = {
            "area": f"Area {modem_num} - Por definir",
            "piso": "Por confirmar",
            "ubicacion_exacta": "Por confirmar",
            "modem_info": f"Módem #{modem_num} - {d['vendor']}",
            "modem_sla": modem_info.get('velocidad_interfaz', 'Por confirmar'),
            "modem_numero_contrato": f"Por definir",
            "contacto": "Por definir",
            "telefono_soporte": "Por definir",
            "notas": f"Prioridad: {priority}" + (" - CRÍTICO" if priority == "CRITICAL" else ""),
            "fecha_deteccion": datetime.now().isoformat(),
            "mac_address": d['mac'],
            "vendor": d['vendor']
        }
        modem_num += 1

# Guardar areas_config
with open('$OUTPUT_DIR/areas_config_auto.json', 'w') as f:
    json.dump(areas_config, f, indent=2, ensure_ascii=False)

print(f"✅ {len(dispositivos)} dispositivos encontrados")
print(f"✅ {sum(1 for d in dispositivos if d['es_modem'])} módems detectados")
print(f"✅ areas_config_auto.json generado")
PYEOF

# ═══════════════════════════════════════════════════════════════════════
#  INFORMACIÓN DEL SISTEMA
# ═══════════════════════════════════════════════════════════════════════
log "💻 Recopilando información del sistema..."

{
    echo "=== INFORMACIÓN DEL SISTEMA ==="
    echo "Timestamp: $(date)"
    echo "Empresa: $EMPRESA_NOMBRE"
    echo "Hostname: $(hostname)"
    echo "Kernel: $(uname -r)"
    echo ""
    echo "=== MÓDEMS DETECTADOS ==="
    for ip in "${!MODEMS_DETECTADOS[@]}"; do
        echo "  • $ip - ${MODEMS_DETECTADOS[$ip]}"
    done
    echo ""
    echo "=== INTERFACES DE RED ==="
    ip addr
} > "$OUTPUT_DIR/system_info.txt"

# ═══════════════════════════════════════════════════════════════════════
#  README
# ═══════════════════════════════════════════════════════════════════════
cat > "$OUTPUT_DIR/README.txt" <<EOF
═══════════════════════════════════════════════════════════════════════
  DIAGNÓSTICO DE RED - $EMPRESA_NOMBRE
═══════════════════════════════════════════════════════════════════════

Fecha: $(date)
Red: $NETWORK_RANGE
Módems detectados: $NUM_MODEMS

ARCHIVOS INCLUIDOS:
-------------------
- metadata_simple.json          Datos estructurados
- areas_config_auto.json        ⭐ Configuración AUTO de módems
- modems_detail/                Análisis detallado de cada módem
- nmap_*.txt                    Escaneos de red
- arp_scan.txt                  Tabla ARP
- speedtest.txt                 Velocidad de internet
- system_info.txt               Info del sistema

CARACTERÍSTICAS V2:
-------------------
✅ Detección automática de módems por vendor
✅ Análisis SNMP si está disponible
✅ Medición de latencia por módem
✅ Detección de criticidad por tráfico
✅ Escaneo de puertos de administración
✅ Generación automática de areas_config.json

SIGUIENTE PASO:
---------------
1. Revisar areas_config_auto.json
2. Ajustar ubicaciones y contactos
3. Copiar como areas_config.json
4. Procesar con enriquecedor
5. Generar dashboard

EOF

# ═══════════════════════════════════════════════════════════════════════
#  COMPRIMIR
# ═══════════════════════════════════════════════════════════════════════
log "📦 Comprimiendo diagnóstico..."

ZIP_NAME="diagnostico_${EMPRESA_NOMBRE// /_}_$TIMESTAMP.zip"
zip -r "$ZIP_NAME" "$OUTPUT_DIR" > /dev/null
rm -rf "$OUTPUT_DIR"

# ═══════════════════════════════════════════════════════════════════════
#  RESULTADO
# ═══════════════════════════════════════════════════════════════════════
echo ""
echo -e "${GREEN}╔══════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                                                                  ║${NC}"
echo -e "${GREEN}║            ✅  DIAGNÓSTICO COMPLETADO (V2 AUTO)                  ║${NC}"
echo -e "${GREEN}║                                                                  ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${BLUE}📦 Archivo generado:${NC} $(pwd)/$ZIP_NAME"
echo -e "${BLUE}📊 Tamaño:${NC} $(du -h $ZIP_NAME | cut -f1)"
echo ""
echo -e "${YELLOW}🎯 MÓDEMS DETECTADOS AUTOMÁTICAMENTE:${NC}"
if [ $NUM_MODEMS -gt 0 ]; then
    for ip in "${!MODEMS_DETECTADOS[@]}"; do
        echo -e "   📡 $ip - ${MODEMS_DETECTADOS[$ip]}"
    done
    echo ""
    echo -e "${GREEN}✅ areas_config_auto.json generado dentro del ZIP${NC}"
    echo -e "   → Descomprimir y revisar este archivo"
    echo -e "   → Ajustar ubicaciones físicas y contactos"
    echo -e "   → Copiar como areas_config.json"
else
    echo -e "   ${YELLOW}⚠️  No se detectaron módems automáticamente${NC}"
    echo -e "   Esto puede significar:"
    echo -e "   • Los módems usan vendors no reconocidos"
    echo -e "   • Están en otra subred"
    echo -e "   • Revisar manualmente arp_scan.txt en el ZIP"
fi
echo ""
echo -e "${BLUE}📧 SIGUIENTE PASO:${NC}"
echo -e "   1. Descomprimir: unzip $ZIP_NAME"
echo -e "   2. Revisar: cat diagnostico_*/areas_config_auto.json"
echo -e "   3. Ajustar ubicaciones manualmente"
echo -e "   4. Procesar con enriquecedor + visualizador"
echo ""
