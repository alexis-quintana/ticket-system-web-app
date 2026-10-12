# Módulo 6 — Dashboard, reportes y API REST.
# En el Grupo B lo absorben los integrantes 4 y 5. Mientras se desarrolla, /reportes
# muestra una página "en construcción" (en lugar de 404). Quien implemente los reportes
# reemplaza el cuerpo de la función y la plantilla; el nombre del Blueprint se mantiene.
from flask import Blueprint, render_template

from modules.auth import roles_required

bp = Blueprint("reportes", __name__)


@bp.route("/reportes")
@roles_required("Administrador")      # en el menú, Reportes solo aparece al Administrador
def index():
    return render_template("reportes/construccion.html")
