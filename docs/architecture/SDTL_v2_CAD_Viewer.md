# SDTL 2.0 CAD Viewer — primera iteración
Rama independiente; no sustituye el visor 3D v1.9.5.
## Auditoría estática
Frontend existente: Babylon.js 9.17.0, Vite 8.1.5, Vitest 4.1.10, jsdom 29.1.1, package-lock presente. Backend: ezdxf, Shapely, Pydantic v2, PyMuPDF. No se encontró manifiesto Python global ni CI en el árbol revisado. Los rangos nuevos son provisionales, no lock reproducible.
Las pruebas CAD existentes dependen de DXF locales ignorados por git. La prueba de integración ElectricalRoom crea JSON predefinido, no valida procesamiento real. No se ejecutaron las suites existentes en esta sesión.
## Ejecución local
Desde raíz, Windows PowerShell:
```
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-cad-viewer.txt
.venv\Scripts\python.exe -m pytest tests/test_cad_viewer_v2.py
.venv\Scripts\python.exe -m backend.cad_viewer.server
```
Abrir http://127.0.0.1:8765. Seleccionar DXF local. No subir planos al repositorio. El servidor escucha solo loopback; no desplegar públicamente.
## Aceptación LOM-OC-06 (pendiente de ejecución)
Comparar contra AutoCAD: extensión visible, colores, cotas, bloques, textos y grosores; confirmar unidades y conteo mediante inspector; ocultar capas, buscar texto, probar zoom/pan. Registrar tiempo y discrepancias. No se adjunta el plano.
## Límites
SVG generado por ezdxf, no DWG nativo. El inspector selecciona desde inventario, no picking gráfico. Capas: ocultamiento por regeneración, no activación de capas originalmente apagadas/congeladas. Sin mediciones OSNAP, IA, MCP ni validación normativa. Pruebas nuevas sin ejecutar en esta sesión.
