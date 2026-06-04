#!/usr/bin/env python3
"""
Visualizador Triple Vista - Con logos y 3 topologías
"""

import os, sys, json, zipfile, datetime, webbrowser
from collections import defaultdict

def cargar(zip_file):
    carpeta = "gemelo_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    with zipfile.ZipFile(zip_file, 'r') as z:
        z.extractall(carpeta)
    for root, _, files in os.walk(carpeta):
        for f in files:
            if "metadata" in f and f.endswith(".json"):
                with open(os.path.join(root, f), 'r') as file:
                    return json.load(file), carpeta
    return None, carpeta

def cargar_areas_config():
    """Carga configuración de áreas personalizadas si existe"""
    config_path = "areas_config.json"
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
                # Filtrar claves que empiezan con _ (comentarios)
                return {k: v for k, v in config.items() if not k.startswith('_')}
        except Exception as e:
            print(f"⚠️  Error leyendo areas_config.json: {e}")
            return {}
    return {}

def analizar_red(dispositivos, conexiones, metadata, areas_config={}):
    """Genera diagnóstico inteligente de la red"""

    # Análisis de velocidades
    speeds = {'10 Gbps': 0, '1 Gbps': 0, '100 Mbps': 0, '<100 Mbps': 0}
    slow_nodes = []

    for d in dispositivos:
        vel = d.get('velocidad', '100 Mbps')
        if '10 Gbps' in vel or '10Gbps' in vel:
            speeds['10 Gbps'] += 1
        elif '1 Gbps' in vel or '1Gbps' in vel or '1000 Mbps' in vel:
            speeds['1 Gbps'] += 1
        elif '100 Mbps' in vel:
            speeds['100 Mbps'] += 1
            slow_nodes.append(d)
        else:
            speeds['<100 Mbps'] += 1
            slow_nodes.append(d)

    # Análisis de tipos
    tipos_count = {}
    for d in dispositivos:
        tipo = d.get('tipo', 'unknown')
        tipos_count[tipo] = tipos_count.get(tipo, 0) + 1

    # Análisis de fabricantes
    vendors_set = set(d.get('vendor', 'Unknown') for d in dispositivos)

    # Detección de problemas
    issues = {
        'critico': [],
        'advertencia': [],
        'recomendacion': []
    }

    # NUEVO: Análisis de SLA de módems
    modems_incumplen_sla = []
    total_modems_con_sla = 0

    for d in dispositivos:
        area_info = areas_config.get(d['ip'], {})
        if 'modem_sla' in area_info:
            total_modems_con_sla += 1

            # Extraer velocidad contratada
            sla_str = area_info['modem_sla']
            import re
            sla_match = re.search(r'(\d+)', sla_str)
            if sla_match:
                sla_mbps = int(sla_match.group(1))

                # Extraer velocidad real
                vel = d.get('velocidad', '')
                vel_real_mbps = 0

                if 'Gbps' in vel:
                    vel_match = re.search(r'([\d.]+)', vel)
                    if vel_match:
                        vel_real_mbps = int(float(vel_match.group(1)) * 1000)
                elif 'Mbps' in vel:
                    vel_match = re.search(r'(\d+)', vel)
                    if vel_match:
                        vel_real_mbps = int(vel_match.group(1))

                # Calcular cumplimiento
                if sla_mbps > 0:
                    cumplimiento = (vel_real_mbps / sla_mbps) * 100

                    # Si no cumple al menos 90% del SLA
                    if cumplimiento < 90:
                        modems_incumplen_sla.append({
                            'ip': d['ip'],
                            'hostname': d.get('hostname', d['ip']),
                            'modem_info': area_info.get('modem_info', 'Módem'),
                            'sla_contratado': sla_mbps,
                            'velocidad_real': vel_real_mbps,
                            'cumplimiento': cumplimiento,
                            'area': area_info.get('area', 'N/A')
                        })

    # Agregar problema si hay módems que no cumplen SLA
    if len(modems_incumplen_sla) > 0:
        if any(m['cumplimiento'] < 70 for m in modems_incumplen_sla):
            # Crítico si alguno está por debajo del 70%
            issues['critico'].append({
                'titulo': f'{len(modems_incumplen_sla)} Módem(s) NO Cumplen SLA Contratado',
                'descripcion': f'{len([m for m in modems_incumplen_sla if m["cumplimiento"] < 70])} módem(s) operando a menos del 70% de velocidad contratada',
                'impacto': 'ALTO - Incumplimiento contractual grave, afecta operaciones',
                'accion': 'Contactar a proveedor inmediatamente para solución o reclamo de SLA'
            })
        else:
            # Advertencia si están entre 70-90%
            issues['advertencia'].append({
                'titulo': f'{len(modems_incumplen_sla)} Módem(s) con Velocidad Baja (70-90% SLA)',
                'descripcion': f'Módems operando por debajo del rendimiento esperado',
                'impacto': 'MEDIO - Rendimiento degradado, posible incumplimiento de SLA',
                'accion': 'Monitorear y contactar a proveedor si persiste'
            })

    # Problema crítico: Sin firewall
    if tipos_count.get('firewall', 0) == 0:
        issues['critico'].append({
            'titulo': 'Sin Firewall Detectado',
            'descripcion': f'La red tiene {len(dispositivos)} dispositivos sin protección perimetral.',
            'impacto': 'ALTO - Vulnerabilidad de seguridad crítica',
            'accion': 'Implementar firewall entre gateway y routers inmediatamente'
        })

    # Problema: Usar routers en lugar de switches
    if tipos_count.get('router', 0) > 3 and tipos_count.get('switch', 0) == 0:
        issues['advertencia'].append({
            'titulo': 'Arquitectura Ineficiente: Routers en Lugar de Switches',
            'descripcion': f'{tipos_count.get("router", 0)} routers usados para distribución LAN',
            'impacto': 'MEDIO - Sobrecosto operativo y latencia innecesaria',
            'accion': f'Reemplazar {tipos_count.get("router", 0) - 2} routers por 2-3 switches administrados'
        })

    # Nodos lentos
    if len(slow_nodes) > 0:
        issues['advertencia'].append({
            'titulo': f'{len(slow_nodes)} Dispositivos con Velocidad Baja',
            'descripcion': f'Equipos operando a ≤100 Mbps que pueden causar cuellos de botella',
            'impacto': 'MEDIO - Degradación de rendimiento',
            'accion': 'Ver lista detallada abajo y priorizar upgrades'
        })

    # Diversidad de vendors
    if len(vendors_set) > 10:
        issues['recomendacion'].append({
            'titulo': f'Alta Diversidad de Fabricantes ({len(vendors_set)} diferentes)',
            'descripcion': 'Muchos vendors dificultan soporte y mantenimiento',
            'impacto': 'BAJO - Complejidad operativa',
            'accion': 'Estandarizar en 3-5 vendors principales para futuras compras'
        })

    # Velocidad de internet baja para investigación
    download_speed = float(metadata.get('velocidad_internet', {}).get('download', '0 Mbit/s').split()[0])
    if download_speed < 100 and tipos_count.get('server', 0) > 5:
        issues['recomendacion'].append({
            'titulo': f'Velocidad de Internet Baja ({download_speed:.1f} Mbps)',
            'descripcion': f'Con {tipos_count.get("server", 0)} servidores, se recomienda más ancho de banda',
            'impacto': 'BAJO - Posible limitación para transferencias externas',
            'accion': 'Considerar upgrade a 200+ Mbps si el presupuesto lo permite'
        })

    # Cálculos para métricas ejecutivas
    health_score = calcular_salud(issues, speeds, len(dispositivos))

    # Costo estimado de hardware
    costo_hardware = (
        tipos_count.get('gateway', 0) * 15000 +
        tipos_count.get('firewall', 0) * 15000 +
        tipos_count.get('router', 0) * 8000 +
        tipos_count.get('switch', 0) * 5000 +
        tipos_count.get('server', 0) * 12000 +
        tipos_count.get('workstation', 0) * 1500 +
        tipos_count.get('laptop', 0) * 1500 +
        (len(dispositivos) - sum(tipos_count.get(t, 0) for t in ['gateway', 'firewall', 'router', 'switch', 'server', 'workstation', 'laptop'])) * 500
    )

    # Costo de mantenimiento anual (15% del hardware)
    costo_mantenimiento = int(costo_hardware * 0.15)

    # ROI calculations
    costo_mejoras = len(issues['critico']) * 8000 + len(issues['advertencia']) * 3000
    ahorro_anual = len(issues['critico']) * 35000 + len(issues['advertencia']) * 12000
    roi_porcentaje = int((ahorro_anual / costo_mejoras * 100) if costo_mejoras > 0 else 0)

    # Uptime estimado
    uptime_estimado = 95 + (health_score / 100 * 4.5)

    # Inversión total sugerida
    inversion_firewall = 8500 if len([i for i in issues['critico'] if 'firewall' in str(i).lower()]) > 0 else 0
    inversion_switches = 15000 if tipos_count.get('router', 0) > 5 else 0
    inversion_total = inversion_firewall + inversion_switches + 4500 + 6000

    return {
        'speeds': speeds,
        'slow_nodes': slow_nodes,
        'tipos_count': tipos_count,
        'vendors_count': len(vendors_set),
        'issues': issues,
        'health_score': health_score,
        # Métricas ejecutivas
        'costo_hardware': costo_hardware,
        'costo_mantenimiento': costo_mantenimiento,
        'costo_mejoras': costo_mejoras,
        'ahorro_anual': ahorro_anual,
        'roi_porcentaje': roi_porcentaje,
        'uptime_estimado': uptime_estimado,
        'inversion_firewall': inversion_firewall,
        'inversion_switches': inversion_switches,
        'inversion_total': inversion_total,
        # Análisis de módems SLA
        'modems_incumplen_sla': modems_incumplen_sla,
        'total_modems_con_sla': total_modems_con_sla
    }

def calcular_salud(issues, speeds, total_devices):
    """Calcula score de salud de 0-100"""
    score = 100

    # Penalizar por problemas
    score -= len(issues['critico']) * 25
    score -= len(issues['advertencia']) * 10
    score -= len(issues['recomendacion']) * 5

    # Bonificar por velocidades altas
    high_speed_ratio = (speeds['10 Gbps'] + speeds['1 Gbps']) / max(total_devices, 1)
    score = score * (0.7 + 0.3 * high_speed_ratio)

    return max(0, min(100, int(score)))

def generar(metadata, carpeta, areas_config={}):
    import shutil

    dispositivos = metadata['dispositivos']
    conexiones = metadata['conexiones']
    red = metadata['red']
    vel = metadata['velocidad_internet']
    empresa = metadata['empresa']
    stats = metadata['estadisticas']

    # Generar diagnóstico
    diagnostico = analizar_red(dispositivos, conexiones, metadata, areas_config)

    # Copiar librerías locales al directorio de salida
    script_dir = os.path.dirname(os.path.abspath(__file__))
    for lib in ['vis-network.min.js', 'chart.min.js']:
        src = os.path.join(script_dir, lib)
        if os.path.exists(src):
            shutil.copy(src, carpeta)

    # Copiar iconos de red si existen
    icons_src = os.path.join(script_dir, 'network-icons')
    if os.path.exists(icons_src):
        icons_dst = os.path.join(carpeta, 'network-icons')
        if os.path.exists(icons_dst):
            shutil.rmtree(icons_dst)
        shutil.copytree(icons_src, icons_dst)

    ip_to_id = {d['ip']: i for i, d in enumerate(dispositivos)}

    # Logos como Data URIs (SVG inline)
    logos = {
        'fortinet': 'https://upload.wikimedia.org/wikipedia/commons/6/62/Fortinet_logo.svg',
        'cisco': 'https://upload.wikimedia.org/wikipedia/commons/0/08/Cisco_logo_blue_2016.svg',
        'telmex': 'https://upload.wikimedia.org/wikipedia/commons/3/33/Telmex_Logo.svg',
        'hp': 'https://upload.wikimedia.org/wikipedia/commons/a/ad/HP_logo_2012.svg',
        'dell': 'https://upload.wikimedia.org/wikipedia/commons/4/48/Dell_Logo.svg'
    }

    # Análisis de vendors
    vendors_count_temp = defaultdict(int)
    for d in dispositivos:
        vendor = d.get('vendor', 'Desconocido')
        # Simplificar nombre de vendor
        if 'Fortinet' in vendor:
            vendors_count_temp['Fortinet'] += 1
        elif 'Cisco' in vendor:
            vendors_count_temp['Cisco'] += 1
        elif 'Telmex' in vendor or 'Infinitum' in vendor:
            vendors_count_temp['Telmex'] += 1
        elif 'TP-Link' in vendor:
            vendors_count_temp['TP-Link'] += 1
        elif 'D-Link' in vendor or 'DLink' in vendor:
            vendors_count_temp['D-Link'] += 1
        elif 'HP' in vendor or 'Hewlett' in vendor:
            vendors_count_temp['HP'] += 1
        elif 'Dell' in vendor:
            vendors_count_temp['Dell'] += 1
        elif 'Lenovo' in vendor:
            vendors_count_temp['Lenovo'] += 1
        elif 'Netgear' in vendor:
            vendors_count_temp['Netgear'] += 1
        elif 'Hikvision' in vendor:
            vendors_count_temp['Hikvision'] += 1
        elif 'Dahua' in vendor:
            vendors_count_temp['Dahua'] += 1
        elif 'Synology' in vendor:
            vendors_count_temp['Synology'] += 1
        elif 'ZTE' in vendor:
            vendors_count_temp['ZTE'] += 1
        elif 'Huawei' in vendor:
            vendors_count_temp['Huawei'] += 1
        elif 'Brother' in vendor:
            vendors_count_temp['Brother'] += 1
        elif 'Canon' in vendor:
            vendors_count_temp['Canon'] += 1
        else:
            vendors_count_temp[vendor] += 1

    # Ordenar vendors de mayor a menor
    vendors_count = dict(sorted(vendors_count_temp.items(), key=lambda x: x[1], reverse=True))

    # Análisis por departamento
    dept_count = defaultdict(int)
    for d in dispositivos:
        dept = d.get('departamento', 'N/A')
        dept_count[dept] += 1

    # Análisis por velocidad
    speed_count = defaultdict(int)
    for d in dispositivos:
        speed = d.get('velocidad', 'N/A')
        speed_count[speed] += 1

    # Análisis detallado de tipos de terminal
    terminal_types = defaultdict(int)
    for d in dispositivos:
        tipo = d.get('tipo', 'unknown')
        if tipo in ['workstation', 'laptop', 'smartphone', 'tablet']:
            terminal_types[tipo] += 1
        elif tipo == 'server':
            terminal_types['Servidores'] += 1
        elif tipo in ['router', 'switch', 'gateway', 'firewall']:
            terminal_types['Infraestructura'] += 1
        else:
            terminal_types['Otros'] += 1

    nodos = []
    edges = []

    # Mapeo de tipos a iconos SVG
    icon_map = {
        'gateway': 'network-icons/conectividad/router.svg',
        'router': 'network-icons/conectividad/router.svg',
        'firewall': 'network-icons/seguridad/firewall.svg',
        'modem': 'network-icons/conectividad/modem.svg',
        'switch': 'network-icons/conectividad/switch.svg',
        'server': 'network-icons/servidores/servidor.svg',
        'workstation': 'network-icons/terminales/pc.svg',
        'laptop': 'network-icons/terminales/laptop.svg',
        'printer': 'network-icons/terminales/impresora.svg',
        'camera': 'network-icons/terminales/camara_ip.svg',
        'iot': 'network-icons/terminales/iot.svg'
    }

    config_tipos = {
        'gateway': {'color': '#1e40af', 'size': 60, 'shape': 'image', 'symbol': '◈', 'label': 'GATEWAY'},
        'router': {'color': '#0c4a6e', 'size': 55, 'shape': 'image', 'symbol': '🔶', 'label': 'ROUTER'},
        'firewall': {'color': '#dc2626', 'size': 55, 'shape': 'image', 'symbol': '🛡️', 'label': 'FIREWALL'},
        'modem': {'color': '#0ea5e9', 'size': 50, 'shape': 'image', 'symbol': '📡', 'label': 'MODEM'},
        'switch': {'color': '#10b981', 'size': 50, 'shape': 'image', 'symbol': '⬣', 'label': 'SWITCH'},
        'server': {'color': '#f59e0b', 'size': 50, 'shape': 'image', 'symbol': '▮', 'label': 'SERVER'},
        'workstation': {'color': '#6b7280', 'size': 40, 'shape': 'image', 'symbol': '💻', 'label': 'PC'},
        'laptop': {'color': '#8b5cf6', 'size': 40, 'shape': 'image', 'symbol': '💻', 'label': 'LAPTOP'},
        'printer': {'color': '#ec4899', 'size': 40, 'shape': 'image', 'symbol': '🖨️', 'label': 'PRINTER'},
        'camera': {'color': '#ef4444', 'size': 40, 'shape': 'image', 'symbol': '📷', 'label': 'CAM'},
        'iot': {'color': '#14b8a6', 'size': 35, 'shape': 'image', 'symbol': '○', 'label': 'IOT'}
    }

    # Crear nodos con logos cuando sea posible
    for i, d in enumerate(dispositivos):
        tipo = d.get('tipo', 'unknown')
        cfg = config_tipos.get(tipo, config_tipos['workstation'])
        vendor = d.get('vendor', '')

        hostname = d.get('hostname', d['ip'])[:30]
        velocidad = d.get('velocidad', '')

        # Etiquetas completas: Tipo + IP + Hostname
        tipo_label_map = {
            'gateway': 'GATEWAY',
            'router': 'ROUTER',
            'firewall': 'FIREWALL',
            'switch': 'SWITCH',
            'server': 'SERVER',
            'workstation': 'PC',
            'laptop': 'LAPTOP',
            'printer': 'PRINTER',
            'camera': 'CAM',
            'iot': 'IOT'
        }

        tipo_text = tipo_label_map.get(tipo, tipo.upper())
        hostname_short = hostname[:20] if len(hostname) > 20 else hostname

        # Formato: TIPO\nIP\nHostname
        if tipo in ['gateway', 'router', 'firewall', 'server']:
            # Nodos importantes: más información
            label = f"{tipo_text}\n{d['ip']}\n{hostname_short}"
        else:
            # Nodos regulares: info compacta
            label = f"{tipo_text}\n{d['ip']}"

        title = f"<b>{hostname}</b><br>"
        title += f"IP: {d['ip']}<br>"
        title += f"Tipo: {tipo.upper()}<br>"
        if velocidad:
            title += f"⚡ {velocidad}<br>"
        title += f"Vendor: {d.get('vendor', 'N/A')}<br>"
        title += f"Latencia: {d.get('latencia', 'N/A')} ms<br>"
        title += f"Depto: {d.get('departamento', 'N/A')}"

        # Agregar información de área personalizada si existe
        area_info = areas_config.get(d['ip'])
        if area_info:
            title += "<br><br><b>📍 Ubicación:</b><br>"
            for key, value in area_info.items():
                # Formatear clave (snake_case → Title Case)
                key_formatted = key.replace('_', ' ').title()
                title += f"{key_formatted}: {value}<br>"

        # Agregar imagen si existe icono
        icon_path = icon_map.get(tipo)

        # Determinar color según velocidad (identificar nodos lentos)
        velocidad_str = d.get('velocidad', '100 Mbps')
        border_color = cfg['color']  # Color por defecto según tipo

        # Extraer valor numérico de velocidad
        if '10 Gbps' in velocidad_str or '10Gbps' in velocidad_str:
            # Muy rápido - Verde (OK)
            border_color = '#059669'
            speed_category = 'fast'
        elif '1 Gbps' in velocidad_str or '1Gbps' in velocidad_str or '1000 Mbps' in velocidad_str:
            # Rápido - Azul (OK)
            border_color = '#0ea5e9'
            speed_category = 'normal'
        elif '100 Mbps' in velocidad_str:
            # Lento - Naranja (Advertencia)
            border_color = '#f59e0b'
            speed_category = 'slow'
        else:
            # Muy lento o desconocido - Rojo (Problema)
            border_color = '#ef4444'
            speed_category = 'very_slow'

        nodo = {
            'id': i,
            'label': label,
            'title': title,
            'size': cfg['size'],
            'shape': cfg['shape'],
            'font': {
                'size': 11 if tipo in ['modem', 'firewall', 'gateway', 'router'] else 9,
                'color': '#1e293b',
                'face': 'Arial',
                'multi': 'html',
                'bold': {'mod': 'bold'} if tipo in ['gateway', 'firewall', 'router'] else {}
            },
            'borderWidth': 4 if speed_category in ['slow', 'very_slow'] else 3,
            'shadow': {
                'enabled': True,
                'size': 12 if speed_category == 'very_slow' else 10 if tipo in ['gateway', 'firewall', 'router'] else 6,
                'color': 'rgba(239, 68, 68, 0.4)' if speed_category == 'very_slow' else 'rgba(0,0,0,0.2)'
            },
            'shapeProperties': {
                'borderRadius': 6
            }
        }

        # Si existe icono, usar imagen
        if icon_path:
            nodo['image'] = icon_path
            nodo['shape'] = 'image'
            nodo['color'] = {
                'border': border_color,
                'highlight': {'border': '#000000'}
            }
        else:
            # Fallback a colores
            nodo['color'] = {
                'background': cfg['color'],
                'border': border_color,
                'highlight': {'background': cfg['color'], 'border': '#000000'}
            }

        nodos.append(nodo)

    # Crear edges
    for conn in conexiones:
        if conn['from'] in ip_to_id and conn['to'] in ip_to_id:
            tipo_conn = conn.get('tipo', 'acceso')

            if tipo_conn == 'backbone':
                width, color, dashes = 8, '#1e40af', False
            elif tipo_conn == 'troncal':
                width, color, dashes = 5, '#10b981', False
            else:
                width, color, dashes = 2, '#9ca3af', [5, 5]

            edge = {
                'from': ip_to_id[conn['from']],
                'to': ip_to_id[conn['to']],
                'width': width,
                'color': {'color': color, 'opacity': 0.6},
                'dashes': dashes,
                'smooth': {'type': 'continuous'},
                'arrows': {'to': {'enabled': False}},
                'shadow': {'enabled': True} if tipo_conn != 'acceso' else {'enabled': False}
            }
            edges.append(edge)

    por_tipo = defaultdict(list)
    for d in dispositivos:
        por_tipo[d.get('tipo', 'unknown')].append(d)

    tipos_count = {t: len(d) for t, d in por_tipo.items()}

    html = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{empresa['nombre']} - Network Topology Pro</title>
    <script src="vis-network.min.js"></script>
    <script src="chart.min.js"></script>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
        }}
        .header {{
            background: linear-gradient(135deg, #1e40af 0%, #0ea5e9 100%);
            color: white;
            padding: 20px 40px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        .header h1 {{
            font-size: 1.8em;
            font-weight: 700;
        }}
        .header .sub {{
            opacity: 0.95;
            margin-top: 5px;
        }}
        .container {{
            max-width: 1900px;
            margin: 0 auto;
            padding: 25px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
            gap: 15px;
            margin-bottom: 25px;
        }}
        .stat {{
            background: white;
            padding: 18px;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            border-left: 4px solid #1e40af;
        }}
        .stat-num {{
            font-size: 2.2em;
            font-weight: 700;
            color: #1e40af;
        }}
        .stat-label {{
            color: #64748b;
            font-size: 0.9em;
            margin-top: 4px;
        }}
        .section {{
            background: white;
            padding: 25px;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            margin-bottom: 25px;
        }}
        .section-title {{
            font-size: 1.4em;
            color: #1e293b;
            margin-bottom: 18px;
            padding-bottom: 8px;
            border-bottom: 2px solid #e2e8f0;
        }}
        .topology-container {{
            width: 100%;
            height: 750px;
            border: 2px solid #e2e8f0;
            border-radius: 10px;
            background: #ffffff;
            box-shadow: inset 0 2px 8px rgba(0,0,0,0.05);
        }}
        .legend {{
            display: flex;
            flex-wrap: wrap;
            gap: 20px;
            margin: 18px 0;
            padding: 18px;
            background: #f8fafc;
            border-radius: 8px;
            border: 1px solid #e2e8f0;
        }}
        .legend-item {{
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.9em;
        }}
        .legend-box {{
            width: 18px;
            height: 18px;
            border-radius: 3px;
            border: 2px solid #1e293b;
        }}
        .network-info {{
            background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
            padding: 20px;
            border-radius: 10px;
            margin: 18px 0;
            border-left: 4px solid #0ea5e9;
        }}
        .network-info p {{
            margin: 8px 0;
            font-size: 1.02em;
            color: #1e293b;
        }}
        .network-info strong {{
            color: #0f172a;
            font-weight: 600;
        }}
        .highlight-box {{
            background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #0ea5e9;
            margin: 15px 0;
        }}
        .highlight-box h4 {{
            color: #1e40af;
            margin-bottom: 8px;
            font-size: 1.1em;
        }}
        .badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 0.85em;
            font-weight: 600;
            margin: 0 5px;
        }}
        .badge-modem {{
            background: #0ea5e9;
            color: white;
        }}
        .badge-firewall {{
            background: #dc2626;
            color: white;
        }}

        /* Tabs para las vistas */
        .tabs {{
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            border-bottom: 2px solid #e2e8f0;
        }}
        .tab {{
            padding: 12px 24px;
            background: #f1f5f9;
            border: none;
            border-radius: 8px 8px 0 0;
            cursor: pointer;
            font-size: 1em;
            font-weight: 600;
            color: #64748b;
            transition: all 0.3s;
        }}
        .tab:hover {{
            background: #e2e8f0;
            color: #1e293b;
        }}
        .tab.active {{
            background: #1e40af;
            color: white;
        }}
        .view {{
            display: none;
        }}
        .view.active {{
            display: block;
        }}

        /* Charts grid - 3 por línea */
        .charts-grid {{
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 25px;
            margin-top: 20px;
        }}
        @media (max-width: 1400px) {{
            .charts-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
        }}
        @media (max-width: 900px) {{
            .charts-grid {{
                grid-template-columns: 1fr;
            }}
        }}
        .chart-box {{
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
        }}
        .chart-container {{
            position: relative;
            height: 350px;
            width: 100%;
        }}

        /* Hierarchical tree */
        .tree {{
            margin: 20px;
        }}
        .tree-node {{
            margin: 10px 0;
            padding-left: 20px;
            border-left: 2px solid #e2e8f0;
        }}
        .tree-node-header {{
            display: flex;
            align-items: center;
            padding: 8px 12px;
            background: #f8fafc;
            border-radius: 6px;
            margin: 4px 0;
            cursor: pointer;
            transition: all 0.2s;
        }}
        .tree-node-header:hover {{
            background: #e2e8f0;
        }}
        .tree-node-icon {{
            width: 24px;
            height: 24px;
            margin-right: 10px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
        }}
        .tree-node-children {{
            margin-left: 20px;
            display: none;
        }}
        .tree-node-children.expanded {{
            display: block;
        }}
        .expand-icon {{
            margin-right: 8px;
            font-weight: bold;
            color: #64748b;
        }}

        /* Modal para información detallada */
        .modal {{
            display: none;
            position: fixed;
            z-index: 1000;
            left: 0;
            top: 0;
            width: 100%;
            height: 100%;
            background-color: rgba(0,0,0,0.5);
            backdrop-filter: blur(4px);
        }}
        .modal-content {{
            background-color: white;
            margin: 5% auto;
            padding: 0;
            border-radius: 12px;
            width: 90%;
            max-width: 600px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.3);
            animation: slideDown 0.3s ease-out;
        }}
        @keyframes slideDown {{
            from {{
                transform: translateY(-50px);
                opacity: 0;
            }}
            to {{
                transform: translateY(0);
                opacity: 1;
            }}
        }}
        .modal-header {{
            background: linear-gradient(135deg, #1e40af 0%, #0ea5e9 100%);
            color: white;
            padding: 20px 25px;
            border-radius: 12px 12px 0 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        .modal-header h2 {{
            margin: 0;
            font-size: 1.4em;
        }}
        .close {{
            color: white;
            font-size: 32px;
            font-weight: bold;
            cursor: pointer;
            background: none;
            border: none;
            padding: 0;
            line-height: 1;
            transition: transform 0.2s;
        }}
        .close:hover {{
            transform: scale(1.2);
        }}
        .modal-body {{
            padding: 25px;
        }}
        .info-grid {{
            display: grid;
            grid-template-columns: 140px 1fr;
            gap: 12px;
            margin: 10px 0;
        }}
        .info-label {{
            font-weight: 600;
            color: #64748b;
            display: flex;
            align-items: center;
        }}
        .info-value {{
            color: #1e293b;
            padding: 8px 12px;
            background: #f8fafc;
            border-radius: 6px;
            border-left: 3px solid #0ea5e9;
            font-family: monospace;
        }}
        .device-icon-large {{
            width: 60px;
            height: 60px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            margin: 0 auto 15px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
        }}
        .vendors-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
            gap: 15px;
            margin: 20px 0;
        }}
        .vendor-card {{
            background: white;
            border: 2px solid #e2e8f0;
            border-radius: 10px;
            padding: 15px;
            text-align: center;
            transition: all 0.3s;
            cursor: pointer;
        }}
        .vendor-card:hover {{
            border-color: #0ea5e9;
            box-shadow: 0 4px 12px rgba(14, 165, 233, 0.2);
            transform: translateY(-2px);
        }}
        .vendor-icon {{
            width: 60px;
            height: 60px;
            margin: 0 auto 10px;
        }}
        .vendor-icon img {{
            width: 100%;
            height: 100%;
            object-fit: contain;
        }}
        .vendor-name {{
            font-weight: 600;
            color: #1e293b;
            font-size: 0.9em;
            margin-bottom: 4px;
        }}
        .vendor-count {{
            color: #64748b;
            font-size: 0.85em;
        }}

        /* Barra de búsqueda */
        .search-container {{
            margin: 20px 0;
            padding: 20px;
            background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%);
            border-radius: 10px;
            border: 2px solid #0ea5e9;
        }}
        .search-box {{
            display: flex;
            gap: 15px;
            align-items: center;
            flex-wrap: wrap;
        }}
        .search-input {{
            flex: 1;
            min-width: 300px;
            padding: 12px 20px;
            font-size: 1em;
            border: 2px solid #0ea5e9;
            border-radius: 8px;
            background: white;
            transition: all 0.3s;
        }}
        .search-input:focus {{
            outline: none;
            border-color: #1e40af;
            box-shadow: 0 0 0 3px rgba(30, 64, 175, 0.1);
        }}
        .search-filters {{
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }}
        .filter-btn {{
            padding: 8px 16px;
            border: 2px solid #cbd5e1;
            background: white;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.9em;
            font-weight: 600;
            color: #64748b;
            transition: all 0.2s;
        }}
        .filter-btn:hover {{
            border-color: #0ea5e9;
            color: #0ea5e9;
        }}
        .filter-btn.active {{
            background: #0ea5e9;
            color: white;
            border-color: #0ea5e9;
        }}
        .search-results {{
            margin-top: 10px;
            padding: 10px 15px;
            background: white;
            border-radius: 6px;
            font-size: 0.95em;
            color: #1e293b;
            font-weight: 600;
        }}
        .search-results .highlight {{
            color: #0ea5e9;
            font-size: 1.1em;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🌐 {empresa['nombre']}</h1>
        <div class="sub">Gemelo Digital Triple Vista · {empresa['ubicacion']} · {metadata['timestamp'][:16]}</div>
    </div>

    <div class="container">
        <div class="stats">
            <div class="stat">
                <div class="stat-num">{len(dispositivos)}</div>
                <div class="stat-label">Total Dispositivos</div>
            </div>
            <div class="stat">
                <div class="stat-num">{len([d for d in dispositivos if d.get('tipo') in ['workstation', 'laptop']])}</div>
                <div class="stat-label">💻 PC/Laptops</div>
            </div>
            <div class="stat">
                <div class="stat-num">{len([d for d in dispositivos if d.get('tipo') == 'server'])}</div>
                <div class="stat-label">🖥️ Servidores</div>
            </div>
            <div class="stat">
                <div class="stat-num">{len([d for d in dispositivos if d.get('tipo') in ['router', 'switch']])}</div>
                <div class="stat-label">🔶 Routers/Switches</div>
            </div>
            <div class="stat">
                <div class="stat-num">{len([d for d in dispositivos if '10 Gbps' in d.get('velocidad', '')])}</div>
                <div class="stat-label">⚡ 10 Gbps</div>
            </div>
            <div class="stat">
                <div class="stat-num">{len([d for d in dispositivos if '1 Gbps' in d.get('velocidad', '')])}</div>
                <div class="stat-label">⚡ 1 Gbps</div>
            </div>
            <div class="stat">
                <div class="stat-num">{len(vendors_count)}</div>
                <div class="stat-label">🏭 Fabricantes</div>
            </div>
        </div>

        <div class="highlight-box">
            <h4>🌐 Infraestructura de Red Principal</h4>
            <p style="margin-bottom: 10px;">
                <strong>Gateway Principal:</strong>
                <span class="badge" style="background: #1e40af; color: white;">{next((d['vendor'] for d in dispositivos if d.get('tipo') == 'gateway'), 'N/A')}</span>
                <span class="badge" style="background: #059669; color: white;">{next((d.get('velocidad', 'N/A') for d in dispositivos if d.get('tipo') == 'gateway'), 'N/A')}</span>
            </p>
            <p style="margin-bottom: 10px;">
                <strong>Infraestructura de Red:</strong>
                <span class="badge" style="background: #0c4a6e; color: white;">🔶 {len([d for d in dispositivos if d.get('tipo') == 'router'])} Routers</span>
                <span class="badge" style="background: #10b981; color: white;">⬣ {len([d for d in dispositivos if d.get('tipo') == 'switch'])} Switches</span>
                <span class="badge" style="background: #f59e0b; color: white;">🖥️ {len([d for d in dispositivos if d.get('tipo') == 'server'])} Servidores</span>
            </p>
            <p>
                <strong>Red:</strong> {red.get('rango', 'N/A')} ·
                <strong>Velocidad:</strong> {vel.get('download', 'N/A')} ↓ / {vel.get('upload', 'N/A')} ↑ ·
                <strong>Latencia:</strong> {vel.get('ping_ms', 'N/A')}
            </p>
        </div>

        <div class="section">
            <h2 class="section-title">🗺️ Topología de Red - Vista Dual</h2>

            <div class="tabs">
                <button class="tab active" onclick="switchView('mesh', this)">🔷 Vista Malla Completa</button>
                <button class="tab" onclick="switchView('blocks', this)">🧱 Vista Árbol</button>
                <button class="tab" onclick="switchView('diagnostico', this)">📋 Diagnóstico</button>
                <button class="tab" onclick="switchView('metricas', this)">📈 Métricas Ejecutivas</button>
            </div>

            <div class="legend">
                <div class="legend-item">
                    <img src="network-icons/conectividad/router.svg" style="width: 28px; height: 28px; margin-right: 8px; vertical-align: middle;">
                    <span style="font-weight: 600; color: #1e40af;">Gateway Principal</span>
                </div>
                <div class="legend-item">
                    <img src="network-icons/conectividad/router.svg" style="width: 28px; height: 28px; margin-right: 8px; vertical-align: middle; filter: hue-rotate(30deg);">
                    <span style="font-weight: 600; color: #0c4a6e;">Routers 🔶</span>
                </div>
                <div class="legend-item">
                    <img src="network-icons/seguridad/firewall.svg" style="width: 28px; height: 28px; margin-right: 8px; vertical-align: middle;">
                    <span style="font-weight: 600; color: #dc2626;">Firewall</span>
                </div>
                <div class="legend-item">
                    <img src="network-icons/conectividad/switch.svg" style="width: 28px; height: 28px; margin-right: 8px; vertical-align: middle;">
                    <span style="font-weight: 600; color: #10b981;">Switches</span>
                </div>
                <div class="legend-item">
                    <img src="network-icons/servidores/servidor.svg" style="width: 28px; height: 28px; margin-right: 8px; vertical-align: middle;">
                    <span style="font-weight: 600; color: #f59e0b;">Servidores</span>
                </div>
                <div class="legend-item">
                    <img src="network-icons/terminales/pc.svg" style="width: 28px; height: 28px; margin-right: 8px; vertical-align: middle;">
                    <span style="font-weight: 600; color: #6b7280;">Workstations</span>
                </div>
                <div class="legend-item">
                    <img src="network-icons/terminales/laptop.svg" style="width: 28px; height: 28px; margin-right: 8px; vertical-align: middle;">
                    <span style="font-weight: 600; color: #8b5cf6;">Laptops</span>
                </div>
                <div class="legend-item">
                    <img src="network-icons/terminales/impresora.svg" style="width: 28px; height: 28px; margin-right: 8px; vertical-align: middle;">
                    <span style="font-weight: 600; color: #ec4899;">Impresoras</span>
                </div>
            </div>

            <!-- Barra de Búsqueda -->
            <div class="search-container">
                <div class="search-box">
                    <input type="text"
                           id="searchInput"
                           class="search-input"
                           placeholder="🔍 Buscar por IP, MAC, Hostname, Vendor..."
                           onkeyup="filterDevices()">
                    <div class="search-filters">
                        <button class="filter-btn active" onclick="filterByType('all')">Todos</button>
                        <button class="filter-btn" onclick="filterByType('router')">Routers</button>
                        <button class="filter-btn" onclick="filterByType('switch')">Switches</button>
                        <button class="filter-btn" onclick="filterByType('server')">Servidores</button>
                        <button class="filter-btn" onclick="filterByType('workstation')">PCs</button>
                        <button class="filter-btn" onclick="filterByType('slow')">⚠️ Lentos</button>
                    </div>
                </div>
                <div id="searchResults" class="search-results" style="display: none;">
                    Encontrados: <span class="highlight">0</span> dispositivos
                </div>
            </div>

            <!-- Vista 1: Malla Completa -->
            <div id="view-mesh" class="view active">
                <div id="topology-mesh" class="topology-container"></div>
                <p style="text-align: center; margin-top: 15px; color: #64748b; font-size: 0.95em;">
                    💡 Muestra: Tipo + IP + Hostname | Arrastra routers para mover grupos | Click para detalles completos
                </p>
                <div style="text-align: center; margin-top: 10px; padding: 12px; background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border-radius: 8px; border-left: 4px solid #f59e0b;">
                    <strong style="color: #92400e;">⚡ Código de Velocidad (borde de nodos):</strong>
                    <span style="color: #059669; font-weight: bold;">● Verde</span> = 10 Gbps (Rápido) ·
                    <span style="color: #0ea5e9; font-weight: bold;">● Azul</span> = 1 Gbps (Normal) ·
                    <span style="color: #f59e0b; font-weight: bold;">● Naranja</span> = 100 Mbps (Lento) ⚠️ ·
                    <span style="color: #ef4444; font-weight: bold;">● Rojo</span> = <100 Mbps (Muy Lento) 🔴
                </div>
            </div>

            <!-- Vista 2: Bloques expandibles -->
            <div id="view-blocks" class="view">
                <div id="topology-blocks" style="max-height: 750px; overflow-y: auto; padding: 20px; background: white; border: 2px solid #e2e8f0; border-radius: 10px;">
                    <div class="tree" id="tree-root"></div>
                </div>
                <p style="text-align: center; margin-top: 15px; color: #64748b; font-size: 0.95em;">
                    💡 Click en los nodos para expandir/colapsar | Vista de árbol jerárquico
                </p>
            </div>

            <!-- Vista 3: Diagnóstico -->
            <div id="view-diagnostico" class="view">
                <div style="max-height: 750px; overflow-y: auto; padding: 25px; background: white; border: 2px solid #e2e8f0; border-radius: 10px;">

                    <!-- Header del diagnóstico -->
                    <div style="text-align: center; margin-bottom: 30px; padding: 20px; background: linear-gradient(135deg, #1e40af 0%, #0ea5e9 100%); border-radius: 10px; color: white;">
                        <h2 style="margin: 0 0 10px 0; font-size: 2em;">📋 Diagnóstico de Red</h2>
                        <p style="margin: 0; font-size: 1.1em; opacity: 0.95;">{empresa['nombre']} - {red['rango']}</p>
                        <div style="margin-top: 15px; font-size: 3em; font-weight: bold;">
                            {diagnostico['health_score']}%
                        </div>
                        <div style="font-size: 0.9em;">Salud General de la Red</div>
                    </div>

                    <!-- Resumen Ejecutivo -->
                    <div style="margin-bottom: 25px; padding: 20px; background: #f8fafc; border-left: 4px solid #0ea5e9; border-radius: 8px;">
                        <h3 style="margin: 0 0 15px 0; color: #1e293b;">📊 Resumen Ejecutivo</h3>
                        <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;">
                            <div>
                                <div style="font-size: 2em; font-weight: bold; color: #0ea5e9;">{len(dispositivos)}</div>
                                <div style="color: #64748b; font-size: 0.9em;">Total Dispositivos</div>
                            </div>
                            <div>
                                <div style="font-size: 2em; font-weight: bold; color: #10b981;">{diagnostico['speeds']['10 Gbps'] + diagnostico['speeds']['1 Gbps']}</div>
                                <div style="color: #64748b; font-size: 0.9em;">Velocidad Óptima (≥1G)</div>
                            </div>
                            <div>
                                <div style="font-size: 2em; font-weight: bold; color: #{'ef4444' if len(diagnostico['issues']['critico']) > 0 else '059669'}">{len(diagnostico['issues']['critico']) + len(diagnostico['issues']['advertencia'])}</div>
                                <div style="color: #64748b; font-size: 0.9em;">Problemas Detectados</div>
                            </div>
                        </div>
                    </div>

                    <!-- Problemas Críticos -->
                    {f'''<div style="margin-bottom: 25px;">
                        <h3 style="margin: 0 0 15px 0; color: #dc2626;">🔴 PROBLEMAS CRÍTICOS ({len(diagnostico['issues']['critico'])})</h3>
                        {''.join([f"""
                        <div style="margin-bottom: 15px; padding: 15px; background: #fef2f2; border-left: 4px solid #dc2626; border-radius: 8px;">
                            <div style="font-weight: bold; color: #991b1b; margin-bottom: 8px;">{issue['titulo']}</div>
                            <div style="color: #64748b; margin-bottom: 8px;">{issue['descripcion']}</div>
                            <div style="color: #dc2626; font-weight: 600; margin-bottom: 8px;">Impacto: {issue['impacto']}</div>
                            <div style="background: white; padding: 10px; border-radius: 6px; border-left: 3px solid #dc2626;">
                                <strong>✓ Acción:</strong> {issue['accion']}
                            </div>
                        </div>
                        """ for issue in diagnostico['issues']['critico']])}
                    </div>''' if len(diagnostico['issues']['critico']) > 0 else ''}

                    <!-- Advertencias -->
                    {f'''<div style="margin-bottom: 25px;">
                        <h3 style="margin: 0 0 15px 0; color: #f59e0b;">⚠️ ADVERTENCIAS ({len(diagnostico['issues']['advertencia'])})</h3>
                        {''.join([f"""
                        <div style="margin-bottom: 15px; padding: 15px; background: #fffbeb; border-left: 4px solid #f59e0b; border-radius: 8px;">
                            <div style="font-weight: bold; color: #92400e; margin-bottom: 8px;">{issue['titulo']}</div>
                            <div style="color: #64748b; margin-bottom: 8px;">{issue['descripcion']}</div>
                            <div style="color: #f59e0b; font-weight: 600; margin-bottom: 8px;">Impacto: {issue['impacto']}</div>
                            <div style="background: white; padding: 10px; border-radius: 6px; border-left: 3px solid #f59e0b;">
                                <strong>✓ Acción:</strong> {issue['accion']}
                            </div>
                        </div>
                        """ for issue in diagnostico['issues']['advertencia']])}
                    </div>''' if len(diagnostico['issues']['advertencia']) > 0 else ''}

                    <!-- Recomendaciones -->
                    {f'''<div style="margin-bottom: 25px;">
                        <h3 style="margin: 0 0 15px 0; color: #0ea5e9;">💡 RECOMENDACIONES ({len(diagnostico['issues']['recomendacion'])})</h3>
                        {''.join([f"""
                        <div style="margin-bottom: 15px; padding: 15px; background: #f0f9ff; border-left: 4px solid #0ea5e9; border-radius: 8px;">
                            <div style="font-weight: bold; color: #075985; margin-bottom: 8px;">{issue['titulo']}</div>
                            <div style="color: #64748b; margin-bottom: 8px;">{issue['descripcion']}</div>
                            <div style="color: #0ea5e9; font-weight: 600; margin-bottom: 8px;">Impacto: {issue['impacto']}</div>
                            <div style="background: white; padding: 10px; border-radius: 6px; border-left: 3px solid #0ea5e9;">
                                <strong>✓ Acción:</strong> {issue['accion']}
                            </div>
                        </div>
                        """ for issue in diagnostico['issues']['recomendacion']])}
                    </div>''' if len(diagnostico['issues']['recomendacion']) > 0 else ''}

                    <!-- Módems con SLA Incumplido -->
                    {f'''<div style="margin-bottom: 25px;">
                        <h3 style="margin: 0 0 15px 0; color: #dc2626;">📡 MÓDEMS - ANÁLISIS DE SLA ({len(diagnostico['modems_incumplen_sla'])} de {diagnostico['total_modems_con_sla']} NO CUMPLEN)</h3>
                        <div style="background: #fef2f2; padding: 15px; border-radius: 8px; border: 2px solid #dc2626;">
                            <table style="width: 100%; border-collapse: collapse;">
                                <thead>
                                    <tr style="border-bottom: 2px solid #dc2626;">
                                        <th style="text-align: left; padding: 8px;">Módem</th>
                                        <th style="text-align: left; padding: 8px;">Área</th>
                                        <th style="text-align: center; padding: 8px;">SLA Contratado</th>
                                        <th style="text-align: center; padding: 8px;">Velocidad Real</th>
                                        <th style="text-align: center; padding: 8px;">Cumplimiento</th>
                                        <th style="text-align: center; padding: 8px;">Estado</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {''.join([f"""
                                    <tr style="border-bottom: 1px solid #fecaca;">
                                        <td style="padding: 8px; font-weight: 600;">{modem['modem_info']}</td>
                                        <td style="padding: 8px;">{modem['area']}</td>
                                        <td style="padding: 8px; text-align: center; font-weight: bold; color: #0ea5e9;">{modem['sla_contratado']} Mbps</td>
                                        <td style="padding: 8px; text-align: center; font-weight: bold; color: #{'10b981' if modem['cumplimiento'] >= 90 else 'f59e0b' if modem['cumplimiento'] >= 70 else 'dc2626'};">{modem['velocidad_real']} Mbps</td>
                                        <td style="padding: 8px; text-align: center; font-weight: bold; font-size: 1.1em; color: #{'10b981' if modem['cumplimiento'] >= 90 else 'f59e0b' if modem['cumplimiento'] >= 70 else 'dc2626'};">{modem['cumplimiento']:.1f}%</td>
                                        <td style="padding: 8px; text-align: center;">
                                            <span style="padding: 4px 12px; background: #{'dcfce7' if modem['cumplimiento'] >= 90 else 'fef3c7' if modem['cumplimiento'] >= 70 else 'fecaca'}; border: 2px solid #{'10b981' if modem['cumplimiento'] >= 90 else 'f59e0b' if modem['cumplimiento'] >= 70 else 'dc2626'}; border-radius: 4px; font-size: 0.85em; font-weight: 700; color: #{'166534' if modem['cumplimiento'] >= 90 else '92400e' if modem['cumplimiento'] >= 70 else '991b1b'};">
                                                {'✅ OK' if modem['cumplimiento'] >= 90 else '⚠️ BAJO' if modem['cumplimiento'] >= 70 else '❌ CRÍTICO'}
                                            </span>
                                        </td>
                                    </tr>
                                    """ for modem in diagnostico['modems_incumplen_sla']])}
                                </tbody>
                            </table>
                            <div style="margin-top: 15px; padding: 12px; background: white; border-radius: 6px; border-left: 4px solid #dc2626;">
                                <strong style="color: #991b1b;">⚡ ACCIÓN REQUERIDA:</strong>
                                <p style="margin: 8px 0 0 0; color: #64748b;">
                                    Contactar a proveedor (Telmex/otro) para reportar incumplimiento de SLA.
                                    Los módems marcados en ROJO requieren atención inmediata - posible reclamo contractual.
                                </p>
                            </div>
                        </div>
                    </div>''' if len(diagnostico['modems_incumplen_sla']) > 0 and diagnostico['total_modems_con_sla'] > 0 else (
                        f'''<div style="margin-bottom: 25px; padding: 20px; background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); border: 2px solid #10b981; border-radius: 8px;">
                            <h3 style="color: #16a34a; margin: 0 0 10px 0;">✅ MÓDEMS - CUMPLIMIENTO DE SLA PERFECTO</h3>
                            <p style="color: #15803d; margin: 0;">
                                <strong>{diagnostico['total_modems_con_sla']} módem(es)</strong> monitoreados están cumpliendo o superando el SLA contratado (≥90%).
                            </p>
                        </div>''' if diagnostico['total_modems_con_sla'] > 0 else ''
                    )}

                    <!-- Dispositivos Lentos -->
                    {f'''<div style="margin-bottom: 25px;">
                        <h3 style="margin: 0 0 15px 0; color: #f59e0b;">🐌 DISPOSITIVOS QUE NECESITAN ATENCIÓN ({len(diagnostico['slow_nodes'])})</h3>
                        <div style="background: #fffbeb; padding: 15px; border-radius: 8px; border: 1px solid #fbbf24;">
                            <table style="width: 100%; border-collapse: collapse;">
                                <thead>
                                    <tr style="border-bottom: 2px solid #fbbf24;">
                                        <th style="text-align: left; padding: 8px;">Hostname</th>
                                        <th style="text-align: left; padding: 8px;">IP</th>
                                        <th style="text-align: left; padding: 8px;">Tipo</th>
                                        <th style="text-align: left; padding: 8px;">Velocidad</th>
                                        <th style="text-align: left; padding: 8px;">Prioridad</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {''.join([f"""
                                    <tr style="border-bottom: 1px solid #fde68a;">
                                        <td style="padding: 8px;">{node['hostname']}</td>
                                        <td style="padding: 8px; font-family: monospace;">{node['ip']}</td>
                                        <td style="padding: 8px;">{node['tipo'].upper()}</td>
                                        <td style="padding: 8px; font-weight: bold; color: #{'ef4444' if '<100' in node.get('velocidad', '') or '10 Mbps' in node.get('velocidad', '') else 'f59e0b'};">{node.get('velocidad', 'N/A')}</td>
                                        <td style="padding: 8px;">
                                            <span style="padding: 4px 8px; background: #{'fecaca' if '<100' in node.get('velocidad', '') or '10 Mbps' in node.get('velocidad', '') else 'fed7aa'}; border-radius: 4px; font-size: 0.85em; font-weight: 600;">
                                                {'ALTA' if '<100' in node.get('velocidad', '') or '10 Mbps' in node.get('velocidad', '') else 'MEDIA'}
                                            </span>
                                        </td>
                                    </tr>
                                    """ for node in diagnostico['slow_nodes'][:20]])}
                                </tbody>
                            </table>
                            {f'<p style="margin-top: 10px; color: #92400e; font-size: 0.9em;">Mostrando 20 de {len(diagnostico["slow_nodes"])} dispositivos lentos</p>' if len(diagnostico['slow_nodes']) > 20 else ''}
                        </div>
                    </div>''' if len(diagnostico['slow_nodes']) > 0 else '<div style="padding: 20px; background: #f0fdf4; border: 2px solid #86efac; border-radius: 8px; text-align: center;"><h3 style="color: #16a34a; margin: 0;">✅ ¡Excelente! No hay dispositivos lentos en la red</h3><p style="color: #15803d; margin: 10px 0 0 0;">Todos los dispositivos operan a 1 Gbps o más</p></div>'}

                    <!-- Plan de Acción -->
                    <div style="margin-top: 30px; padding: 20px; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-radius: 10px; border: 2px solid #0ea5e9;">
                        <h3 style="margin: 0 0 15px 0; color: #075985;">🎯 PLAN DE ACCIÓN RECOMENDADO</h3>

                        <div style="margin-bottom: 15px;">
                            <div style="font-weight: bold; color: #dc2626; margin-bottom: 8px;">⚡ INMEDIATO (0-1 semana):</div>
                            <ul style="margin: 0; padding-left: 20px; color: #1e293b;">
                                {f'<li>Implementar firewall perimetral</li>' if any('firewall' in str(i).lower() for i in diagnostico['issues']['critico']) else ''}
                                {f'<li>Actualizar {len([n for n in diagnostico["slow_nodes"] if "<100" in n.get("velocidad", "")])} dispositivos críticos (<100 Mbps)</li>' if len([n for n in diagnostico['slow_nodes'] if '<100' in n.get('velocidad', '')]) > 0 else ''}
                                {'<li>No hay acciones inmediatas críticas ✅</li>' if len(diagnostico['issues']['critico']) == 0 else ''}
                            </ul>
                        </div>

                        <div style="margin-bottom: 15px;">
                            <div style="font-weight: bold; color: #f59e0b; margin-bottom: 8px;">📅 CORTO PLAZO (1-3 meses):</div>
                            <ul style="margin: 0; padding-left: 20px; color: #1e293b;">
                                {f'<li>Evaluar reemplazo de routers por switches</li>' if any('router' in str(i).lower() for i in diagnostico['issues']['advertencia']) else ''}
                                {f'<li>Planificar upgrade de {len(diagnostico["slow_nodes"])} dispositivos a 1 Gbps</li>' if len(diagnostico['slow_nodes']) > 0 else ''}
                                {'<li>Mantener monitoreo de rendimiento</li>' if len(diagnostico['issues']['advertencia']) == 0 else ''}
                            </ul>
                        </div>

                        <div>
                            <div style="font-weight: bold; color: #0ea5e9; margin-bottom: 8px;">🚀 LARGO PLAZO (3-12 meses):</div>
                            <ul style="margin: 0; padding-left: 20px; color: #1e293b;">
                                {f'<li>Estandarizar fabricantes (actualmente {diagnostico["vendors_count"]})</li>' if diagnostico['vendors_count'] > 10 else ''}
                                <li>Documentar topología y configuraciones</li>
                                <li>Implementar monitoreo automatizado (SNMP, Grafana)</li>
                                <li>Planificar redundancia en enlaces críticos</li>
                            </ul>
                        </div>
                    </div>

                </div>
            </div>

            <!-- Vista 4: Métricas Ejecutivas -->
            <div id="view-metricas" class="view">
                <div style="max-height: 750px; overflow-y: auto; padding: 25px; background: white; border: 2px solid #e2e8f0; border-radius: 10px;">

                    <!-- Header -->
                    <div style="text-align: center; margin-bottom: 30px; padding: 20px; background: linear-gradient(135deg, #059669 0%, #10b981 100%); border-radius: 10px; color: white;">
                        <h2 style="margin: 0 0 10px 0; font-size: 2em;">📈 Métricas Ejecutivas</h2>
                        <p style="margin: 0; font-size: 1.1em; opacity: 0.95;">Análisis de Negocio - {empresa['nombre']}</p>
                    </div>

                    <!-- Grid de KPIs -->
                    <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; margin-bottom: 30px;">

                        <!-- KPI 1: Inversión Total -->
                        <div style="padding: 25px; background: linear-gradient(135deg, #f0f9ff 0%, #e0f2fe 100%); border-radius: 10px; border-left: 4px solid #0ea5e9;">
                            <div style="display: flex; justify-content: space-between; align-items: start;">
                                <div>
                                    <div style="font-size: 0.9em; color: #64748b; margin-bottom: 8px;">💰 INVERSIÓN TOTAL ESTIMADA</div>
                                    <div style="font-size: 2.5em; font-weight: bold; color: #0ea5e9; margin-bottom: 5px;">
                                        ${diagnostico['costo_hardware']:,} USD
                                    </div>
                                    <div style="font-size: 0.85em; color: #64748b;">
                                        Hardware: ${diagnostico['costo_hardware']:,}
                                    </div>
                                    <div style="font-size: 0.85em; color: #64748b;">
                                        Mantenimiento/año: ${diagnostico['costo_mantenimiento']:,}
                                    </div>
                                </div>
                                <div style="font-size: 3em;">💵</div>
                            </div>
                        </div>

                        <!-- KPI 2: Nivel de Riesgo -->
                        <div style="padding: 25px; background: linear-gradient(135deg, #{'fef2f2' if diagnostico['health_score'] < 60 else 'fef3c7' if diagnostico['health_score'] < 80 else 'f0fdf4'} 0%, #{'fee2e2' if diagnostico['health_score'] < 60 else 'fde68a' if diagnostico['health_score'] < 80 else 'dcfce7'} 100%); border-radius: 10px; border-left: 4px solid #{'dc2626' if diagnostico['health_score'] < 60 else 'f59e0b' if diagnostico['health_score'] < 80 else '10b981'};">
                            <div style="display: flex; justify-content: space-between; align-items: start;">
                                <div style="flex: 1;">
                                    <div style="font-size: 0.9em; color: #64748b; margin-bottom: 8px;">⚠️ NIVEL DE RIESGO</div>
                                    <div style="font-size: 2.5em; font-weight: bold; color: #{'dc2626' if diagnostico['health_score'] < 60 else 'f59e0b' if diagnostico['health_score'] < 80 else '10b981'}; margin-bottom: 5px;">
                                        {'ALTO' if diagnostico['health_score'] < 60 else 'MEDIO' if diagnostico['health_score'] < 80 else 'BAJO'}
                                    </div>
                                    <div style="font-size: 0.85em; color: #64748b;">Score de seguridad: {diagnostico['health_score']}%</div>
                                    <div style="font-size: 0.85em; color: #64748b;">{len(diagnostico['issues']['critico'])} críticos, {len(diagnostico['issues']['advertencia'])} advertencias</div>
                                </div>
                                <div style="font-size: 3em;">{'🔴' if diagnostico['health_score'] < 60 else '🟡' if diagnostico['health_score'] < 80 else '🟢'}</div>
                            </div>
                        </div>

                        <!-- KPI 3: ROI de Mejoras -->
                        <div style="padding: 25px; background: linear-gradient(135deg, #f0fdf4 0%, #dcfce7 100%); border-radius: 10px; border-left: 4px solid #10b981;">
                            <div style="display: flex; justify-content: space-between; align-items: start;">
                                <div>
                                    <div style="font-size: 0.9em; color: #64748b; margin-bottom: 8px;">📉 ROI DE MEJORAS SUGERIDAS</div>
                                    <div style="font-size: 2.5em; font-weight: bold; color: #10b981; margin-bottom: 5px;">
                                        {diagnostico['roi_porcentaje'] if diagnostico['roi_porcentaje'] > 0 else 'N/A'}{'%' if diagnostico['roi_porcentaje'] > 0 else ''}
                                    </div>
                                    <div style="font-size: 0.85em; color: #64748b;">
                                        Invertir: ${diagnostico['costo_mejoras']:,} USD
                                    </div>
                                    <div style="font-size: 0.85em; color: #64748b;">
                                        Ahorrar: ${diagnostico['ahorro_anual']:,} USD/año
                                    </div>
                                </div>
                                <div style="font-size: 3em;">📊</div>
                            </div>
                        </div>

                        <!-- KPI 4: SLA / Uptime -->
                        <div style="padding: 25px; background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%); border-radius: 10px; border-left: 4px solid #f59e0b;">
                            <div style="display: flex; justify-content: space-between; align-items: start;">
                                <div>
                                    <div style="font-size: 0.9em; color: #64748b; margin-bottom: 8px;">⏱️ SLA / UPTIME ESTIMADO</div>
                                    <div style="font-size: 2.5em; font-weight: bold; color: #f59e0b; margin-bottom: 5px;">
                                        {diagnostico['uptime_estimado']:.1f}%
                                    </div>
                                    <div style="font-size: 0.85em; color: #64748b;">
                                        Esperado: 99.5% (industria)
                                    </div>
                                    <div style="font-size: 0.85em; color: #64748b;">
                                        {'⚠️ Pérdidas: ~$2,400 USD/mes' if diagnostico['uptime_estimado'] < 99 else '✅ Dentro de SLA'}
                                    </div>
                                </div>
                                <div style="font-size: 3em;">⏰</div>
                            </div>
                        </div>

                    </div>

                    <!-- Prioridades de Inversión -->
                    <div style="margin-top: 30px; padding: 25px; background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%); border-radius: 10px; border: 2px solid #64748b;">
                        <h3 style="margin: 0 0 20px 0; color: #1e293b;">🎯 PRIORIDADES DE INVERSIÓN</h3>

                        <div style="display: grid; gap: 15px;">
                            {f'''
                            <div style="padding: 15px; background: white; border-radius: 8px; border-left: 4px solid #dc2626;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <div style="font-weight: bold; color: #dc2626; margin-bottom: 5px;">1. Firewall Perimetral (CRÍTICO)</div>
                                        <div style="font-size: 0.9em; color: #64748b;">Protección esencial contra amenazas externas</div>
                                    </div>
                                    <div style="font-size: 1.3em; font-weight: bold; color: #dc2626;">$8,500</div>
                                </div>
                            </div>
                            ''' if len([i for i in diagnostico['issues']['critico'] if 'firewall' in str(i).lower()]) > 0 else ''}

                            {f'''
                            <div style="padding: 15px; background: white; border-radius: 8px; border-left: 4px solid #f59e0b;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <div style="font-weight: bold; color: #f59e0b; margin-bottom: 5px;">2. Upgrade Switches (RECOMENDADO)</div>
                                        <div style="font-size: 0.9em; color: #64748b;">Reemplazar routers por switches administrables</div>
                                    </div>
                                    <div style="font-size: 1.3em; font-weight: bold; color: #f59e0b;">$15,000</div>
                                </div>
                            </div>
                            ''' if len([d for d in dispositivos if d.get('tipo') == 'router']) > 5 else ''}

                            <div style="padding: 15px; background: white; border-radius: 8px; border-left: 4px solid #0ea5e9;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <div style="font-weight: bold; color: #0ea5e9; margin-bottom: 5px;">{'3' if len([i for i in diagnostico['issues']['critico'] if 'firewall' in str(i).lower()]) > 0 else '2'}. Sistema de Monitoreo (FUTURO)</div>
                                        <div style="font-size: 0.9em; color: #64748b;">SNMP, Grafana, alertas automatizadas</div>
                                    </div>
                                    <div style="font-size: 1.3em; font-weight: bold; color: #0ea5e9;">$4,500</div>
                                </div>
                            </div>

                            <div style="padding: 15px; background: white; border-radius: 8px; border-left: 4px solid #10b981;">
                                <div style="display: flex; justify-content: space-between; align-items: center;">
                                    <div>
                                        <div style="font-weight: bold; color: #10b981; margin-bottom: 5px;">{'4' if len([i for i in diagnostico['issues']['critico'] if 'firewall' in str(i).lower()]) > 0 else '3'}. Redundancia y Backup</div>
                                        <div style="font-size: 0.9em; color: #64748b;">NAS, enlaces redundantes, UPS</div>
                                    </div>
                                    <div style="font-size: 1.3em; font-weight: bold; color: #10b981;">$6,000</div>
                                </div>
                            </div>
                        </div>

                        <!-- Resumen Total -->
                        <div style="margin-top: 20px; padding: 15px; background: #1e293b; color: white; border-radius: 8px;">
                            <div style="display: flex; justify-content: space-between; align-items: center;">
                                <div style="font-size: 1.2em; font-weight: bold;">INVERSIÓN TOTAL SUGERIDA</div>
                                <div style="font-size: 1.8em; font-weight: bold;">
                                    ${diagnostico['inversion_total']:,} USD
                                </div>
                            </div>
                            <div style="font-size: 0.9em; opacity: 0.9; margin-top: 8px;">
                                Retorno estimado en 12-18 meses con mejora en seguridad, rendimiento y reducción de downtime
                            </div>
                        </div>
                    </div>

                </div>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">📡 Configuración de Red</h2>
            <div class="network-info">
                <p><strong>🌐 Rango:</strong> {red.get('rango', 'N/A')}</p>
                <p><strong>🚪 Gateway:</strong> {red.get('gateway', 'N/A')}</p>
                <p><strong>💻 IP Local:</strong> {red.get('ip_local', 'N/A')}</p>
                <p><strong>⚡ Velocidad Total:</strong> ↓ {vel.get('download', 'N/A')} / ↑ {vel.get('upload', 'N/A')}</p>
                <p><strong>📶 Ping:</strong> {vel.get('ping_ms', 'N/A')}</p>
                <p><strong>📊 Ancho Banda Total:</strong> {stats.get('total_bandwidth_mbps', 0)} Mbps</p>
            </div>
        </div>

        <div class="section">
            <h2 class="section-title">📊 Análisis Estadístico Completo</h2>
            <div class="charts-grid">
                <div class="chart-box">
                    <div class="chart-container">
                        <canvas id="typeChart"></canvas>
                    </div>
                </div>
                <div class="chart-box">
                    <div class="chart-container">
                        <canvas id="speedChart"></canvas>
                    </div>
                </div>
                <div class="chart-box">
                    <div class="chart-container">
                        <canvas id="terminalChart"></canvas>
                    </div>
                </div>
                <div class="chart-box">
                    <div class="chart-container">
                        <canvas id="vendorChart"></canvas>
                    </div>
                </div>
                <div class="chart-box">
                    <div class="chart-container">
                        <canvas id="deptChart"></canvas>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Modal para información del dispositivo -->
    <div id="deviceModal" class="modal">
        <div class="modal-content">
            <div class="modal-header">
                <h2 id="modal-title">Información del Dispositivo</h2>
                <button class="close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body">
                <div id="modal-icon" class="device-icon-large"></div>
                <div id="modal-info" class="info-grid"></div>
            </div>
        </div>
    </div>

    <script>
        // Verificar que vis-network esté cargado
        if (typeof vis === 'undefined') {{
            alert('Error: La biblioteca vis-network no se pudo cargar. Verifica tu conexión a internet.');
            console.error('vis-network library not loaded');
        }}

        const nodesData = {json.dumps(nodos)};
        const edgesData = {json.dumps(edges)};
        const dispositivosData = {json.dumps(dispositivos)};
        const areasConfig = {json.dumps(areas_config)};

        // Funciones del modal
        function closeModal() {{
            document.getElementById('deviceModal').style.display = 'none';
        }}

        function showDeviceInfo(deviceId) {{
            const device = dispositivosData[deviceId];
            if (!device) return;

            const modal = document.getElementById('deviceModal');
            const modalTitle = document.getElementById('modal-title');
            const modalIcon = document.getElementById('modal-icon');
            const modalInfo = document.getElementById('modal-info');

            const colorMap = {{
                'gateway': '#1e40af',
                'firewall': '#dc2626',
                'modem': '#0ea5e9',
                'switch': '#10b981',
                'server': '#f59e0b',
                'workstation': '#6b7280',
                'laptop': '#8b5cf6',
                'printer': '#ec4899',
                'camera': '#ef4444',
                'iot': '#14b8a6'
            }};

            const symbolMap = {{
                'gateway': '◈',
                'firewall': '🛡️',
                'modem': '📡',
                'switch': '⬣',
                'server': '▮',
                'workstation': '●',
                'laptop': '●',
                'printer': '⊞',
                'camera': '◉',
                'iot': '○'
            }};

            const color = colorMap[device.tipo] || '#64748b';
            const symbol = symbolMap[device.tipo] || '●';

            modalTitle.textContent = device.hostname || device.ip;
            modalIcon.style.background = color;
            modalIcon.style.color = 'white';
            modalIcon.textContent = symbol;

            const fields = [
                {{ label: '📍 Dirección IP', value: device.ip }},
                {{ label: '🏷️ Hostname', value: device.hostname || 'N/A' }},
                {{ label: '🔧 Tipo', value: device.tipo ? device.tipo.toUpperCase() : 'N/A' }},
                {{ label: '🏭 Fabricante', value: device.vendor || 'N/A' }},
                {{ label: '🏢 Departamento', value: device.departamento || 'N/A' }},
                {{ label: '📶 MAC Address', value: device.mac || 'N/A' }},
                {{ label: '⚡ Velocidad', value: device.velocidad || 'N/A' }},
                {{ label: '⏱️ Latencia', value: device.latencia ? device.latencia + ' ms' : 'N/A' }},
                {{ label: '🔗 Padre', value: device.padre || 'Gateway Principal' }},
                {{ label: '🛠️ Servicios', value: device.servicios ? device.servicios.join(', ') : 'N/A' }}
            ];

            let html = fields.map(f => `
                <div class="info-label">${{f.label}}</div>
                <div class="info-value">${{f.value}}</div>
            `).join('');

            // Agregar información de área personalizada si existe
            const areaInfo = areasConfig[device.ip];
            if (areaInfo) {{
                html += '<div style="margin-top: 20px; padding-top: 15px; border-top: 2px solid #e2e8f0;"></div>';
                html += '<div style="font-weight: 700; color: #1e40af; margin-bottom: 10px; font-size: 1.1em;">📍 Ubicación y Detalles</div>';

                Object.keys(areaInfo).forEach(key => {{
                    const keyFormatted = key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
                    html += `
                        <div class="info-label">${{keyFormatted}}</div>
                        <div class="info-value">${{areaInfo[key]}}</div>
                    `;
                }});
            }}

            modalInfo.innerHTML = html;
            modal.style.display = 'block';
        }}

        // Cerrar modal al hacer click fuera
        window.onclick = function(event) {{
            const modal = document.getElementById('deviceModal');
            if (event.target === modal) {{
                modal.style.display = 'none';
            }}
        }}

        // Cerrar modal con ESC
        document.addEventListener('keydown', function(event) {{
            if (event.key === 'Escape') {{
                closeModal();
            }}
        }});

        // Función para cambiar de vista
        function switchView(viewName, clickedButton) {{
            document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));

            document.getElementById('view-' + viewName).classList.add('active');
            if (clickedButton) {{
                clickedButton.classList.add('active');
            }}

            // Inicializar vista de bloques si no está inicializada
            if (viewName === 'blocks' && !window.blocksInitialized) {{
                initBlocks();
            }}

            // Re-fit network cuando se cambia a vista malla
            if (viewName === 'mesh' && networkMesh) {{
                setTimeout(() => networkMesh.fit(), 100);
            }}
        }}

        // Variables globales para búsqueda
        let currentFilter = 'all';
        let searchTerm = '';

        // Función de búsqueda/filtrado
        function filterDevices() {{
            searchTerm = document.getElementById('searchInput').value.toLowerCase();
            applyFilters();
        }}

        function filterByType(type) {{
            currentFilter = type;

            // Actualizar botones activos
            document.querySelectorAll('.filter-btn').forEach(btn => {{
                btn.classList.remove('active');
            }});
            event.target.classList.add('active');

            applyFilters();
        }}

        function applyFilters() {{
            let matchedNodes = [];

            dispositivosData.forEach((device, idx) => {{
                let matches = true;

                // Filtro por búsqueda de texto
                if (searchTerm) {{
                    const searchableText = [
                        device.ip || '',
                        device.hostname || '',
                        device.mac || '',
                        device.vendor || '',
                        device.tipo || '',
                        device.departamento || ''
                    ].join(' ').toLowerCase();

                    matches = searchableText.includes(searchTerm);
                }}

                // Filtro por tipo
                if (matches && currentFilter !== 'all') {{
                    if (currentFilter === 'slow') {{
                        // Filtrar nodos lentos (100 Mbps o menos)
                        const vel = device.velocidad || '';
                        matches = vel.includes('100 Mbps') ||
                                 (!vel.includes('1 Gbps') && !vel.includes('10 Gbps'));
                    }} else {{
                        matches = device.tipo === currentFilter;
                    }}
                }}

                if (matches) {{
                    matchedNodes.push(idx);
                }}
            }});

            // Mostrar resultados
            const resultsDiv = document.getElementById('searchResults');
            const resultsCount = matchedNodes.length;

            if (searchTerm || currentFilter !== 'all') {{
                resultsDiv.style.display = 'block';
                resultsDiv.innerHTML = `Encontrados: <span class="highlight">${{resultsCount}}</span> de ${{dispositivosData.length}} dispositivos`;
            }} else {{
                resultsDiv.style.display = 'none';
            }}

            // Resaltar nodos en el grafo
            highlightNodes(matchedNodes);
        }}

        function highlightNodes(matchedIndices) {{
            if (!networkMesh) return;

            const allNodeIds = nodesMesh.getIds();

            if (matchedIndices.length === 0 || (searchTerm === '' && currentFilter === 'all')) {{
                // Restaurar todos los nodos
                allNodeIds.forEach(id => {{
                    nodesMesh.update({{
                        id: id,
                        opacity: 1,
                        font: {{ size: nodesData[id].font?.size || 14 }}
                    }});
                }});

                // Restaurar todas las aristas
                edgesMesh.getIds().forEach(id => {{
                    edgesMesh.update({{ id: id, color: {{ opacity: 1 }} }});
                }});
            }} else {{
                // Atenuar nodos no coincidentes
                allNodeIds.forEach(id => {{
                    const isMatch = matchedIndices.includes(id);
                    nodesMesh.update({{
                        id: id,
                        opacity: isMatch ? 1 : 0.15,
                        font: {{ size: isMatch ? (nodesData[id].font?.size || 14) + 2 : (nodesData[id].font?.size || 14) }}
                    }});
                }});

                // Atenuar aristas no conectadas a nodos coincidentes
                edgesMesh.getIds().forEach(id => {{
                    const edge = edgesMesh.get(id);
                    const isConnected = matchedIndices.includes(edge.from) || matchedIndices.includes(edge.to);
                    edgesMesh.update({{
                        id: id,
                        color: {{ opacity: isConnected ? 0.8 : 0.1 }}
                    }});
                }});

                // Centrar en nodos coincidentes si hay pocos
                if (matchedIndices.length > 0 && matchedIndices.length <= 5) {{
                    networkMesh.fit({{
                        nodes: matchedIndices,
                        animation: {{ duration: 500 }}
                    }});
                }}
            }}
        }}

        // Vista 1: Malla (Force-directed)
        const nodesMesh = new vis.DataSet(nodesData);
        const edgesMesh = new vis.DataSet(edgesData);

        const containerMesh = document.getElementById('topology-mesh');
        const dataMesh = {{ nodes: nodesMesh, edges: edgesMesh }};

        const optionsMesh = {{
            layout: {{
                randomSeed: 42
            }},
            physics: {{
                enabled: true,
                barnesHut: {{
                    gravitationalConstant: -50000,
                    centralGravity: 0.05,
                    springLength: 280,
                    springConstant: 0.02,
                    damping: 0.4,
                    avoidOverlap: 0.8
                }},
                maxVelocity: 50,
                minVelocity: 0.75,
                stabilization: {{
                    enabled: true,
                    iterations: 400,
                    updateInterval: 25
                }}
            }},
            interaction: {{
                hover: true,
                tooltipDelay: 100,
                navigationButtons: true,
                keyboard: true,
                zoomView: true,
                dragView: true
            }},
            nodes: {{
                shadow: {{
                    enabled: true,
                    color: 'rgba(0,0,0,0.2)',
                    size: 8,
                    x: 3,
                    y: 3
                }}
            }},
            edges: {{
                smooth: {{
                    enabled: true,
                    type: 'continuous',
                    roundness: 0.5
                }},
                shadow: {{
                    enabled: true,
                    color: 'rgba(0,0,0,0.15)',
                    size: 5
                }}
            }}
        }};

        const networkMesh = new vis.Network(containerMesh, dataMesh, optionsMesh);

        networkMesh.on('stabilizationIterationsDone', function() {{
            networkMesh.setOptions({{ physics: false }});
            networkMesh.fit({{ animation: {{ duration: 800, easingFunction: 'easeInOutQuad' }} }});
        }});

        // Click event para mostrar información
        networkMesh.on('click', function(params) {{
            if (params.nodes.length > 0) {{
                showDeviceInfo(params.nodes[0]);
            }}
        }});

        // Arrastre jerárquico - mover hijos con el padre
        let draggedNode = null;
        let initialPositions = {{}};

        networkMesh.on('dragStart', function(params) {{
            if (params.nodes.length > 0) {{
                draggedNode = params.nodes[0];
                const nodeIP = dispositivosData[draggedNode].ip;

                // Encontrar todos los hijos (dispositivos conectados a este nodo)
                const children = dispositivosData
                    .map((d, idx) => d.padre === nodeIP ? idx : null)
                    .filter(idx => idx !== null);

                // Guardar posiciones iniciales
                initialPositions = {{}};
                const positions = networkMesh.getPositions([draggedNode, ...children]);
                Object.keys(positions).forEach(nodeId => {{
                    initialPositions[nodeId] = {{ ...positions[nodeId] }};
                }});

                // Guardar lista de hijos
                draggedNode = {{
                    id: params.nodes[0],
                    children: children
                }};
            }}
        }});

        networkMesh.on('dragging', function(params) {{
            if (draggedNode && params.nodes.length > 0) {{
                const currentPos = networkMesh.getPositions([draggedNode.id])[draggedNode.id];
                const initialPos = initialPositions[draggedNode.id];

                if (currentPos && initialPos) {{
                    const deltaX = currentPos.x - initialPos.x;
                    const deltaY = currentPos.y - initialPos.y;

                    // Mover todos los hijos con el mismo delta
                    draggedNode.children.forEach(childId => {{
                        const childInitial = initialPositions[childId];
                        if (childInitial) {{
                            networkMesh.moveNode(childId,
                                childInitial.x + deltaX,
                                childInitial.y + deltaY
                            );
                        }}
                    }});
                }}
            }}
        }});

        networkMesh.on('dragEnd', function() {{
            draggedNode = null;
            initialPositions = {{}};
        }});


        // Vista 2: Jerárquica
        function initHierarchical() {{
            const nodesHier = new vis.DataSet(nodesData);
            const edgesHier = new vis.DataSet(edgesData);

            const containerHier = document.getElementById('topology-hierarchical');
            const dataHier = {{ nodes: nodesHier, edges: edgesHier }};

            const optionsHier = {{
                layout: {{
                    hierarchical: {{
                        enabled: true,
                        direction: 'LR',
                        sortMethod: 'hubsize',
                        levelSeparation: 250,
                        nodeSpacing: 80,
                        treeSpacing: 150,
                        blockShifting: true,
                        edgeMinimization: true,
                        parentCentralization: true,
                        shakeTowards: 'leaves'
                    }}
                }},
                physics: {{
                    enabled: false
                }},
                interaction: {{
                    hover: true,
                    tooltipDelay: 100,
                    navigationButtons: true,
                    keyboard: true,
                    zoomView: true,
                    dragView: true
                }},
                nodes: {{
                    shadow: {{
                        enabled: true,
                        color: 'rgba(0,0,0,0.2)',
                        size: 8
                    }}
                }},
                edges: {{
                    smooth: {{
                        enabled: true,
                        type: 'cubicBezier',
                        forceDirection: 'horizontal',
                        roundness: 0.6
                    }},
                    arrows: {{
                        to: {{
                            enabled: true,
                            scaleFactor: 0.8,
                            type: 'arrow'
                        }}
                    }},
                    shadow: {{
                        enabled: true,
                        color: 'rgba(0,0,0,0.15)',
                        size: 5
                    }},
                    color: {{
                        inherit: 'from'
                    }}
                }}
            }};

            window.networkHierarchical = new vis.Network(containerHier, dataHier, optionsHier);

            // Click event para mostrar información
            window.networkHierarchical.on('click', function(params) {{
                if (params.nodes.length > 0) {{
                    showDeviceInfo(params.nodes[0]);
                }}
            }});

            setTimeout(() => {{
                window.networkHierarchical.fit({{ animation: {{ duration: 500 }} }});
            }}, 100);
        }}

        // Vista 3: Bloques expandibles
        function initBlocks() {{
            const treeRoot = document.getElementById('tree-root');

            // Construir árbol jerárquico
            const ipToDevice = {{}};
            dispositivosData.forEach(d => {{
                ipToDevice[d.ip] = d;
            }});

            const hierarchy = {{}};
            dispositivosData.forEach(d => {{
                if (!d.padre) {{
                    hierarchy[d.ip] = {{ device: d, children: [] }};
                }}
            }});

            dispositivosData.forEach(d => {{
                if (d.padre && hierarchy[d.padre]) {{
                    hierarchy[d.padre].children.push({{ device: d, children: [] }});
                }} else if (d.padre) {{
                    // Buscar padre recursivamente
                    Object.values(hierarchy).forEach(parent => {{
                        if (parent.device.ip === d.padre) {{
                            parent.children.push({{ device: d, children: [] }});
                        }}
                    }});
                }}
            }});

            // Función recursiva para agregar hijos
            function addChildren(parentIp, targetList) {{
                dispositivosData.forEach(d => {{
                    if (d.padre === parentIp) {{
                        const node = {{ device: d, children: [] }};
                        targetList.push(node);
                        addChildren(d.ip, node.children);
                    }}
                }});
            }}

            // Reconstruir jerarquía completa
            Object.values(hierarchy).forEach(root => {{
                addChildren(root.device.ip, root.children);
            }});

            // Renderizar árbol
            function renderNode(node, level = 0) {{
                const d = node.device;
                const hasChildren = node.children.length > 0;

                const colorMap = {{
                    'gateway': '#1e40af',
                    'firewall': '#dc2626',
                    'modem': '#0ea5e9',
                    'switch': '#10b981',
                    'server': '#f59e0b',
                    'workstation': '#6b7280',
                    'laptop': '#8b5cf6',
                    'printer': '#ec4899',
                    'camera': '#ef4444'
                }};

                const color = colorMap[d.tipo] || '#64748b';
                const symbolMap = {{
                    'gateway': '◈',
                    'firewall': '🛡️',
                    'modem': '📡',
                    'switch': '⬣',
                    'server': '▮',
                    'workstation': '●',
                    'laptop': '●',
                    'printer': '⊞',
                    'camera': '◉'
                }};
                const symbol = symbolMap[d.tipo] || '●';

                const nodeDiv = document.createElement('div');
                nodeDiv.className = 'tree-node';

                const headerDiv = document.createElement('div');
                headerDiv.className = 'tree-node-header';
                headerDiv.innerHTML = `
                    ${{hasChildren ? '<span class="expand-icon">▶</span>' : '<span class="expand-icon" style="visibility:hidden;">▶</span>'}}
                    <div class="tree-node-icon" style="background: ${{color}}; color: white;">${{symbol}}</div>
                    <strong>${{d.hostname || d.ip}}</strong>
                    <span style="margin-left: auto; color: #64748b; font-size: 0.9em;">${{d.ip}}</span>
                    ${{d.velocidad ? `<span style="margin-left: 10px; padding: 2px 8px; background: #dbeafe; border-radius: 4px; font-size: 0.85em;">${{d.velocidad}}</span>` : ''}}
                `;

                // Obtener el índice del dispositivo
                const deviceIndex = dispositivosData.findIndex(dev => dev.ip === d.ip);

                const childrenDiv = document.createElement('div');
                childrenDiv.className = 'tree-node-children';

                if (hasChildren) {{
                    headerDiv.style.cursor = 'pointer';
                    const expandIcon = headerDiv.querySelector('.expand-icon');
                    expandIcon.onclick = function(e) {{
                        e.stopPropagation();
                        childrenDiv.classList.toggle('expanded');
                        this.textContent = childrenDiv.classList.contains('expanded') ? '▼' : '▶';
                    }};

                    // Click en el header muestra info (excepto en el icono de expandir)
                    headerDiv.onclick = function(e) {{
                        if (!e.target.classList.contains('expand-icon')) {{
                            showDeviceInfo(deviceIndex);
                        }}
                    }};
                }} else {{
                    // Sin hijos, click muestra info directamente
                    headerDiv.style.cursor = 'pointer';
                    headerDiv.onclick = function() {{
                        showDeviceInfo(deviceIndex);
                    }};
                }}

                if (hasChildren) {{
                    node.children.forEach(child => {{
                        childrenDiv.appendChild(renderNode(child, level + 1));
                    }});
                }}

                nodeDiv.appendChild(headerDiv);
                if (hasChildren) {{
                    nodeDiv.appendChild(childrenDiv);
                }}

                return nodeDiv;
            }}

            Object.values(hierarchy).forEach(root => {{
                treeRoot.appendChild(renderNode(root));
            }});

            window.blocksInitialized = true;
        }}

        // Gráfico 1: Tipos de dispositivo
        const ctx1 = document.getElementById('typeChart').getContext('2d');
        new Chart(ctx1, {{
            type: 'doughnut',
            data: {{
                labels: {json.dumps(list(tipos_count.keys()))},
                datasets: [{{
                    label: 'Dispositivos',
                    data: {json.dumps(list(tipos_count.values()))},
                    backgroundColor: ['#1e40af', '#0c4a6e', '#dc2626', '#0ea5e9', '#10b981', '#f59e0b', '#6b7280', '#8b5cf6', '#ec4899', '#ef4444', '#14b8a6']
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Dispositivos por Tipo',
                        font: {{ size: 16, weight: 'bold' }}
                    }},
                    legend: {{
                        position: 'bottom',
                        labels: {{ font: {{ size: 10 }} }}
                    }}
                }}
            }}
        }});

        // Gráfico 2: Velocidades de Módems (Real vs Contratada)
        const ctx2 = document.getElementById('speedChart').getContext('2d');

        // Extraer módems con info de SLA
        const modemsConSLA = dispositivosData.filter(d => {{
            const areaInfo = areasConfig[d.ip];
            return areaInfo && areaInfo.modem_sla;
        }});

        const modemsLabels = modemsConSLA.map(d => {{
            const areaInfo = areasConfig[d.ip];
            return areaInfo.modem_info || d.hostname || d.ip;
        }});

        const velocidadesContratadas = modemsConSLA.map(d => {{
            const areaInfo = areasConfig[d.ip];
            const sla = areaInfo.modem_sla || '';
            const match = sla.match(/(\d+)/);
            return match ? parseInt(match[1]) : 0;
        }});

        const velocidadesReales = modemsConSLA.map(d => {{
            const vel = d.velocidad || '';
            // Intentar extraer número de velocidad
            if (vel.includes('Gbps')) {{
                const match = vel.match(/([\d.]+)/);
                return match ? parseFloat(match[1]) * 1000 : 0;
            }} else if (vel.includes('Mbps')) {{
                const match = vel.match(/(\d+)/);
                return match ? parseInt(match[1]) : 0;
            }}
            return 0;
        }});

        // Calcular colores: verde si cumple >=90% SLA, amarillo si >=70%, rojo si <70%
        const coloresReales = velocidadesReales.map((real, i) => {{
            const contratada = velocidadesContratadas[i];
            const porcentaje = contratada > 0 ? (real / contratada) * 100 : 0;
            if (porcentaje >= 90) return '#10b981'; // Verde
            if (porcentaje >= 70) return '#f59e0b'; // Amarillo
            return '#ef4444'; // Rojo
        }});

        new Chart(ctx2, {{
            type: 'bar',
            data: {{
                labels: modemsLabels.length > 0 ? modemsLabels : ['No hay módems con SLA configurado'],
                datasets: [
                    {{
                        label: 'SLA Contratado',
                        data: modemsLabels.length > 0 ? velocidadesContratadas : [0],
                        backgroundColor: '#0ea5e9',
                        borderColor: '#0284c7',
                        borderWidth: 2
                    }},
                    {{
                        label: 'Velocidad Real',
                        data: modemsLabels.length > 0 ? velocidadesReales : [0],
                        backgroundColor: modemsLabels.length > 0 ? coloresReales : ['#6b7280'],
                        borderColor: modemsLabels.length > 0 ? coloresReales.map(c => c) : ['#4b5563'],
                        borderWidth: 2
                    }}
                ]
            }},
            options: {{
                indexAxis: 'y',  // Horizontal bars
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Módems: Velocidad Real vs SLA Contratado',
                        font: {{ size: 14, weight: 'bold' }}
                    }},
                    legend: {{
                        position: 'bottom',
                        labels: {{ font: {{ size: 10 }} }}
                    }},
                    tooltip: {{
                        callbacks: {{
                            label: function(context) {{
                                const valor = context.parsed.x;
                                const dataset = context.dataset.label;
                                if (dataset === 'Velocidad Real') {{
                                    const contratada = velocidadesContratadas[context.dataIndex];
                                    const cumplimiento = contratada > 0 ? ((valor / contratada) * 100).toFixed(1) : 0;
                                    return `${{dataset}}: ${{valor}} Mbps (${{cumplimiento}}% del SLA)`;
                                }}
                                return `${{dataset}}: ${{valor}} Mbps`;
                            }}
                        }}
                    }}
                }},
                scales: {{
                    x: {{
                        beginAtZero: true,
                        title: {{
                            display: true,
                            text: 'Velocidad (Mbps)'
                        }}
                    }}
                }}
            }}
        }});

        // Gráfico 3: Tipos de terminales
        const ctx3 = document.getElementById('terminalChart').getContext('2d');
        new Chart(ctx3, {{
            type: 'pie',
            data: {{
                labels: {json.dumps(list(terminal_types.keys()))},
                datasets: [{{
                    data: {json.dumps(list(terminal_types.values()))},
                    backgroundColor: ['#6b7280', '#8b5cf6', '#3b82f6', '#f59e0b', '#10b981', '#ec4899']
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Terminales: PC/Laptop/Móvil',
                        font: {{ size: 16, weight: 'bold' }}
                    }},
                    legend: {{
                        position: 'bottom',
                        labels: {{ font: {{ size: 11 }} }}
                    }}
                }}
            }}
        }});

        // Gráfico 4: Fabricantes
        const ctx4 = document.getElementById('vendorChart').getContext('2d');
        new Chart(ctx4, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(list(vendors_count.keys()))},
                datasets: [{{
                    label: 'Equipos',
                    data: {json.dumps(list(vendors_count.values()))},
                    backgroundColor: '#0ea5e9',
                    borderColor: '#0284c7',
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Equipos por Fabricante',
                        font: {{ size: 16, weight: 'bold' }}
                    }},
                    legend: {{ display: false }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: true,
                        ticks: {{ stepSize: 1 }}
                    }}
                }}
            }}
        }});

        // Gráfico 5: Departamentos
        const ctx5 = document.getElementById('deptChart').getContext('2d');
        new Chart(ctx5, {{
            type: 'bar',
            data: {{
                labels: {json.dumps(list(dept_count.keys()))},
                datasets: [{{
                    label: 'Equipos',
                    data: {json.dumps(list(dept_count.values()))},
                    backgroundColor: '#10b981',
                    borderColor: '#059669',
                    borderWidth: 2
                }}]
            }},
            options: {{
                responsive: true,
                maintainAspectRatio: true,
                indexAxis: 'y',
                plugins: {{
                    title: {{
                        display: true,
                        text: 'Equipos por Departamento',
                        font: {{ size: 16, weight: 'bold' }}
                    }},
                    legend: {{ display: false }}
                }},
                scales: {{
                    x: {{
                        beginAtZero: true,
                        ticks: {{ stepSize: 1 }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
"""

    ruta = os.path.join(carpeta, "dashboard_triple_vista.html")
    with open(ruta, 'w', encoding='utf-8') as f:
        f.write(html)

    return ruta

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Uso: python3 visualizador_triple_vista.py <archivo.zip>")
        sys.exit(1)

    metadata, carpeta = cargar(sys.argv[1])
    if not metadata:
        print("Error cargando datos")
        sys.exit(1)

    # Cargar configuración de áreas personalizadas
    areas_config = cargar_areas_config()
    if areas_config:
        print(f"📍 Configuración de áreas cargada: {len(areas_config)} dispositivos etiquetados")

    ruta = generar(metadata, carpeta, areas_config)
    print(f"\n✅ {os.path.abspath(ruta)}\n")

    webbrowser.open('file://' + os.path.abspath(ruta))

    print("✨ Dashboard Triple Vista Completo:")
    print("   ✅ 3 Vistas de topología: Malla + Jerárquica + Bloques")
    print("   ✅ 3 Gráficas: Tipo + Vendor + Área")
    print("   ✅ Logos de fabricantes integrados")
    print("   ✅ 8 modems Telmex + Fortinet")
