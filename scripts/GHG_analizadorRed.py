#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════
 ESCANEO DE RED MULTI-VLAN  (solo librería estándar de Python)
 - No requiere nmap / arp-scan / pip install
 - Funciona en Windows (incl. Server) y Linux
 - Detecta hosts vivos por PING y por caché ARP (atrapa equipos que
   bloquean ICMP pero responden a nivel de enlace en la VLAN local)
 - Genera metadata_simple.json + areas_config_auto.json + ZIP
   100% compatible con enriquecer_metadata_kais.py / visualizador_triple_vista.py
═══════════════════════════════════════════════════════════════════════════
"""
import os, re, sys, json, socket, subprocess, zipfile, ipaddress, datetime
from concurrent.futures import ThreadPoolExecutor

# ─────────────────  CONFIG (editar si cambian las VLAN)  ─────────────────
EMPRESA          = "Grupo Hernandez Garza"
SUBNETS          = ["10.69.1.0/24", "10.69.2.0/24"]   # las dos VLAN
GATEWAY          = "10.69.1.250"                        # puerta de enlace principal
INTERFAZ         = "Ethernet0"                          # NIC real (informativo)
PING_TIMEOUT_MS  = 600
MAX_WORKERS      = 120
# ─────────────────────────────────────────────────────────────────────────

IS_WIN = os.name == "nt"


def ping(ip):
    """Devuelve (ip, latencia_ms) si responde, si no None."""
    if IS_WIN:
        cmd = ["ping", "-n", "1", "-w", str(PING_TIMEOUT_MS), ip]
    else:
        cmd = ["ping", "-c", "1", "-W", "1", ip]
    try:
        out = subprocess.run(cmd, capture_output=True, text=True,
                             encoding="utf-8", errors="ignore").stdout
    except Exception:
        return None
    if "TTL=" in out.upper():
        m = re.search(r'[<=]\s*([\d.]+)\s*ms', out)
        return (ip, m.group(1) if m else "0")
    return None


def get_arp_table():
    """IP -> MAC desde la caché ARP del sistema."""
    table = {}
    try:
        out = subprocess.run(["arp", "-a"], capture_output=True, text=True,
                             encoding="utf-8", errors="ignore").stdout
    except Exception:
        return table
    for line in out.splitlines():
        m = re.search(r'(\d+\.\d+\.\d+\.\d+)\s+([0-9a-fA-F]{2}(?:[-:][0-9a-fA-F]{2}){5})', line)
        if not m:
            continue
        ip  = m.group(1)
        mac = m.group(2).replace("-", ":").upper()
        if mac.startswith(("FF:FF", "01:00:5E", "00:00:00")):   # broadcast/multicast/vacío
            continue
        table[ip] = mac
    return table


def hostname_of(ip):
    try:
        socket.setdefaulttimeout(0.5)
        return socket.gethostbyaddr(ip)[0]
    except Exception:
        return ""


def en_subredes(ip, redes):
    try:
        a = ipaddress.ip_address(ip)
        return any(a in n for n in redes)
    except Exception:
        return False


def main():
    ts = datetime.datetime.now()
    redes = [ipaddress.ip_network(s, strict=False) for s in SUBNETS]

    print("=" * 64)
    print(f"  ESCANEO DE RED  ·  {EMPRESA}")
    print(f"  VLANs: {', '.join(SUBNETS)}   Gateway: {GATEWAY}")
    print("=" * 64)

    # 1) Lista de IPs a sondear
    ips = [str(h) for net in redes for h in net.hosts()]
    print(f"[1/4] Ping a {len(ips)} direcciones (1-3 min, no cierres la ventana)...")

    vivos = {}
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as ex:
        for res in ex.map(ping, ips):
            if res:
                vivos[res[0]] = res[1]
    print(f"      -> {len(vivos)} respondieron a ping")

    # 2) ARP (atrapa hosts que bloquean ICMP en la VLAN local)
    print("[2/4] Leyendo tabla ARP...")
    arp = get_arp_table()
    extra = 0
    for ip, mac in arp.items():
        if ip not in vivos and en_subredes(ip, redes):
            vivos[ip] = "0"
            extra += 1
    if extra:
        print(f"      -> {extra} host(s) extra detectados por ARP")

    # 3) Construir dispositivos (formato 'simple')
    print(f"[3/4] Resolviendo nombres de {len(vivos)} host(s)...")
    def keyip(x): return tuple(int(o) for o in x.split('.'))
    dispositivos = []
    for ip in sorted(vivos, key=keyip):
        mac = arp.get(ip, "")
        ms  = vivos[ip]
        try:
            lat_seg = str(round(float(ms) / 1000.0, 4))   # enriquecer espera segundos
        except Exception:
            lat_seg = "0"
        es_gw = ip.endswith(".1") or ip.endswith(".250") or ip == GATEWAY
        dispositivos.append({
            "ip": ip,
            "mac": mac if mac else "N/A",
            "vendor": "",                       # lo completa enriquecer por OUI/MAC
            "hostname": hostname_of(ip),
            "latencia": lat_seg,
            "estado": "up",
            "es_modem": es_gw,
            "modem_info": {"prioridad": "CRITICAL"} if es_gw else {}
        })

    metadata = {
        "timestamp": ts.isoformat(),
        "empresa": EMPRESA,
        "red": {"rango": ", ".join(SUBNETS), "gateway": GATEWAY, "interfaz": INTERFAZ},
        "velocidad_internet": {"download": "N/A", "upload": "N/A", "ping_ms": "N/A"},
        "total_dispositivos": len(dispositivos),
        "total_modems_detectados": sum(1 for d in dispositivos if d["es_modem"]),
        "dispositivos": dispositivos,
    }

    areas = {"_README": "Generado automaticamente - revisar y ajustar",
             "_EMPRESA": EMPRESA, "_GENERADO": ts.isoformat()}
    n = 1
    for d in dispositivos:
        if d["es_modem"]:
            areas[d["ip"]] = {
                "area": "Segmento/VLAN - por definir",
                "modem_info": f"Gateway/Router #{n}",
                "modem_sla": "Por confirmar",
                "mac_address": d["mac"],
                "notas": "Detectado como gateway/router (.1/.250)",
            }
            n += 1

    # 4) Guardar + comprimir
    folder = f"diagnostico_{EMPRESA.replace(' ', '_')}_{ts.strftime('%Y%m%d_%H%M%S')}"
    os.makedirs(folder, exist_ok=True)
    with open(os.path.join(folder, "metadata_simple.json"), "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    with open(os.path.join(folder, "areas_config_auto.json"), "w", encoding="utf-8") as f:
        json.dump(areas, f, indent=2, ensure_ascii=False)
    with open(os.path.join(folder, "hosts_vivos.txt"), "w", encoding="utf-8") as f:
        f.write("IP\tMAC\tHostname\tLatencia(s)\n")
        for d in dispositivos:
            f.write(f"{d['ip']}\t{d['mac']}\t{d['hostname']}\t{d['latencia']}\n")

    zip_path = folder + ".zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for root, _, files in os.walk(folder):
            for fn in files:
                fp = os.path.join(root, fn)
                z.write(fp, os.path.relpath(fp, os.path.dirname(folder) or "."))

    # Resumen por VLAN
    print("[4/4] Listo.")
    print("=" * 64)
    for net in redes:
        c = sum(1 for d in dispositivos if ipaddress.ip_address(d["ip"]) in net)
        print(f"  {str(net):18s} -> {c} host(s)")
    print(f"  TOTAL host(s):      {len(dispositivos)}")
    print(f"  Gateways/routers:   {metadata['total_modems_detectados']}")
    print(f"  ZIP generado:       {os.path.abspath(zip_path)}")
    print("=" * 64)
    print("  Envia ese .zip para generar el dashboard.")


if __name__ == "__main__":
    main()
