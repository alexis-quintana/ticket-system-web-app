from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from models.notificacion import Notificacion, TIPOS
from modules.auth import roles_required

bp = Blueprint("notificaciones", __name__)


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


@bp.route("/notificaciones/<int:notificacion_id>/leer", methods=["POST"])
@roles_required()
def marcar_leida(notificacion_id):
    Notificacion.marcar_leida(notificacion_id, session["usuario_id"])
    return redirect(url_for("notificaciones.lista"))


@bp.route("/notificaciones/leer-todas", methods=["POST"])
@roles_required()
def marcar_todas():
    Notificacion.marcar_todas(session["usuario_id"])
    return redirect(url_for("notificaciones.lista"))