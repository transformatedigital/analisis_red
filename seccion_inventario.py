#!/usr/bin/env python3
"""Sección de Inventario IT para el dashboard (datos del administrador de red).

Genera HTML estático (cards + barras CSS) a partir de un JSON de estadísticas
de inventario. Sin dependencias de Chart.js para evitar problemas de render.
"""
import json


def cargar_inventario(ruta_json):
    """Carga y valida el JSON de estadísticas de inventario."""
    try:
        with open(ruta_json, 'r', encoding='utf-8') as f:
            inv = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"⚠️  Error leyendo inventario '{ruta_json}': {e}")
        return None
    if 'total_equipos' not in inv:
        print(f"⚠️  El JSON de inventario no tiene 'total_equipos'")
        return None
    return inv


def _barras(titulo, datos, color='#3b82f6', top=12):
    """Grupo de barras horizontales CSS a partir de un dict {etiqueta: valor}."""
    items = sorted(datos.items(), key=lambda x: -x[1])[:top]
    if not items:
        return ''
    max_v = max(v for _, v in items)
    filas = ''
    for etiqueta, valor in items:
        pct = int(valor / max_v * 100) if max_v else 0
        filas += f'''
            <div style="display: flex; align-items: center; margin: 6px 0; gap: 10px;">
                <div style="width: 150px; font-size: 0.85em; color: #334155; text-align: right;
                            white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{etiqueta}</div>
                <div style="flex: 1; background: #f1f5f9; border-radius: 6px; height: 22px; position: relative;">
                    <div style="width: {pct}%; background: {color}; height: 100%; border-radius: 6px;
                                min-width: 28px; display: flex; align-items: center; justify-content: flex-end;
                                padding-right: 6px; color: white; font-size: 0.8em; font-weight: 600;">{valor}</div>
                </div>
            </div>'''
    return f'''
        <div style="background: white; border: 2px solid #e2e8f0; border-radius: 10px; padding: 18px;">
            <h4 style="margin: 0 0 12px 0; color: #1e293b;">{titulo}</h4>
            {filas}
        </div>'''


def _card(valor, titulo, subtitulo, color):
    return f'''
        <div style="background: white; border: 2px solid #e2e8f0; border-left: 5px solid {color};
                    border-radius: 10px; padding: 16px 20px; flex: 1; min-width: 180px;">
            <div style="font-size: 1.9em; font-weight: 700; color: {color};">{valor}</div>
            <div style="font-weight: 600; color: #1e293b; margin-top: 2px;">{titulo}</div>
            <div style="font-size: 0.82em; color: #64748b; margin-top: 4px;">{subtitulo}</div>
        </div>'''


def _informe_faltantes(inv, scan_stats):
    """Informe detallado de qué falta para completar la plataforma de gemelo digital."""
    filas_campos = ''
    for c in inv.get('campos_incompletos', []):
        color = '#f59e0b' if c['pct'] >= 50 else '#ef4444'
        filas_campos += f'''
            <tr>
                <td style="padding: 6px 10px; border-bottom: 1px solid #e2e8f0;">{c['campo']}</td>
                <td style="padding: 6px 10px; border-bottom: 1px solid #e2e8f0; text-align: center;">{c['llenos']}/{c['total']}</td>
                <td style="padding: 6px 10px; border-bottom: 1px solid #e2e8f0; text-align: center; color: {color}; font-weight: 600;">{c['pct']}%</td>
            </tr>'''

    def bloque(titulo, color, items):
        lis = ''.join(f'<li style="margin: 5px 0;"><strong>{t}:</strong> {d}</li>' for t, d in items)
        return f'''
            <div style="background: white; border: 2px solid #e2e8f0; border-top: 4px solid {color}; border-radius: 10px; padding: 18px;">
                <h4 style="margin: 0 0 10px 0; color: #1e293b;">{titulo}</h4>
                <ul style="margin: 0; padding-left: 20px; color: #334155; line-height: 1.6; font-size: 0.92em;">{lis}</ul>
            </div>'''

    # Contenido del informe: viene del JSON de inventario (datos del cliente,
    # no se versionan). Cada bloque es una lista de pares [titulo, descripcion].
    informe = inv.get('informe_faltantes', {})
    b_red = bloque('🔴 Del escaneo de red (próxima visita)', '#ef4444',
                   informe.get('escaneo', [('Pendiente', 'definir faltantes del escaneo en informe_faltantes.escaneo del JSON de inventario.')]))
    b_inv = bloque('🟠 Del inventario (para el administrador de red)', '#f59e0b',
                   informe.get('inventario', [('Pendiente', 'definir faltantes del inventario en informe_faltantes.inventario del JSON de inventario.')]))
    b_cliente = bloque('🔵 Del cliente / gerencia', '#3b82f6',
                       informe.get('cliente', [('Pendiente', 'definir faltantes del cliente en informe_faltantes.cliente del JSON de inventario.')]))

    tabla_campos = ''
    if filas_campos:
        tabla_campos = f'''
            <div style="margin-top: 15px; background: white; border: 2px solid #e2e8f0; border-radius: 10px; padding: 18px;">
                <h4 style="margin: 0 0 10px 0; color: #1e293b;">📝 Campos del inventario con captura incompleta</h4>
                <table style="width: 100%; border-collapse: collapse; font-size: 0.88em;">
                    <tr style="background: #f8fafc;">
                        <th style="padding: 8px 10px; text-align: left;">Campo</th>
                        <th style="padding: 8px 10px;">Capturados</th>
                        <th style="padding: 8px 10px;">% Completo</th>
                    </tr>{filas_campos}
                </table>
            </div>'''

    return f'''
            <div style="margin-top: 20px;">
                <h3 style="color: #1e293b; margin: 0 0 12px 0;">📋 Informe: qué falta para completar la plataforma (gemelo digital)</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 15px;">
                    {b_red}
                    {b_inv}
                    {b_cliente}
                </div>
                {tabla_campos}
            </div>'''


def generar_seccion_inventario(inv, scan_stats):
    """Genera la sección HTML de inventario.

    inv: dict con estadísticas del inventario (ver inventario_stats.json)
    scan_stats: dict con datos del escaneo {'total_online': int, 'telefonos_online': int}
    """
    total = inv['total_equipos']
    tel_reg = inv.get('telefonos_registrados', 0)
    tel_online = scan_stats.get('telefonos_online', 0)
    total_online = scan_stats.get('total_online', 0)
    activos_registrados = total + tel_reg

    tipo = inv.get('por_tipo_equipo', {})
    laptops = tipo.get('LAPTOP', 0)
    escritorios = tipo.get('ESCRITORIO', 0)

    os_dist = inv.get('por_os', {})
    win11 = os_dist.get('WINDOWS 11', 0)
    win10 = os_dist.get('WINDOWS 10', 0)

    migracion = inv.get('cumple_migracion', {})
    no_cumple = migracion.get('No cumple', 0)
    pct_no_cumple = int(no_cumple / total * 100) if total else 0

    cards = (
        _card(total, 'Equipos inventariados', f'{laptops} laptops · {escritorios} escritorios', '#3b82f6')
        + _card(f'{tel_online}/{tel_reg}', 'Teléfonos IP en línea', f'{tel_reg} extensiones registradas, {tel_online} vistos en el escaneo', '#8b5cf6')
        + _card(f'{win11}/{total}', 'Ya en Windows 11', f'{win10} equipos siguen en Windows 10', '#10b981')
        + _card(f'{no_cumple}', 'No cumplen para Win11', f'{pct_no_cumple}% del parque requiere reemplazo/upgrade', '#ef4444')
    )

    barras = (
        _barras('🏢 Equipos por Departamento (Top 12)', inv.get('por_departamento', {}), '#3b82f6')
        + _barras('🏷️ Equipos por Empresa', inv.get('por_empresa', {}), '#8b5cf6')
        + _barras('💻 Equipos por Marca', inv.get('por_marca', {}), '#0ea5e9')
        + _barras('🧠 Memoria RAM', inv.get('por_ram', {}), '#10b981')
        + _barras('⚙️ Categoría de Procesador', inv.get('por_cpu_cat', {}), '#f59e0b')
        + _barras('📍 Equipos por Sucursal', inv.get('por_sucursal', {}), '#64748b')
    )

    fuente = inv.get('fuente', 'Inventario IT del cliente')

    return f'''
        <div class="section">
            <h2 class="section-title">📦 Inventario IT — Datos del Administrador de Red</h2>
            <p style="color: #64748b; margin: 0 0 18px 0; font-size: 0.9em;">Fuente: {fuente}</p>

            <div style="display: flex; gap: 15px; flex-wrap: wrap; margin-bottom: 20px;">
                {cards}
            </div>

            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 15px;">
                {barras}
            </div>

            <div style="margin-top: 20px; background: #fffbeb; border: 2px solid #fbbf24; border-radius: 10px; padding: 18px;">
                <h4 style="margin: 0 0 10px 0; color: #92400e;">🔀 Cruce: Escaneo de Red vs Inventario</h4>
                <ul style="margin: 0; padding-left: 20px; color: #451a03; line-height: 1.7;">
                    <li><strong>{total_online} dispositivos en línea</strong> durante el escaneo vs <strong>{activos_registrados} activos registrados</strong> en inventario ({total} equipos de cómputo + {tel_reg} extensiones telefónicas).</li>
                    <li><strong>Teléfonos:</strong> {tel_reg} extensiones registradas, {tel_online} teléfonos IP respondieron al escaneo ({tel_reg - tel_online} apagados, desconectados o fuera de la subred escaneada).</li>
                    {''.join(f'<li>{nota}</li>' for nota in inv.get('cruce_notas', []))}
                </ul>
            </div>

            {_informe_faltantes(inv, scan_stats)}
        </div>'''
