# Dashboard Publicado

Este directorio contiene el dashboard publicado en GitHub Pages.

## Cómo Actualizar el Dashboard

Después de generar un nuevo análisis:

```bash
# 1. Generar el dashboard con tus datos
python3 visualizador_triple_vista.py diagnostico_Cliente_YYYYMMDD.zip

# 2. Copiar el dashboard generado aquí
cp gemelo_*/dashboard_triple_vista.html docs/index.html

# 3. Commit y push
git add docs/index.html
git commit -m "Actualizar dashboard publicado"
git push origin main
```

El dashboard estará disponible en:
**https://transformatedigital.github.io/analisis_red/**

## Notas de Seguridad

⚠️ **IMPORTANTE:** No publiques dashboards con datos confidenciales de clientes.

- Usa datos anonimizados o de ejemplo para la versión pública
- Para enviar análisis reales a clientes, usa el archivo HTML directamente (por email)
- GitHub Pages es público - cualquiera con la URL puede ver el contenido
