#!/usr/bin/env python3
"""
Enriquecedor de Metadata - Convierte diagnóstico simple a formato completo
"""

import json
import sys
import os

# Importar vendor lookup mejorado
try:
    from vendor_lookup import get_vendor
except ImportError:
    # Fallback si no está disponible
    def get_vendor(mac, current_vendor=""):
        return current_vendor if current_vendor else "Unknown"

def inferir_tipo(device):
    """Infiere el tipo de dispositivo basado en vendor, MAC, hostname, etc."""
    vendor = device.get('vendor', '').lower()
    hostname = device.get('hostname', '').lower()
    ip = device.get('ip', '')

    # Gateway (normalmente .1)
    if ip.endswith('.1') or 'gateway' in hostname:
        return 'gateway'

    # Juniper suele ser router/firewall
    if 'juniper' in vendor:
        return 'router'

    # Synology es NAS (servidor)
    if 'synology' in vendor:
        return 'server'

    # HP puede ser servidor o impresora
    if 'hp' in vendor or 'hewlett' in vendor:
        if 'laserjet' in vendor or 'printer' in hostname:
            return 'printer'
        return 'server'

    # Dell suele ser servidor o workstation
    if 'dell' in vendor:
        return 'server'

    # Asus, Gigabyte = workstation/desktop
    if any(x in vendor for x in ['asus', 'giga-byte', 'gigabyte', 'asustek']):
        return 'workstation'

    # Apple
    if 'apple' in vendor:
        return 'laptop'

    # Switches comunes
    if any(x in vendor for x in ['cisco', 'netgear', 'd-link', 'tp-link']):
        return 'switch'

    # Por defecto, workstation
    return 'workstation'

def asignar_departamento(tipo, index):
    """Asigna departamento basado en tipo de dispositivo"""
    if tipo in ['gateway', 'router', 'firewall']:
        return 'Core'
    elif tipo == 'server':
        departamentos_servidores = ['IT', 'Datos', 'Infraestructura']
        return departamentos_servidores[index % len(departamentos_servidores)]
    elif tipo == 'switch':
        return 'Networking'
    else:
        departamentos_usuarios = ['Desarrollo', 'Investigación', 'Administración', 'Operaciones']
        return departamentos_usuarios[index % len(departamentos_usuarios)]

def enriquecer_metadata(metadata_simple):
    """Enriquece metadata simple con tipos, conexiones y jerarquía"""

    # Información de la empresa
    empresa = {
        "nombre": "KAIS-GDI",
        "ubicacion": "Corea del Sur",
        "tipo": "Departamento de Investigación y Desarrollo"
    }

    # Primer pase: identificar tipos sin asignar padres
    dispositivos_temp = []
    gateway_ip = metadata_simple['red']['gateway']
    tipo_counters = {}

    for idx, device in enumerate(metadata_simple['dispositivos']):
        tipo = inferir_tipo(device)

        # Contador para nombres
        tipo_counters[tipo] = tipo_counters.get(tipo, 0) + 1
        num = tipo_counters[tipo]

        # Generar hostname si no existe
        if not device.get('hostname') or device['hostname'] == '':
            tipo_label = {
                'gateway': 'Gateway',
                'router': 'Router',
                'switch': 'Switch',
                'server': 'Server',
                'workstation': 'PC',
                'laptop': 'Laptop',
                'printer': 'Printer'
            }.get(tipo, 'Device')
            hostname = f"{tipo_label}-{num:02d}"
        else:
            hostname = device['hostname']

        dept = asignar_departamento(tipo, idx)

        # Padre se asignará en segundo pase
        padre = None

        # Velocidad estimada
        velocidad_map = {
            'gateway': '10 Gbps',
            'router': '10 Gbps',
            'switch': '1 Gbps',
            'server': '1 Gbps',
            'workstation': '1 Gbps',
            'laptop': '100 Mbps',
            'printer': '100 Mbps'
        }
        velocidad = velocidad_map.get(tipo, '100 Mbps')

        # Servicios típicos
        servicios_map = {
            'gateway': ['dhcp', 'dns', 'routing'],
            'router': ['routing', 'nat'],
            'switch': ['switching'],
            'server': ['http', 'https', 'ssh', 'smb'],
            'workstation': [],
            'laptop': [],
            'printer': ['ipp', 'http']
        }
        servicios = servicios_map.get(tipo, [])

        # Convertir latencia
        lat_raw = device.get('latencia', '0')
        if lat_raw == '' or lat_raw is None:
            lat_raw = '0'
        try:
            latencia_ms = str(float(lat_raw) * 1000)[:5]
        except:
            latencia_ms = '0'

        # Mejorar identificación de vendor usando MAC
        vendor_mejorado = get_vendor(
            device.get('mac', ''),
            device.get('vendor', '')
        )

        device_enriquecido = {
            'ip': device['ip'],
            'hostname': hostname,
            'mac': device.get('mac', 'N/A'),
            'vendor': vendor_mejorado,
            'tipo': tipo,
            'departamento': dept,
            'latencia': latencia_ms,
            'padre': padre,
            'velocidad': velocidad,
            'servicios': servicios,
            'estado': device.get('estado', 'up')
        }

        dispositivos_temp.append(device_enriquecido)

    # Segundo pase: asignar jerarquía realista
    dispositivos_enriquecidos = []

    # Separar por tipos
    gateway = next((d for d in dispositivos_temp if d['tipo'] == 'gateway'), None)
    routers = [d for d in dispositivos_temp if d['tipo'] == 'router']
    switches = [d for d in dispositivos_temp if d['tipo'] == 'switch']
    servers = [d for d in dispositivos_temp if d['tipo'] == 'server']
    workstations = [d for d in dispositivos_temp if d['tipo'] == 'workstation']
    others = [d for d in dispositivos_temp if d['tipo'] not in ['gateway', 'router', 'switch', 'server', 'workstation']]

    # Asignar padres según jerarquía
    # 1. Gateway no tiene padre
    if gateway:
        gateway['padre'] = None
        dispositivos_enriquecidos.append(gateway)

    # 2. Routers conectados al gateway
    for router in routers:
        router['padre'] = gateway_ip
        dispositivos_enriquecidos.append(router)

    # 3. Switches distribuidos entre routers (si no hay routers, van al gateway)
    if routers:
        for i, switch in enumerate(switches):
            switch['padre'] = routers[i % len(routers)]['ip']
            dispositivos_enriquecidos.append(switch)
    else:
        for switch in switches:
            switch['padre'] = gateway_ip
            dispositivos_enriquecidos.append(switch)

    # 4. Servidores distribuidos entre switches (si no hay switches, van a routers o gateway)
    if switches:
        for i, server in enumerate(servers):
            server['padre'] = switches[i % len(switches)]['ip']
            dispositivos_enriquecidos.append(server)
    elif routers:
        for i, server in enumerate(servers):
            server['padre'] = routers[i % len(routers)]['ip']
            dispositivos_enriquecidos.append(server)
    else:
        for server in servers:
            server['padre'] = gateway_ip
            dispositivos_enriquecidos.append(server)

    # 5. Workstations distribuidas entre switches
    if switches:
        for i, ws in enumerate(workstations):
            ws['padre'] = switches[i % len(switches)]['ip']
            dispositivos_enriquecidos.append(ws)
    elif routers:
        for i, ws in enumerate(workstations):
            ws['padre'] = routers[i % len(routers)]['ip']
            dispositivos_enriquecidos.append(ws)
    else:
        for ws in workstations:
            ws['padre'] = gateway_ip
            dispositivos_enriquecidos.append(ws)

    # 6. Otros dispositivos distribuidos entre switches
    if switches:
        for i, other in enumerate(others):
            other['padre'] = switches[i % len(switches)]['ip']
            dispositivos_enriquecidos.append(other)
    elif routers:
        for i, other in enumerate(others):
            other['padre'] = routers[i % len(routers)]['ip']
            dispositivos_enriquecidos.append(other)
    else:
        for other in others:
            other['padre'] = gateway_ip
            dispositivos_enriquecidos.append(other)

    # Crear conexiones con tipos apropiados
    conexiones = []
    for device in dispositivos_enriquecidos:
        if device['padre']:
            # Determinar tipo de conexión según jerarquía
            if device['tipo'] == 'router':
                tipo_conn = 'backbone'  # Gateway → Router
            elif device['tipo'] == 'switch':
                tipo_conn = 'troncal'   # Router → Switch
            elif device['tipo'] == 'server':
                tipo_conn = 'troncal'   # Switch → Server
            else:
                tipo_conn = 'acceso'    # Switch → Workstation/otros

            conexiones.append({
                'from': device['padre'],
                'to': device['ip'],
                'tipo': tipo_conn
            })

    # Estadísticas
    tipos_count = {}
    vendors_count = {}
    for d in dispositivos_enriquecidos:
        tipos_count[d['tipo']] = tipos_count.get(d['tipo'], 0) + 1
        vendors_count[d['vendor']] = vendors_count.get(d['vendor'], 0) + 1

    estadisticas = {
        'total_dispositivos': len(dispositivos_enriquecidos),
        'tipos': tipos_count,
        'vendors': list(vendors_count.keys()),
        'total_bandwidth_mbps': sum([
            10000 if d['velocidad'] == '10 Gbps' else
            1000 if d['velocidad'] == '1 Gbps' else
            100 for d in dispositivos_enriquecidos
        ])
    }

    # Metadata enriquecido
    metadata_enriquecido = {
        'timestamp': metadata_simple['timestamp'],
        'ubicacion': 'Corea del Sur',
        'empresa': empresa,
        'red': metadata_simple['red'],
        'velocidad_internet': metadata_simple['velocidad_internet'],
        'total_dispositivos': len(dispositivos_enriquecidos),
        'dispositivos': dispositivos_enriquecidos,
        'conexiones': conexiones,
        'latencias': metadata_simple.get('latencias', []),
        'estadisticas': estadisticas
    }

    return metadata_enriquecido

def main():
    if len(sys.argv) < 2:
        print("Uso: python3 enriquecer_metadata_kais.py <metadata_simple.json>")
        sys.exit(1)

    input_file = sys.argv[1]

    # Leer metadata simple
    with open(input_file, 'r', encoding='utf-8') as f:
        metadata_simple = json.load(f)

    # Enriquecer
    metadata_enriquecido = enriquecer_metadata(metadata_simple)

    # Guardar en directorio actual (no en el original que puede ser de root)
    base_name = os.path.basename(input_file).replace('.json', '_enriquecido.json')
    output_file = os.path.join(os.getcwd(), base_name)
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(metadata_enriquecido, f, indent=2, ensure_ascii=False)

    print(f"✅ Metadata enriquecido guardado en: {output_file}")
    print(f"\n📊 Estadísticas:")
    print(f"   • Total dispositivos: {metadata_enriquecido['total_dispositivos']}")
    print(f"   • Empresa: {metadata_enriquecido['empresa']['nombre']}")
    print(f"   • Red: {metadata_enriquecido['red']['rango']}")
    print(f"\n🔧 Tipos detectados:")
    for tipo, count in metadata_enriquecido['estadisticas']['tipos'].items():
        print(f"   • {tipo}: {count}")

if __name__ == "__main__":
    main()
