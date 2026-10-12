# Módulo 5 (Quintana): comentarios del ticket.
# El SQL está en models/comentario.py; el trigger trg_comentarios_ai avisa al solicitante y al técnico.
# Se muestra en el detalle con {% include "historial/_comentarios.html" %}.
from flask import Blueprint, abort, flash, redirect, session, request, url_for

from models.comentario import Comentario, MAX_COMENTARIO
from modules.auth import respuesta, roles_required

bp = Blueprint("comentarios", __name__)


# Administrador, solicitante dueño o técnico asignado; el ticket cerrado ya no admite cambios.
def _puede_comentar(t):
    if t["estado"] == "Cerrado":
        return False
    if session["rol"] == "Administrador":
        return True
    return session["usuario_id"] in (t["solicitante_id"], t["tecnico_id"])


# Ticket que el usuario de la sesión puede ver, o None.
def _ticket_visible(ticket_id):
    return Comentario.ticket_visible(ticket_id, session["empresa_id"], session["usuario_id"], session["rol"])


# Lista de comentarios del ticket (más antiguos primero) para la plantilla del detalle.
@bp.app_template_global("comentarios_de")
def comentarios_de(ticket_id):
    return Comentario.listar(ticket_id, session["empresa_id"])


@bp.app_template_global("puede_comentar")
def puede_comentar(ticket):
    return _puede_comentar(ticket)


# 1. Pantalla: el formulario del detalle del ticket
@bp.route("/tickets/<int:ticket_id>/comentarios", methods=["POST"])
@roles_required()
def comentar(ticket_id):
    texto = request.form.get("comentario", "").strip()
    destino = url_for("historial.ver_historial", ticket_id=ticket_id) + "#comentarios"
    if not texto:
        flash("Escribe un comentario antes de enviarlo.", "danger")
        return redirect(destino)
    if len(texto) > MAX_COMENTARIO:
        flash("El comentario no puede superar %d caracteres." % MAX_COMENTARIO, "danger")
        return redirect(destino)
    t = _ticket_visible(ticket_id)
    if not t:
        abort(404)
    if not _puede_comentar(t):
        flash("No puedes comentar en este ticket.", "danger")
        return redirect(destino)
    Comentario.crear(session["empresa_id"], ticket_id, session["usuario_id"], texto)
    flash("Comentario publicado.", "success")
    return redirect(destino)


# 2. API de comentarios: GET lista y POST crea, se prueba en Postman con la sesión iniciada
@bp.route("/api/tickets/<int:ticket_id>/comentarios")
@roles_required()
def api_listar(ticket_id):
    try:
        if not _ticket_visible(ticket_id):
            return respuesta(0, None, "El ticket no existe.", 404)
        lista = list()
        for c in Comentario.listar(ticket_id, session["empresa_id"]):
            lista.append(c.a_diccionario())
        return respuesta(1, lista, "Lista de comentarios generada correctamente en JSON.")
    except Exception as e:
        return respuesta(0, None, repr(e), 500)


@bp.route("/api/tickets/<int:ticket_id>/comentarios", methods=["POST"])
@roles_required()
def api_crear(ticket_id):
    try:
        datos = request.get_json(silent=True) or request.form
        texto = str(datos.get("comentario", "")).strip()
        t = _ticket_visible(ticket_id)
        if not t:
            return respuesta(0, None, "El ticket no existe.", 404)
        if not _puede_comentar(t):
            return respuesta(0, None, "No puedes comentar en este ticket.", 403)
        if not texto or len(texto) > MAX_COMENTARIO:
            return respuesta(0, None, "El comentario debe tener entre 1 y %d caracteres." % MAX_COMENTARIO, 400)
        comentario = Comentario.crear(session["empresa_id"], ticket_id, session["usuario_id"], texto)
        return respuesta(1, comentario.a_diccionario(), "Comentario publicado.", 201)
    except Exception as e:
        return respuesta(0, None, repr(e), 500)
