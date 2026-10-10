"""Módulo 5 (Quintana): comentarios del ticket.

El comentario se guarda en `ticket_comentarios`; el trigger `trg_comentarios_ai` crea la
notificación para el solicitante y el técnico asignado (menos para quien comenta).
Se muestra en el detalle con {% include "historial/_comentarios.html" %}.
"""
from flask import Blueprint, abort, flash, redirect, session, request, url_for

from db import obtener_conexion
from modules.auth import roles_required

bp = Blueprint("comentarios", __name__)

MAX_COMENTARIO = 1000


def _ticket_visible(cur, ticket_id):
    """Ticket de la empresa activa que el usuario puede ver, o None."""
    cur.execute("SELECT id, estado, solicitante_id, tecnico_id FROM tickets WHERE id=%s AND empresa_id=%s",
                (ticket_id, session["empresa_id"]))
    t = cur.fetchone()
    if not t:
        return None
    if session["rol"] == "Solicitante" and t["solicitante_id"] != session["usuario_id"]:
        return None
    return t


def _puede_comentar(t):
    """Administrador, solicitante dueño o técnico asignado; el ticket cerrado ya no admite cambios."""
    if t["estado"] == "Cerrado":
        return False
    if session["rol"] == "Administrador":
        return True
    return session["usuario_id"] in (t["solicitante_id"], t["tecnico_id"])


@bp.app_template_global("comentarios_de")
def comentarios_de(ticket_id):
    """Lista de comentarios del ticket (más antiguos primero) para la plantilla del detalle."""
    con = obtener_conexion()
    try:
        with con.cursor() as cur:
            cur.execute(
                "SELECT c.id, c.comentario, c.created_at, c.usuario_id, "
                "CONCAT(p.nombres, ' ', p.apellidos) AS autor, r.nombre AS rol "
                "FROM ticket_comentarios c "
                "JOIN usuarios u ON u.id = c.usuario_id "
                "JOIN personas p ON p.id = u.persona_id "
                "JOIN roles r ON r.id = u.rol_id "
                "WHERE c.ticket_id=%s AND c.empresa_id=%s ORDER BY c.created_at, c.id",
                (ticket_id, session["empresa_id"]))
            return cur.fetchall()
    finally:
        con.close()


@bp.app_template_global("puede_comentar")
def puede_comentar(ticket):
    return _puede_comentar(ticket)


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

    con = obtener_conexion()
    try:
        with con.cursor() as cur:
            t = _ticket_visible(cur, ticket_id)
            if not t:
                abort(404)
            if not _puede_comentar(t):
                flash("No puedes comentar en este ticket.", "danger")
                return redirect(destino)
            cur.execute(
                "INSERT INTO ticket_comentarios (empresa_id, ticket_id, usuario_id, comentario) "
                "VALUES (%s, %s, %s, %s)",
                (session["empresa_id"], ticket_id, session["usuario_id"], texto))
        con.commit()
    finally:
        con.close()
    flash("Comentario publicado.", "success")
    return redirect(destino)
