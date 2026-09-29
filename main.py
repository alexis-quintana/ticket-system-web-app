from flask import Flask

from db import obtener_conexion

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Módulos del sistema.
# Cada integrante descomenta SOLO sus 2 líneas, después de crear su archivo.
# ---------------------------------------------------------------------------

# Módulo 1 — Autenticación y usuarios (Montenegro)
# from modules.auth import bp as auth_bp
# app.register_blueprint(auth_bp)

# Módulo 2 — Registro de tickets con evidencias (Timaná)
# from modules.tickets import bp as tickets_bp
# app.register_blueprint(tickets_bp)

# Módulo 3 — Asignación, estados e historial (Seminario)
# from modules.historial import bp as historial_bp
# app.register_blueprint(historial_bp)

# Módulo 4 — SLA y semáforo visual (Ordoñez)
# from modules.sla import bp as sla_bp
# app.register_blueprint(sla_bp)

# Módulo 5 — Notificaciones internas (Quintana)
# from modules.notificaciones import bp as notificaciones_bp
# app.register_blueprint(notificaciones_bp)


# ---------------------------------------------------------------------------
# Rutas generales
# ---------------------------------------------------------------------------
@app.route("/")
def inicio():
    return "<p>Sistema de Tickets TI en marcha</p>"


@app.route("/probandoconexion")
def probandoconexion():
    try:
        obtener_conexion()
        return "<p>Conexión exitosa</p>"
    except Exception as e:
        return "<p>Error: " + repr(e) + "</p>"


if __name__ == "__main__":
    app.run(debug=True)