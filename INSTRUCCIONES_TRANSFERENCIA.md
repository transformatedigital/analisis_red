# 📦 CÓMO TRANSFERIR EL PROYECTO A OTRA COMPUTADORA

## ✅ **OPCIÓN 1: DESDE GITHUB (MÁS FÁCIL)** ⭐ RECOMENDADO

### En la computadora nueva:

```bash
# 1. Instalar git (si no lo tienes)
sudo apt-get install git

# 2. Clonar el repositorio
git clone https://github.com/transformatedigital/analisis_red.git

# 3. Entrar al directorio
cd analisis_red

# 4. Ver todos los archivos
ls -la
```

**✅ Listo!** Tendrás TODO el proyecto actualizado.

---

## 📦 **OPCIÓN 2: USANDO EL ZIP**

### Paso 1: Copiar el ZIP a la otra computadora

El archivo está aquí:
```
/home/cfonseca/network-analyzer-complete.zip
```

**Tamaño:** 517 KB

Cópialo usando:
- USB
- Email
- SCP/SFTP
- Google Drive / Dropbox

### Paso 2: En la computadora nueva

```bash
# 1. Descomprimir
unzip network-analyzer-complete.zip -d analisis_red

# 2. Entrar al directorio
cd analisis_red

# 3. Verificar archivos
ls -la
```

---

## 🔄 **MANTENER ACTUALIZADO (CON GIT)**

Si usaste git clone, puedes actualizar fácilmente:

```bash
# Dentro del directorio analisis_red
git pull origin main
```

Esto descarga todos los cambios nuevos del repositorio.

---

## 📁 **ARCHIVOS IMPORTANTES DEL PROYECTO**

```
analisis_red/
├── scripts/
│   ├── install.sh                          ← Instalador para clientes (Linux)
│   ├── network_scan_client_v2_auto.sh      ← Script de escaneo (Linux)
│   └── network_scan_windows.ps1            ← Script de escaneo (Windows)
│
├── visualizador_triple_vista.py            ← Genera dashboard HTML
├── enriquecer_metadata_kais.py             ← Enriquece datos
├── vendor_lookup.py                        ← Base datos vendors
│
├── docs/                                   ← GitHub Pages (web pública)
│   ├── index.html                          ← Dashboard KAIST-GDI
│   └── demo.html                           ← Dashboard demo
│
├── README.md                               ← Documentación principal
├── RESUMEN_PROYECTO.md                     ← Resumen completo
├── INSTRUCCIONES_CLIENTE.md                ← Para clientes
└── INSTRUCCIONES_WINDOWS.md                ← Para Windows
```

---

## 🚀 **USO RÁPIDO DESPUÉS DE TRANSFERIR**

### Para generar un análisis de cliente:

```bash
# 1. El cliente ejecuta (en su servidor):
curl -sL https://raw.githubusercontent.com/transformatedigital/analisis_red/main/scripts/install.sh | sudo bash

# 2. Te envía: diagnostico_EMPRESA_YYYYMMDD.zip

# 3. Tú procesas:
python3 enriquecer_metadata_kais.py diagnostico_*/metadata_simple.json
python3 visualizador_triple_vista.py diagnostico_*_enriquecido.zip

# 4. Entregas: dashboard_triple_vista.html
```

---

## 🌐 **URLS DEL PROYECTO**

| Recurso | URL |
|---------|-----|
| **Repositorio** | https://github.com/transformatedigital/analisis_red |
| **Dashboard Demo** | https://transformatedigital.github.io/analisis_red/ |
| **Instalador Linux** | https://raw.githubusercontent.com/.../install.sh |
| **Script Windows** | https://raw.githubusercontent.com/.../network_scan_windows.ps1 |

---

## 💾 **BACKUP RECOMENDADO**

1. **GitHub** (ya está ahí) ✅
2. **ZIP local** (ya creado) ✅
3. **Google Drive / Dropbox** (opcional)
4. **USB** (opcional)

---

## ✅ **VERIFICACIÓN**

Después de transferir, verifica que todo esté:

```bash
# Ver archivos principales
ls -lh *.py scripts/*.sh

# Debería mostrar:
# - visualizador_triple_vista.py
# - enriquecer_metadata_kais.py
# - vendor_lookup.py
# - scripts/install.sh
# - scripts/network_scan_client_v2_auto.sh
# - scripts/network_scan_windows.ps1
```

---

## 🆘 **SI ALGO FALLA**

### Opción A: Re-descargar desde GitHub
```bash
git clone https://github.com/transformatedigital/analisis_red.git
```

### Opción B: Descargar ZIP directo de GitHub
```bash
wget https://github.com/transformatedigital/analisis_red/archive/refs/heads/main.zip
unzip main.zip
cd analisis_red-main
```

---

## 📞 **SOPORTE**

Si tienes problemas:
- 📧 soporte@transformatedigital.com
- 🌐 https://github.com/transformatedigital/analisis_red/issues

---

<p align="center">
  <strong>¡Listo para usar en cualquier computadora! 🚀</strong>
</p>
