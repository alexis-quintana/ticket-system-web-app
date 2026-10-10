from datetime import datetime

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from models.notificacion import Notificacion, TIPOS
from modules.auth import roles_required

bp = Blueprint("notificaciones", __name__)


def _hace(fecha):
    """Texto relativo corto: 'hace 5 min', 'hace 3 h', 'hace 2 d'."""
    segundos = max(0, int((datetime.now() - fecha).total_seconds()))
    if segundos < 60:
        return "hace un momento"
    if segundos < 3600:
        return "hace %d min" % (segundos // 60)
    if segundos < 86400:
        return "hace %d h" % (segundos // 3600)
    return "hace %d d" % (segundos // 86400)


def _quiere_json():
    """fetch() de la página avisa con este encabezado; el formulario normal sigue funcionando sin JS."""
    return request.headers.get("X-Requested-With") == "fetch"


@bp.route("/notificaciones")
@roles_required()
def lista():
    usuario_id = session["usuario_id"]
    lectura = request.args.get("lectura", "todas")
    tipo = request.args.get("tipo", "")
    todas = Notificacion.listar(usuario_id)
    mostradas = Notificacion.listar(usuario_id, lectura, tipo)
    return render_template(
        "notificaciones/lista.html",
        notificaciones=mostradas,
        total=len(todas),
        no_leidas=sum(1 for n in todas if not n["leida"]),
        tipos=TIPOS,
        lectura=lectura,
        tipo=tipo)


@bp.route("/notificaciones/contador")
def contador():
    # Lo consulta la campana en todas las pantallas; sin sesión responde 401 en JSON.
    if "usuario_id" not in session:
        return jsonify(no_leidas=0), 401
    return jsonify(no_leidas=Notificacion.contar_no_leidas(session["usuario_id"]))


@bp.route("/notificaciones/recientes")
def recientes():
    # Alimenta el desplegable de la campana: contador + últimas notificaciones.
    if "usuario_id" not in session:
        return jsonify(no_leidas=0, items=[]), 401
    usuario_id = session["usuario_id"]
    items = [{
        "id": n["id"],
        "tipo": n["tipo"],
        "titulo": TIPOS[n["tipo"]],
        "mensaje": n["mensaje"],
        "leida": bool(n["leida"]),
        "hace": _hace(n["created_at"]),
        "url": url_for("tickets.detalle", ticket_id=n["ticket_id"]),
    } for n in Notificacion.recientes(usuario_id)]
    return jsonify(no_leidas=Notificacion.contar_no_leidas(usuario_id), items=items)


@bp.route("/notificaciones/<int:notificacion_id>/leer", methods=["POST"])
@roles_required()
def marcar_leida(notificacion_id):
    Notificacion.marcar_leida(notificacion_id, session["usuario_id"])
    if _quiere_json():
        return jsonify(ok=True, no_leidas=Notificacion.contar_no_leidas(session["usuario_id"]))
    return redirect(url_for("notificaciones.lista"))


@bp.route("/notificaciones/leer-todas", methods=["POST"])
@roles_required()
def marcar_todas():
    Notificacion.marcar_todas(session["usuario_id"])
    if _quiere_json():
        return jsonify(ok=True, no_leidas=0)
    return redirect(url_for("notificaciones.lista"))