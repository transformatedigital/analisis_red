#!/usr/bin/env python3
"""
Vendor Lookup Avanzado - Identifica fabricantes por MAC address usando múltiples fuentes
"""

import re
import os
import json
import urllib.request
import urllib.error
from pathlib import Path

# Base de datos OUI local (subset común de fabricantes)
OUI_DATABASE = {
    # Networking
    "00:1A:A0": "Dell Inc.",
    "00:23:AE": "Cisco Systems",
    "00:1B:D5": "Hewlett Packard",
    "00:50:56": "VMware",
    "00:0C:29": "VMware",
    "00:05:9A": "Cisco-Linksys",
    "00:14:BF": "Cisco-Linksys",
    "00:18:39": "Cisco-Linksys",
    "00:1C:10": "Cisco-Linksys",
    "00:21:29": "Cisco-Linksys",
    "00:22:6B": "Cisco-Linksys",
    "00:25:9C": "Cisco-Linksys",

    # Juniper
    "00:05:85": "Juniper Networks",
    "00:10:DB": "Juniper Networks",
    "00:12:1E": "Juniper Networks",
    "00:17:CB": "Juniper Networks",
    "00:19:E2": "Juniper Networks",
    "00:1F:12": "Juniper Networks",
    "00:21:59": "Juniper Networks",
    "00:22:83": "Juniper Networks",
    "00:23:9C": "Juniper Networks",
    "00:26:88": "Juniper Networks",
    "2C:6B:F5": "Juniper Networks",
    "3C:61:04": "Juniper Networks",
    "50:C5:8D": "Juniper Networks",
    "84:B5:9C": "Juniper Networks",
    "84:18:88": "Juniper Networks",

    # Fortinet
    "00:09:0F": "Fortinet",
    "08:5B:0E": "Fortinet",
    "90:6C:AC": "Fortinet",

    # HP/HPE
    "00:08:02": "Hewlett Packard",
    "00:0D:9D": "Hewlett Packard",
    "00:10:E3": "Hewlett Packard",
    "00:11:0A": "Hewlett Packard",
    "00:14:C2": "Hewlett Packard",
    "00:15:60": "Hewlett Packard",
    "00:17:A4": "Hewlett Packard",
    "00:1B:78": "Hewlett Packard",
    "00:1E:0B": "Hewlett Packard",
    "00:21:5A": "Hewlett Packard",
    "00:23:7D": "Hewlett Packard",
    "00:24:81": "Hewlett Packard",
    "00:25:B3": "Hewlett Packard",
    "00:26:55": "Hewlett Packard",
    "18:A9:05": "Hewlett Packard Enterprise",
    "48:0F:CF": "Hewlett Packard Enterprise",
    "70:10:6F": "Hewlett Packard Enterprise",

    # Synology
    "00:11:32": "Synology",

    # Apple
    "00:03:93": "Apple",
    "00:0A:27": "Apple",
    "00:0A:95": "Apple",
    "00:0D:93": "Apple",
    "00:11:24": "Apple",
    "00:14:51": "Apple",
    "00:16:CB": "Apple",
    "00:17:F2": "Apple",
    "00:19:E3": "Apple",
    "00:1B:63": "Apple",
    "00:1C:B3": "Apple",
    "00:1D:4F": "Apple",
    "00:1E:52": "Apple",
    "00:1F:5B": "Apple",
    "00:1F:F3": "Apple",
    "00:21:E9": "Apple",
    "00:22:41": "Apple",
    "00:23:12": "Apple",
    "00:23:32": "Apple",
    "00:23:6C": "Apple",
    "00:23:DF": "Apple",
    "00:24:36": "Apple",
    "00:25:00": "Apple",
    "00:25:4B": "Apple",
    "00:25:BC": "Apple",
    "00:26:08": "Apple",
    "00:26:4A": "Apple",
    "00:26:B0": "Apple",
    "00:26:BB": "Apple",

    # ASUS
    "00:11:2F": "ASUS",
    "00:13:D4": "ASUS",
    "00:15:F2": "ASUS",
    "00:17:31": "ASUS",
    "00:18:F3": "ASUS",
    "00:1A:92": "ASUS",
    "00:1B:FC": "ASUS",
    "00:1D:60": "ASUS",
    "00:1E:8C": "ASUS",
    "00:22:15": "ASUS",
    "00:23:54": "ASUS",
    "00:24:8C": "ASUS",
    "00:25:D3": "ASUS",
    "00:26:18": "ASUS",
    "08:60:6E": "ASUS",
    "10:BF:48": "ASUS",
    "14:DD:A9": "ASUS",
    "1C:87:2C": "ASUS",
    "2C:56:DC": "ASUS",
    "30:5A:3A": "ASUS",
    "38:D5:47": "ASUS",
    "50:46:5D": "ASUS",
    "54:04:A6": "ASUS",
    "60:45:CB": "ASUS",

    # Gigabyte
    "00:1B:FC": "Gigabyte",
    "00:24:1D": "Gigabyte",
    "E0:69:95": "Gigabyte",

    # TP-Link
    "00:27:19": "TP-Link",
    "14:CF:92": "TP-Link",
    "50:C7:BF": "TP-Link",
    "54:E6:FC": "TP-Link",
    "60:E3:27": "TP-Link",
    "74:DA:88": "TP-Link",
    "98:DE:D0": "TP-Link",
    "A0:F3:C1": "TP-Link",
    "B0:4E:26": "TP-Link",
    "C0:25:E9": "TP-Link",
    "EC:08:6B": "TP-Link",
    "F4:EC:38": "TP-Link",

    # D-Link
    "00:05:5D": "D-Link",
    "00:0D:88": "D-Link",
    "00:11:95": "D-Link",
    "00:13:46": "D-Link",
    "00:15:E9": "D-Link",
    "00:17:9A": "D-Link",
    "00:19:5B": "D-Link",
    "00:1B:11": "D-Link",
    "00:1C:F0": "D-Link",
    "00:1E:58": "D-Link",
    "00:21:91": "D-Link",
    "00:22:B0": "D-Link",
    "00:24:01": "D-Link",
    "00:26:5A": "D-Link",

    # Netgear
    "00:09:5B": "Netgear",
    "00:0F:B5": "Netgear",
    "00:14:6C": "Netgear",
    "00:18:4D": "Netgear",
    "00:1B:2F": "Netgear",
    "00:1E:2A": "Netgear",
    "00:22:3F": "Netgear",
    "00:24:B2": "Netgear",
    "00:26:F2": "Netgear",
    "20:E5:2A": "Netgear",
    "28:C6:8E": "Netgear",
    "30:46:9A": "Netgear",
    "A0:21:B7": "Netgear",
    "C0:3F:0E": "Netgear",
    "E0:46:9A": "Netgear",

    # Arista Networks
    "00:1C:73": "Arista Networks",
    "44:4C:A8": "Arista Networks",

    # Palo Alto Networks
    "00:1B:17": "Palo Alto Networks",
    "80:81:BC": "Palo Alto Networks",

    # Ubiquiti
    "00:15:6D": "Ubiquiti Networks",
    "00:27:22": "Ubiquiti Networks",
    "04:18:D6": "Ubiquiti Networks",
    "24:A4:3C": "Ubiquiti Networks",
    "68:D7:9A": "Ubiquiti Networks",
    "74:83:C2": "Ubiquiti Networks",
    "80:2A:A8": "Ubiquiti Networks",
    "B4:FB:E4": "Ubiquiti Networks",
    "DC:9F:DB": "Ubiquiti Networks",
    "F0:9F:C2": "Ubiquiti Networks",
    "FC:EC:DA": "Ubiquiti Networks",

    # Hikvision
    "00:12:12": "Hikvision",
    "28:57:BE": "Hikvision",
    "44:19:B6": "Hikvision",
    "BC:AD:28": "Hikvision",

    # Samsung
    "00:12:FB": "Samsung",
    "00:15:B9": "Samsung",
    "00:16:6C": "Samsung",
    "00:17:C9": "Samsung",
    "00:18:AF": "Samsung",
    "00:1A:8A": "Samsung",
    "00:1D:25": "Samsung",
    "00:1E:7D": "Samsung",
    "00:21:19": "Samsung",
    "00:21:4C": "Samsung",
    "00:23:39": "Samsung",
    "00:23:D6": "Samsung",
    "00:24:54": "Samsung",
    "00:24:90": "Samsung",
    "00:24:E9": "Samsung",
    "00:25:66": "Samsung",
    "00:26:37": "Samsung",
    "00:26:5D": "Samsung",
}

def normalize_mac(mac):
    """Normaliza formato de MAC address"""
    # Remover caracteres no-hex
    mac = re.sub(r'[^0-9A-Fa-f]', '', mac)

    # Convertir a formato XX:XX:XX
    if len(mac) >= 6:
        return ':'.join([mac[i:i+2].upper() for i in range(0, 6, 2)])

    return None

def lookup_local(mac):
    """Busca vendor en base de datos local"""
    oui = normalize_mac(mac)
    if not oui:
        return None

    # Buscar en base local
    return OUI_DATABASE.get(oui, None)

def lookup_online(mac):
    """Busca vendor en API online (macvendors.com)"""
    try:
        url = f"https://api.macvendors.com/{mac}"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})

        with urllib.request.urlopen(req, timeout=3) as response:
            vendor = response.read().decode('utf-8').strip()
            return vendor if vendor else None
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError):
        return None

def get_vendor(mac, current_vendor=""):
    """
    Obtiene el fabricante de una MAC address usando múltiples fuentes

    Args:
        mac: MAC address en cualquier formato
        current_vendor: Vendor actual del escaneo (fallback)

    Returns:
        Nombre del fabricante o "Unknown"
    """
    if not mac or mac == "N/A":
        return current_vendor or "Unknown"

    # 1. Intentar base de datos local (más rápido)
    vendor = lookup_local(mac)
    if vendor:
        return vendor

    # 2. Si current_vendor es bueno, usarlo
    if current_vendor and current_vendor not in ["Unknown", "", "N/A"]:
        # Limpiar vendor actual
        vendor_clean = current_vendor.strip()
        if len(vendor_clean) > 3:  # Evitar vendors muy cortos
            return vendor_clean

    # 3. Intentar lookup online (más lento, puede fallar)
    vendor = lookup_online(mac)
    if vendor:
        return vendor

    # 4. Fallback
    return current_vendor if current_vendor else "Unknown"

def enrich_devices_with_vendors(devices):
    """
    Enriquece lista de dispositivos con vendors mejorados

    Args:
        devices: Lista de dispositivos con campo 'mac' y 'vendor'

    Returns:
        Lista de dispositivos con vendors actualizados
    """
    for device in devices:
        mac = device.get('mac', '')
        current_vendor = device.get('vendor', '')

        improved_vendor = get_vendor(mac, current_vendor)
        device['vendor'] = improved_vendor

    return devices

if __name__ == "__main__":
    # Test
    test_macs = [
        ("00:1A:A0:12:34:56", "Dell Inc."),
        ("00:05:85:AA:BB:CC", "Juniper Networks"),
        ("00:11:32:11:22:33", "Synology"),
        ("FF:FF:FF:FF:FF:FF", "Unknown")
    ]

    print("🔍 Test de Vendor Lookup\n")
    for mac, expected in test_macs:
        result = get_vendor(mac)
        status = "✅" if expected in result else "❌"
        print(f"{status} {mac} → {result} (esperado: {expected})")
