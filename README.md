# 🌐 Análisis de Red - Network Analyzer Pro

Sistema profesional de análisis y diagnóstico de redes empresariales con visualización interactiva y gemelo digital.

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.7+](https://img.shields.io/badge/python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/platform-Linux-lightgrey.svg)](https://www.linux.org/)

---

## 🚀 Inicio Rápido (Cliente)

### **Instalación Automática One-Liner:**

```bash
curl -sL https://raw.githubusercontent.com/transformatedigital/analisis_red/main/scripts/install.sh | sudo bash
```

O descargar y ejecutar manualmente:

```bash
# Opción 1: Con curl
curl -O https://raw.githubusercontent.com/transformatedigital/analisis_red/main/scripts/network_scan_client_v2_auto.sh
sudo bash network_scan_client_v2_auto.sh

# Opción 2: Con wget
wget https://raw.githubusercontent.com/transformatedigital/analisis_red/main/scripts/network_scan_client_v2_auto.sh
sudo bash network_scan_client_v2_auto.sh
```

---

## ✨ Características

### **Para el Cliente:**
- ✅ **Escaneo automático** de toda la red local
- ✅ **Detección de módems** por vendor (Cisco, Huawei, ZTE, Telmex, etc.)
- ✅ **Análisis de velocidades** vía SNMP
- ✅ **Identificación de dispositivos críticos** por tráfico
- ✅ **Generación de diagnóstico completo** en formato ZIP

### **Para el Administrador:**
- 📊 **Dashboard interactivo** HTML5 (funciona offline)
- 🔍 **Búsqueda y filtrado** inteligente de dispositivos
- 📈 **Gráficas de velocidades** (Real vs SLA contratado)
- 🎯 **Diagnóstico automático** con recomendaciones
- 💰 **Métricas ejecutivas** para dirección (ROI, costos, riesgos)
- 🏷️ **Sistema de etiquetas** personalizadas por ubicación

---

## 📦 Componentes

```
analisis_red/
├── visualizador_triple_vista.py    # Generador de dashboard HTML
├── enriquecer_metadata_kais.py     # Enriquecedor de metadata
├── vendor_lookup.py                # Lookup de fabricantes por MAC
├── scripts/
│   └── network_scan_client_v2_auto.sh  # Script para clientes
├── network-icons/                  # Iconos SVG para dispositivos
├── vis-network.min.js             # Librería de visualización
├── chart.min.js                   # Librería de gráficas
└── ejemplos/
    └── areas_config_ejemplo.json  # Ejemplo de configuración
```

---

## 🎯 Casos de Uso

### **1. Cliente con Múltiples Módems (Telmex, Totalplay, etc.)**
- Detecta automáticamente todos los módems
- Compara velocidad real vs SLA contratado
- Genera reporte para reclamar incumplimientos

### **2. Auditoría de Red Empresarial**
- Escanea toda la infraestructura
- Identifica dispositivos obsoletos
- Recomienda mejoras con ROI calculado

### **3. Diagnóstico de Problemas**
- Detecta cuellos de botella
- Identifica dispositivos sin firewall
- Encuentra configuraciones ineficientes

---

## 📖 Guía de Uso

### **Paso 1: Escaneo (Cliente)**

El cliente ejecuta en su servidor Linux:

```bash
sudo bash network_scan_client_v2_auto.sh
```

**Resultado:**
- Archivo ZIP con diagnóstico completo
- Metadata en JSON
- Configuración automática de módems detectados

### **Paso 2: Procesamiento (Administrador)**

```bash
# 1. Descomprimir diagnóstico
unzip diagnostico_Cliente_YYYYMMDD_HHMMSS.zip

# 2. Revisar y ajustar configuración (opcional)
nano diagnostico_*/areas_config_auto.json

# 3. Copiar configuración
cp diagnostico_*/areas_config_auto.json areas_config.json

# 4. Enriquecer metadata
python3 enriquecer_metadata_kais.py diagnostico_*/metadata_simple.json

# 5. Generar dashboard
python3 visualizador_triple_vista.py diagnostico_*_enriquecido.zip
```

**Resultado:**
- Dashboard HTML interactivo
- Un solo archivo portable
- Funciona sin internet

### **Paso 3: Entrega**

**Opción A: Archivo HTML directo**
```bash
# Enviar dashboard_triple_vista.html al cliente por email
# El archivo es completamente portable y funciona offline
```

**Opción B: Publicar en GitHub Pages**
```bash
# Copiar dashboard a docs/
cp gemelo_*/dashboard_triple_vista.html docs/index.html

# Commit y push
git add docs/
git commit -m "Actualizar dashboard publicado"
git push origin main

# URL pública: https://transformatedigital.github.io/analisis_red/
```

---

## 🌐 GitHub Pages (Dashboard Público)

Este proyecto incluye soporte para GitHub Pages. Puedes publicar dashboards en:

**https://transformatedigital.github.io/analisis_red/**

### Cómo Habilitar (Solo Primera Vez):

1. Ve a tu repositorio en GitHub
2. **Settings** → **Pages**
3. **Source**: Deploy from a branch
4. **Branch**: `main` → **Folder**: `/docs` → **Save**

### Cómo Actualizar el Dashboard:

```bash
# Después de generar análisis
cp gemelo_Cliente_YYYYMMDD/dashboard_triple_vista.html docs/index.html
git add docs/index.html
git commit -m "Actualizar dashboard"
git push origin main
```

⚠️ **Seguridad:** GitHub Pages es público. No publiques datos confidenciales de clientes. Usa datos anonimizados para demos.

---

## 🖼️ Capturas del Dashboard

### Vista Malla Interactiva
- Topología completa de la red
- Drag & drop jerárquico
- Código de colores por velocidad
- Click para detalles completos

### Gráfica de Velocidades (Módems)
- Comparación Real vs SLA
- Color-coded: Verde ≥90%, Amarillo 70-90%, Rojo <70%
- Tooltip con % de cumplimiento

### Diagnóstico Inteligente
- Health Score de la red
- Problemas categorizados (Crítico/Advertencia/Recomendación)
- Plan de acción recomendado
- Tabla de módems con SLA

### Métricas Ejecutivas
- Inversión total estimada
- Nivel de riesgo
- ROI de mejoras sugeridas
- Prioridades de inversión

---

## ⚙️ Configuración Avanzada

### **Etiquetas Personalizadas (`areas_config.json`)**

```json
{
  "192.168.1.10": {
    "area": "Datacenter Principal",
    "piso": "2do Piso",
    "rack": "A-01",
    "modem_info": "Módem Telmex #1",
    "modem_sla": "200 Mbps contratados",
    "contacto": "Juan Pérez - IT",
    "notas": "Crítico - No desconectar"
  }
}
```

Esta información se muestra automáticamente en:
- Tooltips al pasar el mouse
- Modal de detalles al hacer click
- Diagnóstico de SLA

---

## 🔧 Requisitos

### **Cliente (para escaneo):**
- Linux (Ubuntu, Debian, CentOS, etc.)
- Acceso root (`sudo`)
- Herramientas (se instalan automáticamente):
  - `nmap`
  - `arp-scan`
  - `snmp`
  - `speedtest-cli`
  - `python3`

### **Administrador (para procesamiento):**
- Python 3.7+
- Archivos del repositorio

---

## 🌟 Características Destacadas

### **Detección Automática de Módems**
El script V2 identifica módems por:
- Vendor MAC address
- SNMP queries
- Análisis de tráfico
- Detección de puertos de administración

### **Análisis de SLA**
- Extrae velocidad contratada de `areas_config.json`
- Compara con velocidad real medida
- Genera alertas si incumplimiento <90%
- Categoriza por severidad (<70% = Crítico)

### **Búsqueda Inteligente**
- Filtra por IP, MAC, hostname, vendor
- Botones rápidos: Todos, Routers, Switches, Servidores, Lentos
- Resaltado visual en el grafo
- Zoom automático a resultados

---

## 📊 Métricas y KPIs

El dashboard calcula automáticamente:

- **Costo de infraestructura** (hardware + mantenimiento)
- **Health Score** (0-100 basado en problemas y velocidades)
- **ROI de mejoras** (inversión vs ahorro proyectado)
- **Uptime estimado** (SLA compliance)
- **Prioridades de inversión** (ordenadas por impacto)

---

## 🤝 Contribuir

Las contribuciones son bienvenidas! Por favor:

1. Fork el repositorio
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

---

## 📝 Licencia

Este proyecto está bajo la Licencia MIT - ver el archivo [LICENSE](LICENSE) para detalles.

---

## 💡 Soporte

Para soporte, contacta a:
- **Email:** soporte@transformatedigital.com
- **Issues:** [GitHub Issues](https://github.com/transformatedigital/analisis_red/issues)

---

## 🎯 Roadmap

### **v1.0 - Actual** ✅
- Escaneo automático
- Dashboard interactivo
- Análisis de SLA
- Gráficas profesionales

### **v2.0 - Próximamente** 🚧
- Monitoreo en tiempo real
- API REST
- Dashboard live (WebSocket)
- Mobile app

### **v3.0 - Futuro** 📅
- Machine Learning para predicción de fallos
- Integración con sistemas de ticketing
- Alertas automáticas (email, SMS, Telegram)
- Multi-tenant

---

## 📈 Estadísticas

- 🌟 **100%** detección automática de dispositivos
- 📊 **4 vistas** de topología diferentes
- 🎨 **6 gráficas** estadísticas
- 🔍 **Búsqueda** en tiempo real
- 💾 **Offline** - funciona sin internet
- 📦 **Un solo archivo** HTML portable

---

## 🙏 Agradecimientos

- [vis-network](https://visjs.org/) - Visualización de redes
- [Chart.js](https://www.chartjs.org/) - Gráficas interactivas
- Comunidad open source

---

<p align="center">
  Hecho con ❤️ por <a href="https://transformatedigital.com">Transformate Digital</a>
</p>

<p align="center">
  <a href="https://github.com/transformatedigital/analisis_red">⭐ Dale una estrella si te fue útil!</a>
</p>
