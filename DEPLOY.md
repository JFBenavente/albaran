# 🚀 Guía de despliegue en Railway — CIEMAT Albaranes

## Archivos necesarios en tu carpeta
```
albaran/
├── index.html        ← SIN CAMBIOS
├── historial.html    ← SIN CAMBIOS
├── app.py            ← NUEVO (SQLite, reemplaza el anterior)
├── requirements.txt  ← NUEVO
└── Procfile          ← NUEVO
```
> ⚠️ Elimina el archivo schema.sql antiguo — ya no hace falta.
> ⚠️ NO hace falta instalar SQL Server ni ODBC.

---

## Paso 1 — Crear cuenta en GitHub (gratis)
1. Ve a https://github.com y regístrate
2. Click en **"New repository"**
3. Nombre: `albaran-ciemat` (privado si quieres)
4. Click **"Create repository"**
5. Sube los 5 archivos de la carpeta arrastrándolos o con:
   ```bash
   git init
   git add .
   git commit -m "primer commit"
   git remote add origin https://github.com/TU_USUARIO/albaran-ciemat.git
   git push -u origin main
   ```

---

## Paso 2 — Crear cuenta en Railway (gratis, sin tarjeta)
1. Ve a https://railway.app
2. **"Login with GitHub"** — usa la misma cuenta de GitHub
3. Verifica tu cuenta con email

---

## Paso 3 — Crear el proyecto en Railway
1. Click **"New Project"**
2. Selecciona **"Deploy from GitHub repo"**
3. Elige el repositorio `albaran-ciemat`
4. Railway detecta Python automáticamente ✅

---

## Paso 4 — Configurar el volumen para la base de datos
> Esto es importante: sin volumen, los datos se borran al reiniciar.

1. En tu proyecto Railway, click en el servicio
2. Ve a la pestaña **"Volumes"**
3. Click **"Add Volume"**
4. Mount path: `/data`
5. Click **"Add"**

6. Ve a la pestaña **"Variables"** y añade:
   ```
   DB_PATH = /data/ciemat_radioanalisis.db
   ```

---

## Paso 5 — Obtener la URL pública
1. Ve a la pestaña **"Settings"** del servicio
2. En **"Networking"** → click **"Generate Domain"**
3. Te da una URL tipo:
   ```
   https://albaran-ciemat-production.up.railway.app
   ```

¡Eso es todo! Mándales esa URL a los clientes externos.

---

## Funcionamiento
- **Formulario:** https://tu-url.railway.app
- **Historial:**  https://tu-url.railway.app/historial
- Los datos se guardan en SQLite en `/data/` (persistente)
- El `index.html` funciona exactamente igual que antes

---

## Plan gratuito de Railway
| Límite | Detalle |
|--------|---------|
| Horas | 500 horas/mes gratis |
| RAM | 512 MB (más que suficiente) |
| Almacenamiento | 1 GB para la BD |
| URL | HTTPS pública incluida |

Para uso profesional continuo: $5/mes elimina el límite de horas.

---

## Prueba local antes de subir
```bash
pip install flask flask-cors
python app.py
# Abre http://localhost:5000
```
