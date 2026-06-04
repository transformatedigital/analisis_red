# 🚀 ANÁLISIS DE RED - INSTRUCCIONES PARA CLIENTE

## ⚡ MÉTODO 1: UN SOLO COMANDO (RECOMENDADO)

Ejecuta esto en tu servidor Linux:

```bash
curl -sL https://raw.githubusercontent.com/transformatedigital/analisis_red/main/scripts/install.sh | sudo bash
```

**Eso es todo!** El script:
1. ✅ Instala dependencias automáticamente
2. ✅ Escanea toda tu red
3. ✅ Detecta módems automáticamente
4. ✅ Mide velocidades reales
5. ✅ Genera archivo ZIP con diagnóstico completo

---

## 📦 MÉTODO 2: DESCARGA MANUAL

### Paso 1: Descargar el script

```bash
wget https://raw.githubusercontent.com/transformatedigital/analisis_red/main/scripts/network_scan_client_v2_auto.sh
```

### Paso 2: Ejecutar

```bash
sudo bash network_scan_client_v2_auto.sh
```

---

## 📧 RESULTADO

Al finalizar obtendrás un archivo ZIP:

```
diagnostico_TuEmpresa_20260604_143022.zip
```

**ENVÍA ESTE ARCHIVO** a tu proveedor de análisis por email.

---

## 📊 QUÉ INCLUYE EL ZIP

- `metadata_simple.json` - Todos los dispositivos detectados
- `areas_config_auto.json` - Módems detectados con sus velocidades
- `nmap_*.txt` - Escaneos detallados
- `arp_scan.txt` - Lista de todos los dispositivos
- `speedtest.txt` - Velocidad de internet medida
- `modems_detail/` - Información detallada de cada módem

---

## ⚙️ REQUISITOS

- **Sistema Operativo**: Linux (Ubuntu, Debian, CentOS, etc.)
- **Permisos**: Root (sudo)
- **Conexión**: Internet (para descargar dependencias)

---

## ❓ PROBLEMAS COMUNES

### "Permission denied"
```bash
# Agregar sudo:
curl -sL ... | sudo bash
```

### "command not found: curl"
```bash
# Usar wget:
wget -qO- https://raw.githubusercontent.com/transformatedigital/analisis_red/main/scripts/install.sh | sudo bash
```

### "No se detectaron módems"
**Es normal si:**
- Los módems tienen vendors no reconocidos
- Están en otra subred
- No responden a SNMP

**El diagnóstico funciona igual.**

---

## 🔒 SEGURIDAD

Este script:
- ✅ Solo **LEE** información de tu red
- ✅ **NO modifica** configuraciones
- ✅ **NO envía** datos a internet automáticamente
- ✅ Es código abierto (puedes revisarlo)

---

## 💰 QUÉ RECIBIRÁS

Después de enviar el ZIP, recibirás un **Dashboard HTML Interactivo** con:

### 🗺️ Visualización
- Mapa visual completo de tu red
- 3 vistas diferentes (Malla, Árbol, Bloques)
- Iconos por tipo de dispositivo

### 📊 Análisis
- 6 gráficas estadísticas profesionales
- Diagnóstico inteligente con recomendaciones
- Análisis de módems: Real vs SLA contratado
- Identificación de problemas críticos

### 💼 Métricas Ejecutivas
- Health Score de la red (0-100)
- Costo estimado de infraestructura
- ROI de mejoras sugeridas
- Prioridades de inversión

---

## 📞 SOPORTE

¿Problemas o preguntas?

- 📧 Email: soporte@transformatedigital.com
- 🌐 GitHub: https://github.com/transformatedigital/analisis_red/issues

---

## 🎯 EJEMPLO DE USO

```bash
# 1. Ejecutar en tu servidor
curl -sL https://raw.githubusercontent.com/transformatedigital/analisis_red/main/scripts/install.sh | sudo bash

# 2. Esperar 5-10 minutos (dependiendo del tamaño de tu red)

# 3. Al finalizar verás:
✅ diagnostico_MiEmpresa_20260604_143022.zip

# 4. Enviar el ZIP por email a tu proveedor

# 5. En 24-48 hrs recibirás:
📊 dashboard_interactivo.html
```

---

<p align="center">
  ⭐ Simple, Automático, Profesional
</p>
