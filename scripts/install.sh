#!/bin/bash
#═══════════════════════════════════════════════════════════════════════════
#  INSTALADOR ONE-LINER - Network Analyzer
#  Uso: curl -sL https://raw.githubusercontent.com/transformatedigital/analisis_red/main/scripts/install.sh | sudo bash
#═══════════════════════════════════════════════════════════════════════════

set -e

# Colores
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${BLUE}"
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║                                                                  ║"
echo "║           Network Analyzer - Instalador Automático              ║"
echo "║           https://github.com/transformatedigital/analisis_red   ║"
echo "║                                                                  ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Verificar root
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}⚠️  Este script debe ejecutarse como root${NC}"
    echo -e "${YELLOW}   Ejecuta: curl -sL ... | sudo bash${NC}"
    exit 1
fi

echo -e "${GREEN}[1/4]${NC} Descargando script principal..."
curl -sL https://raw.githubusercontent.com/transformatedigital/analisis_red/main/scripts/network_scan_client_v2_auto.sh -o /tmp/network_scan.sh

echo -e "${GREEN}[2/4]${NC} Verificando dependencias..."
apt-get update -qq > /dev/null 2>&1 || true

DEPS="nmap arp-scan snmp speedtest-cli python3 jq zip"
for dep in $DEPS; do
    if ! command -v $(echo $dep | cut -d'-' -f1) &> /dev/null; then
        echo "   📦 Instalando $dep..."
        apt-get install -y $dep > /dev/null 2>&1 || true
    fi
done

echo -e "${GREEN}[3/4]${NC} Configurando permisos..."
chmod +x /tmp/network_scan.sh

echo -e "${GREEN}[4/4]${NC} Ejecutando escaneo..."
echo ""
bash /tmp/network_scan.sh

echo ""
echo -e "${GREEN}✅ ¡Instalación y escaneo completados!${NC}"
echo ""
