# ⚡ Inicio Rápido - Para Clientes

## 🎯 Un Solo Comando

```bash
curl -sL https://raw.githubusercontent.com/transformatedigital/analisis_red/main/scripts/install.sh | sudo bash
```

**Eso es todo!** El script:
1. ✅ Descarga todo lo necesario
2. ✅ Instala dependencias automáticamente
3. ✅ Escanea tu red
4. ✅ Genera archivo ZIP con diagnóstico

---

## 📦 Resultado

Al finalizar obtendrás:

```
diagnostico_TuEmpresa_20260605_143022.zip
```

**Envía este archivo a tu proveedor de análisis.**

---

## 🔍 ¿Qué Incluye el ZIP?

- `metadata_simple.json` - Datos de tu red
- `areas_config_auto.json` - Configuración de módems detectados
- `nmap_*.txt` - Escaneos detallados
- `arp_scan.txt` - Dispositivos encontrados
- `speedtest.txt` - Velocidad de internet
- `modems_detail/` - Análisis individual de cada módem

---

## 📧 ¿Qué Recibirás?

Después de enviar el ZIP, recibirás:

**Dashboard HTML Interactivo** con:
- 🗺️ Mapa visual de tu red completa
- 📊 Gráficas estadísticas
- 📡 Análisis de módems (Real vs SLA contratado)
- 🎯 Diagnóstico inteligente con recomendaciones
- 💰 Métricas para dirección (costos, ROI)

---

## ❓ Problemas Comunes

### "Permission denied"
```bash
# Agregar sudo antes:
curl -sL ... | sudo bash
```

### "command not found: curl"
```bash
# Usar wget en su lugar:
wget -qO- https://raw.githubusercontent.com/transformatedigital/analisis_red/main/scripts/install.sh | sudo bash
```

### "No se detectaron módems"
Es normal si:
- Los módems tienen vendors no reconocidos
- Están en otra subred
- No están directamente conectados

El diagnóstico funciona igual.

---

## 🔒 Seguridad

Este script:
- ✅ Solo **LEE** información de tu red
- ✅ **NO modifica** configuraciones
- ✅ **NO envía** datos a internet automáticamente
- ✅ Es código abierto (puedes revisarlo)

---

## 📞 Soporte

¿Problemas o preguntas?
- 📧 Email: soporte@transformatedigital.com
- 🌐 GitHub: https://github.com/transformatedigital/analisis_red/issues

---

## 🚀 Avanzado

### Opción 2: Descarga Manual

```bash
# 1. Descargar script
wget https://raw.githubusercontent.com/transformatedigital/analisis_red/main/scripts/network_scan_client_v2_auto.sh

# 2. Ejecutar
sudo bash network_scan_client_v2_auto.sh
```

### Opción 3: Clonar Repositorio Completo

```bash
git clone https://github.com/transformatedigital/analisis_red.git
cd analisis_red/scripts
sudo bash network_scan_client_v2_auto.sh
```

---

<p align="center">
  ⭐ Hecho simple para ti
</p>
