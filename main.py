from flask import Flask, redirect, session, url_for

from db import obtener_conexion

app = Flask(__name__)


# ---------------------------------------------------------------------------
# Módulos del sistema.
# Cada integrante descomenta SOLO sus 2 líneas, después de crear su archivo.
# ---------------------------------------------------------------------------

# Módulo 1 — Autenticación y usuarios (Montenegro)
from modules.auth import bp as auth_bp
app.register_blueprint(auth_bp)

# Módulo 2 — Registro de tickets con evidencias (Timaná)
from modules.tickets import bp as tickets_bp
app.register_blueprint(tickets_bp)

# Módulo 3 — Asignación, estados e historial (Seminario)
from modules.historial import bp as historial_bp
app.register_blueprint(historial_bp)

# Módulo 4 — SLA y semáforo visual (Ordoñez)
from modules.sla import bp as sla_bp
app.register_blueprint(sla_bp)

# Módulo 5 — Notificaciones internas (Quintana)
from modules.notificaciones import bp as notificaciones_bp
app.register_blueprint(notificaciones_bp)

# Módulo 5 — Comentarios del ticket (generan la notificación de tipo comentario)
from modules.comentarios import bp as comentarios_bp
app.register_blueprint(comentarios_bp)

# Módulo 6 — Reportes (por ahora: página "en construcción")
from modules.reportes import bp as reportes_bp
app.register_blueprint(reportes_bp)

# Páginas generales: Inicio, Dashboard, Perfil y Configuración (integración)
from modules.panel import bp as panel_bp
app.register_blueprint(panel_bp)


# ---------------------------------------------------------------------------
# Formato único del código de ticket en todas las plantillas: {{ t.id|codigo_ticket }} -> TK-0007
# (en JS se arma igual: 'TK-' + id con 4 dígitos)
# ---------------------------------------------------------------------------
@app.template_filter("codigo_ticket")
def codigo_ticket(ticket_id):
    return "TK-" + str(ticket_id).zfill(4)


# ---------------------------------------------------------------------------
# Rutas generales
# ---------------------------------------------------------------------------
@app.route("/")
def inicio():
    # Sin sesión va al login; con sesión, a la página de inicio del sistema
    if "usuario_id" not in session:
        return redirect(url_for("auth.login"))
    return redirect("/inicio")


@app.route("/probandoconexion")
def probandoconexion():
    try:
        obtener_conexion()
        return "<p>Conexión exitosa</p>"
    except Exception as e:
        return "<p>Error: " + repr(e) + "</p>"


if __name__ == "__main__":
    app.run(debug=True)