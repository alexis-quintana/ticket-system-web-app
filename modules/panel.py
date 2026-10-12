# INTEGRACIÓN: páginas generales del sistema (Inicio, Dashboard, Perfil, Configuración).
# No pertenecen a ningún módulo; el SQL y las reglas están en models/panel.py (clases Resumen y Perfil).
from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from models.panel import Resumen, Perfil, PerfilError
from modules.auth import roles_required
from modules.sla import plazos_empresa

bp = Blueprint("panel", __name__)


# Los datos del usuario que necesita el modelo (siempre salen de la sesión, nunca del formulario)
def usuario_sesion():
    return dict(empresa_id=session["empresa_id"], usuario_id=session["usuario_id"], rol=session["rol"])


@bp.route("/inicio")
@roles_required()
def inicio():
    return render_template("panel/inicio.html", recientes=Resumen.recientes(usuario_sesion()))


@bp.route("/dashboard")
@roles_required()
def dashboard():
    return render_template("panel/dashboard.html", **Resumen.dashboard(usuario_sesion()))


def _mostrar_perfil(estado=200, **extra):
    datos, admins = Perfil.datos(usuario_sesion())
    return render_template("panel/perfil.html", datos=datos, admins=admins, **extra), estado


@bp.route("/perfil")
@roles_required()
def perfil():
    return _mostrar_perfil()


# ---------- Edición de la propia cuenta: teléfono y contraseña ----------
@bp.route("/perfil/telefono", methods=["POST"])
@roles_required()
def perfil_telefono():
    telefono = request.form.get("telefono", "").strip()
    try:
        con_telefono = Perfil.cambiar_telefono(session["usuario_id"], telefono)
    except PerfilError as e:
        return _mostrar_perfil(400, error_telefono=str(e), telefono_escrito=telefono)
    flash("Teléfono actualizado." if con_telefono else "Teléfono eliminado de tu ficha.", "success")
    return redirect(url_for("panel.perfil"))


@bp.route("/perfil/password", methods=["POST"])
@roles_required()
def perfil_password():
    try:
        Perfil.cambiar_password(session["usuario_id"], request.form.get("actual", ""),
                                request.form.get("nueva", ""), request.form.get("confirmar", ""))
    except PerfilError as e:
        return _mostrar_perfil(400, error_password=str(e))
    flash("Contraseña actualizada. Úsala la próxima vez que inicies sesión.", "success")
    return redirect(url_for("panel.perfil"))


@bp.route("/configuracion")
@roles_required()
def configuracion():
    return render_template("panel/configuracion.html", sla_horas=plazos_empresa(session["empresa_id"]))
