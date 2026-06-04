# 🪟 ANÁLISIS DE RED - INSTRUCCIONES PARA WINDOWS

## 🎯 ¿WSL o PowerShell? - RECOMENDACIÓN

### ✅ **OPCIÓN 1: WSL (RECOMENDADO) - MÁS COMPLETO**

**Ventajas:**
- ✅ **Usa el script original de Linux** (más completo y probado)
- ✅ **Detecta MUCHO MÁS información:**
  - Velocidades reales via SNMP
  - Análisis de tráfico de red
  - Detección avanzada de módems
  - Speedtest real (no solo ping)
  - Más vendors en la base de datos
- ✅ **Mismo resultado que en Linux** (100% compatible)
- ✅ **Fácil de instalar** (1 comando)

**Desventajas:**
- Requiere Windows 10/11
- Ocupa ~1 GB de espacio

### ⚡ **OPCIÓN 2: PowerShell - MÁS RÁPIDO**

**Ventajas:**
- ✅ **No requiere instalación** (ya está en Windows)
- ✅ **Más rápido** de ejecutar
- ✅ **Funciona en Windows 7/8/10/11**

**Desventajas:**
- ❌ **Menos información:** Solo ping, ARP, puertos básicos
- ❌ **No puede obtener velocidades SNMP** de módems
- ❌ **No hace speedtest real** (solo ping)
- ❌ **Detección de módems limitada**

---

## 🏆 **MI RECOMENDACIÓN:**

| Escenario | Usar |
|-----------|------|
| **Cliente tiene 5+ módems** | ✅ **WSL** (necesitas SNMP) |
| **Necesitas velocidades reales** | ✅ **WSL** |
| **Red empresarial grande** | ✅ **WSL** |
| **Red pequeña (<20 dispositivos)** | ⚡ PowerShell OK |
| **No pueden instalar WSL** | ⚡ PowerShell |
| **Análisis rápido/demo** | ⚡ PowerShell |

---

## 📦 OPCIÓN 1: WSL (RECOMENDADO)

### Paso 1: Instalar WSL

Abre **PowerShell como Administrador** y ejecuta:

```powershell
wsl --install
```

Reinicia la computadora cuando te lo pida.

### Paso 2: Configurar Ubuntu

Al reiniciar, se abrirá Ubuntu automáticamente. Te pedirá:
- Usuario: (elige cualquiera)
- Contraseña: (elige cualquiera)

### Paso 3: Ejecutar el Script

En la terminal de Ubuntu que se abrió, ejecuta:

```bash
curl -sL https://raw.githubusercontent.com/transformatedigital/analisis_red/main/scripts/install.sh | sudo bash
```

### Paso 4: Obtener el ZIP

El archivo ZIP estará en:
```
\\wsl$\Ubuntu\home\TU_USUARIO\diagnostico_*.zip
```

Para abrirlo fácilmente:
```bash
# En la terminal de Ubuntu
explorer.exe .
```

---

## ⚡ OPCIÓN 2: PowerShell Nativo

### Paso 1: Descargar Script

```powershell
# Descargar
Invoke-WebRequest -Uri "https://raw.githubusercontent.com/transformatedigital/analisis_red/main/scripts/network_scan_windows.ps1" -OutFile "network_scan_windows.ps1"
```

### Paso 2: Permitir Ejecución

```powershell
# Habilitar scripts (solo primera vez)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Paso 3: Ejecutar

```powershell
# Ejecutar como Administrador
.\network_scan_windows.ps1
```

### Paso 4: Obtener ZIP

Al finalizar se abrirá automáticamente la carpeta con el archivo:
```
diagnostico_COMPUTADORA_20260604_143022.zip
```

---

## 🔄 COMPARACIÓN DE RESULTADOS

### Con WSL (Completo):
```json
{
  "ip": "192.168.1.10",
  "mac": "00:25:9C:AA:BB:01",
  "hostname": "modem-infinitum-1",
  "vendor": "Telmex",
  "tipo": "modem",
  "velocidad": "85 Mbps",          ← ✅ Velocidad REAL via SNMP
  "puertos_abiertos": [80, 8080, 161],
  "trafico_total": "420 GB",       ← ✅ Tráfico real capturado
  "snmp_info": {                   ← ✅ Info adicional
    "sysDescr": "INFINITUM...",
    "uptime": "45 days"
  }
}
```

### Con PowerShell (Básico):
```json
{
  "ip": "192.168.1.10",
  "mac": "00:25:9C:AA:BB:01",
  "hostname": "modem-infinitum-1",
  "vendor": "Telmex",
  "tipo": "modem",
  "velocidad": "1 Gbps",           ← ⚠️  Estimado (no real)
  "puertos_abiertos": [80, 8080],
  "trafico_total": "N/A"           ← ❌ No disponible
}
```

---

## 📊 RESUMEN

| Característica | WSL | PowerShell |
|----------------|-----|------------|
| **Instalación** | 5 min | 0 min |
| **Dispositivos detectados** | ✅✅✅ | ✅✅ |
| **Velocidades SNMP** | ✅ Sí | ❌ No |
| **Análisis de tráfico** | ✅ Sí | ❌ No |
| **Speedtest real** | ✅ Sí | ⚠️  Solo ping |
| **Detección de módems** | ✅✅✅ | ✅ |
| **Calidad del dashboard** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ |

---

## ❓ PREGUNTAS FRECUENTES

### ¿WSL es seguro?
✅ Sí, es una característica oficial de Microsoft incluida en Windows 10/11.

### ¿WSL consume muchos recursos?
No, solo ~1 GB de espacio y usa muy poca RAM cuando no está activo.

### ¿Puedo desinstalar WSL después?
Sí, desde "Agregar o quitar programas".

### ¿El script PowerShell funciona?
Sí, pero con **menos información**. Es suficiente para redes pequeñas.

### ¿Qué pasa si no puedo instalar WSL?
Usa el script PowerShell. Detectará dispositivos básicos y funcionará.

---

## 💡 MI CONSEJO FINAL

**Para clientes empresariales con múltiples módems/ISPs:**
👉 **Usa WSL** - La diferencia en calidad de datos es ENORME

**Para redes caseras o pequeñas oficinas:**
👉 PowerShell está bien

---

## 📞 SOPORTE

¿Problemas?
- 📧 Email: soporte@transformatedigital.com
- 🌐 GitHub: https://github.com/transformatedigital/analisis_red/issues
