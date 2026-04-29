"""
app.py — Servidor Flask para el Albarán de Solicitud de Radioanálisis
CIEMAT URAyVR — L104-RG01

Versión: SQLite (sin SQL Server, funciona en cualquier hosting)

Requisitos:
    pip install flask flask-cors

Uso local:
    python app.py  →  http://localhost:5000
"""

from flask import Flask, request, jsonify, send_from_directory, session
from flask_cors import CORS
import sqlite3
import os
import secrets
from datetime import datetime

app = Flask(__name__, static_folder='.')
CORS(app, supports_credentials=True)

# ─────────────────────────────────────────────
#  SEGURIDAD — Clave de sesión y contraseña admin
#  Se configuran mediante variables de entorno.
#  Si no se definen, se generan valores aleatorios
#  en cada arranque (sesiones no persistentes entre reinicios).
# ─────────────────────────────────────────────
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))
ADMIN_PASSWORD  = os.environ.get('ADMIN_PASSWORD', 'ciemat2024')

# ─────────────────────────────────────────────
#  RUTA DE LA BASE DE DATOS
#  Auto-detecta Railway y usa /data (volumen persistente).
#  Localmente usa el directorio de trabajo.
#  Se puede sobreescribir con la variable DB_PATH.
# ─────────────────────────────────────────────
_en_railway = bool(
    os.environ.get('RAILWAY_ENVIRONMENT') or
    os.environ.get('RAILWAY_PROJECT_ID') or
    os.environ.get('RAILWAY_SERVICE_NAME')
)
_default_db = '/data/ciemat_radioanalisis.db' if _en_railway else 'ciemat_radioanalisis.db'
DB_PATH = os.environ.get('DB_PATH', _default_db)

# Crear directorio si no existe (necesario en Railway la primera vez)
_db_dir = os.path.dirname(DB_PATH)
if _db_dir:
    os.makedirs(_db_dir, exist_ok=True)


def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # permite acceder por nombre de columna
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """Crea las tablas si no existen. Se llama al arrancar."""
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS Albaranes (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            ref_ura             TEXT,
            ref_cliente_ura     TEXT,
            cliente             TEXT,
            ref_cliente         TEXT,
            tipo_muestra        TEXT,
            pto_muestreo        TEXT,
            fecha_recepcion     TEXT,
            recepcionado_por    TEXT,
            periodo             TEXT,
            enviado_por         TEXT,
            email_reenvio       TEXT,
            fecha               TEXT,
            incidencias         TEXT,
            fecha_creacion      TEXT DEFAULT (datetime('now')),
            fecha_modificacion  TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS Analisis (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            albaran_id  INTEGER NOT NULL,
            analisis    TEXT,
            isotopes    TEXT,
            acumula     INTEGER DEFAULT 0,
            n_acum      TEXT,
            de_tanto    TEXT,
            ref_base    TEXT,
            FOREIGN KEY (albaran_id) REFERENCES Albaranes(id) ON DELETE CASCADE
        );
    """)
    conn.commit()
    conn.close()

# ─────────────────────────────────────────────
#  INICIALIZACIÓN AL IMPORTAR EL MÓDULO
#  Necesario para gunicorn/wsgi (no pasa por __main__)
# ─────────────────────────────────────────────
init_db()


# ─────────────────────────────────────────────
#  API — AUTENTICACIÓN ADMIN
# ─────────────────────────────────────────────

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    d = request.get_json() or {}
    if d.get('password') == ADMIN_PASSWORD:
        session['admin'] = True
        return jsonify({'ok': True})
    return jsonify({'ok': False, 'error': 'Contraseña incorrecta'}), 401

@app.route('/api/admin/logout', methods=['POST'])
def admin_logout():
    session.pop('admin', None)
    return jsonify({'ok': True})

@app.route('/api/admin/check', methods=['GET'])
def admin_check():
    return jsonify({'ok': session.get('admin', False)})


# ─────────────────────────────────────────────
#  SERVIR ARCHIVOS ESTÁTICOS
# ─────────────────────────────────────────────

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/historial')
def historial():
    # El control de acceso lo gestiona el JS del cliente
    # consultando /api/admin/check para no exponer lógica en el servidor
    return send_from_directory('.', 'historial.html')


# ─────────────────────────────────────────────
#  API — CREAR ALBARÁN
# ─────────────────────────────────────────────

@app.route('/api/albaran', methods=['POST'])
def crear_albaran():
    d = request.get_json()
    if not d:
        return jsonify({'error': 'Sin datos'}), 400

    try:
        conn   = get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO Albaranes (
                ref_ura, ref_cliente_ura, cliente, ref_cliente,
                tipo_muestra, pto_muestreo,
                fecha_recepcion, recepcionado_por,
                periodo, enviado_por, email_reenvio, fecha,
                incidencias, fecha_creacion, fecha_modificacion
            )
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,datetime('now'),datetime('now'))
        """, (
            d.get('refURA'),
            d.get('refClienteURA'),
            d.get('cliente'),
            d.get('refCliente'),
            d.get('tipoMuestra'),
            d.get('ptoMuestreo'),
            d.get('fechaRecepcion') or None,
            d.get('recepcionadoPor'),
            d.get('periodo'),
            d.get('enviadoPor'),
            d.get('emailReenvio'),
            d.get('fecha') or None,
            d.get('incidencias')
        ))

        albaran_id = cursor.lastrowid     # equivalente a OUTPUT INSERTED.id

        for a in d.get('analisis', []):
            if a.get('analisis'):
                cursor.execute("""
                    INSERT INTO Analisis (
                        albaran_id, analisis, isotopes,
                        acumula, n_acum, de_tanto, ref_base
                    ) VALUES (?,?,?,?,?,?,?)
                """, (
                    albaran_id,
                    a.get('analisis'),
                    a.get('isotopes', ''),
                    1 if a.get('acumula') else 0,
                    a.get('nAcum', ''),
                    a.get('deTanto', ''),
                    a.get('refBase', '')
                ))

        conn.commit()
        conn.close()
        return jsonify({'ok': True, 'id': albaran_id}), 201

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
#  API — ACTUALIZAR ALBARÁN
# ─────────────────────────────────────────────

@app.route('/api/albaran/<int:albaran_id>', methods=['PUT'])
def actualizar_albaran(albaran_id):
    d = request.get_json()
    if not d:
        return jsonify({'error': 'Sin datos'}), 400

    try:
        conn   = get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            UPDATE Albaranes SET
                ref_ura=?, ref_cliente_ura=?, cliente=?, ref_cliente=?,
                tipo_muestra=?, pto_muestreo=?,
                fecha_recepcion=?, recepcionado_por=?,
                periodo=?, enviado_por=?, email_reenvio=?, fecha=?,
                incidencias=?, fecha_modificacion=datetime('now')
            WHERE id=?
        """, (
            d.get('refURA'),
            d.get('refClienteURA'),
            d.get('cliente'),
            d.get('refCliente'),
            d.get('tipoMuestra'),
            d.get('ptoMuestreo'),
            d.get('fechaRecepcion') or None,
            d.get('recepcionadoPor'),
            d.get('periodo'),
            d.get('enviadoPor'),
            d.get('emailReenvio'),
            d.get('fecha') or None,
            d.get('incidencias'),
            albaran_id
        ))

        cursor.execute("DELETE FROM Analisis WHERE albaran_id=?", (albaran_id,))
        for a in d.get('analisis', []):
            if a.get('analisis'):
                cursor.execute("""
                    INSERT INTO Analisis (
                        albaran_id, analisis, isotopes,
                        acumula, n_acum, de_tanto, ref_base
                    ) VALUES (?,?,?,?,?,?,?)
                """, (
                    albaran_id,
                    a.get('analisis'),
                    a.get('isotopes', ''),
                    1 if a.get('acumula') else 0,
                    a.get('nAcum', ''),
                    a.get('deTanto', ''),
                    a.get('refBase', '')
                ))

        conn.commit()
        conn.close()
        return jsonify({'ok': True, 'id': albaran_id})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
#  API — OBTENER UN ALBARÁN
# ─────────────────────────────────────────────

@app.route('/api/albaran/<int:albaran_id>', methods=['GET'])
def obtener_albaran(albaran_id):
    try:
        conn   = get_conn()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM Albaranes WHERE id=?", (albaran_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({'error': 'No encontrado'}), 404

        albaran = dict(row)

        cursor.execute(
            "SELECT * FROM Analisis WHERE albaran_id=? ORDER BY id",
            (albaran_id,)
        )
        albaran['analisis'] = [dict(r) for r in cursor.fetchall()]

        conn.close()
        return jsonify(albaran)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
#  API — LISTAR ALBARANES (búsqueda + paginación)
# ─────────────────────────────────────────────

@app.route('/api/albaranes', methods=['GET'])
def listar_albaranes():
    pagina  = int(request.args.get('pagina', 1))
    por_pag = int(request.args.get('por_pagina', 20))
    buscar  = request.args.get('buscar', '').strip()
    desde   = request.args.get('desde', '')
    hasta   = request.args.get('hasta', '')

    offset = (pagina - 1) * por_pag

    where  = []
    params = []

    if buscar:
        where.append("""(
            cliente          LIKE ? OR
            ref_ura          LIKE ? OR
            ref_cliente      LIKE ? OR
            tipo_muestra     LIKE ? OR
            pto_muestreo     LIKE ? OR
            recepcionado_por LIKE ?
        )""")
        like = f'%{buscar}%'
        params.extend([like] * 6)

    if desde:
        where.append("fecha_recepcion >= ?")
        params.append(desde)

    if hasta:
        where.append("fecha_recepcion <= ?")
        params.append(hasta)

    where_sql = ('WHERE ' + ' AND '.join(where)) if where else ''

    try:
        conn   = get_conn()
        cursor = conn.cursor()

        cursor.execute(
            f"SELECT COUNT(*) FROM Albaranes {where_sql}",
            params
        )
        total = cursor.fetchone()[0]

        # SQLite usa LIMIT … OFFSET (en vez de OFFSET … FETCH)
        cursor.execute(f"""
            SELECT id, ref_ura, cliente, ref_cliente, tipo_muestra,
                   pto_muestreo, fecha_recepcion, fecha_creacion, fecha_modificacion
            FROM Albaranes
            {where_sql}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        """, params + [por_pag, offset])

        albaranes = [dict(r) for r in cursor.fetchall()]
        conn.close()
        return jsonify({'albaranes': albaranes, 'total': total})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ─────────────────────────────────────────────
#  API — ELIMINAR ALBARÁN
# ─────────────────────────────────────────────

@app.route('/api/albaran/<int:albaran_id>', methods=['DELETE'])
def eliminar_albaran(albaran_id):
    try:
        conn   = get_conn()
        cursor = conn.cursor()
        # CASCADE borra Analisis automáticamente (PRAGMA foreign_keys=ON)
        cursor.execute("DELETE FROM Albaranes WHERE id=?", (albaran_id,))
        conn.commit()
        conn.close()
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/ver-datos')
def ver_datos():
    conn = get_conn()
    albaranes = conn.execute("SELECT * FROM Albaranes ORDER BY id DESC").fetchall()
    conn.close()
    html = "<h2>Albaranes guardados</h2><table border='1'>"
    html += "<tr><th>ID</th><th>Ref URA</th><th>Cliente</th><th>Tipo muestra</th><th>Fecha recepción</th><th>Creado</th></tr>"
    for row in albaranes:
        html += f"<tr><td>{row['id']}</td><td>{row['ref_ura']}</td><td>{row['cliente']}</td><td>{row['tipo_muestra']}</td><td>{row['fecha_recepcion']}</td><td>{row['fecha_creacion']}</td></tr>"
    html += "</table>"
    return html
# ─────────────────────────────────────────────
#  ARRANQUE
# ─────────────────────────────────────────────

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print("=" * 55)
    print("  CIEMAT URAyVR — Servidor de Albaranes (SQLite)")
    print(f"  Accede en: http://localhost:{port}")
    print(f"  Historial:  http://localhost:{port}/historial")
    print(f"  Base de datos: {DB_PATH}")
    print("=" * 55)
    app.run(host='0.0.0.0', port=port, debug=False)