"""Módulo 5 (Quintana): notificaciones internas.

Controlador: recibe la petición, llama a la clase `Notificacion` (models/notificacion.py) y responde.
Tres partes:
  1. Pantallas y acciones web (/notificaciones ...), que siguen funcionando sin JavaScript.
  2. Rutas JSON que usa la campana (/notificaciones/contador y /notificaciones/recientes).
  3. API (/api/notificaciones ...) con jsonify. Mismo formato de respuesta que el ejemplo de clase:
     {"code": 1 o 0, "data": ..., "msge": "mensaje"}.
Las notificaciones de asignación, cambio de estado y comentario las crean los triggers de la base de datos.
"""
from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from models.notificacion import Notificacion, TIPOS
from modules.auth import roles_required

bp = Blueprint("notificaciones", __name__)


# ---------------------------------------------------------------------------
# Ayudas
# ---------------------------------------------------------------------------
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


def crearnotificacion(n):
    """Fila de la base de datos -> diccionario listo para jsonify (igual que crearcancion() de la clase)."""
    return {
        "id": n["id"],
        "ticket_id": n["ticket_id"],
        "codigo_ticket": "TK-" + str(n["ticket_id"]).zfill(4),
        "tipo": n["tipo"],
        "titulo": TIPOS[n["tipo"]],
        "mensaje": n["mensaje"],
        "leida": bool(n["leida"]),
        "creada": n["created_at"].isoformat(),
        "hace": _hace(n["created_at"]),
        "url": url_for("tickets.detalle", ticket_id=n["ticket_id"]),
    }


# ---------------------------------------------------------------------------
# 1. Pantalla y acciones web
# ---------------------------------------------------------------------------
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


@bp.route("/notificaciones/<int:notificacion_id>/eliminar", methods=["POST"])
@roles_required()
def eliminar(notificacion_id):
    borradas = Notificacion.eliminar(notificacion_id, session["usuario_id"])
    if _quiere_json():
        return jsonify(ok=bool(borradas), no_leidas=Notificacion.contar_no_leidas(session["usuario_id"]))
    flash("Notificación eliminada." if borradas else "La notificación ya no existe.", "success" if borradas else "info")
    return redirect(url_for("notificaciones.lista"))


@bp.route("/notificaciones/eliminar-leidas", methods=["POST"])
@roles_required()
def eliminar_leidas():
    borradas = Notificacion.eliminar_leidas(session["usuario_id"])
    if _quiere_json():
        return jsonify(ok=True, eliminadas=borradas, no_leidas=Notificacion.contar_no_leidas(session["usuario_id"]))
    flash("Se eliminaron %d notificaciones leídas." % borradas if borradas else "No tienes notificaciones leídas.",
          "success" if borradas else "info")
    return redirect(url_for("notificaciones.lista"))


# ---------------------------------------------------------------------------
# 2. Rutas JSON de la campana (se consultan desde todas las pantallas)
# ---------------------------------------------------------------------------
@bp.route("/notificaciones/contador")
def contador():
    # Sin sesión responde 401 en JSON.
    if "usuario_id" not in session:
        return jsonify(no_leidas=0), 401
    return jsonify(no_leidas=Notificacion.contar_no_leidas(session["usuario_id"]))


@bp.route("/notificaciones/recientes")
def recientes():
    if "usuario_id" not in session:
        return jsonify(no_leidas=0, items=[]), 401
    usuario_id = session["usuario_id"]
    items = [crearnotificacion(n) for n in Notificacion.recientes(usuario_id)]
    return jsonify(no_leidas=Notificacion.contar_no_leidas(usuario_id), items=items)


# ---------------------------------------------------------------------------
# 3. API de notificaciones (JSON). Se prueba con Postman. Requiere sesión iniciada
#    (primero se hace POST /login desde el navegador o Postman).
#    Formato de respuesta, igual que /generandojson de la clase:
#        code = 1 -> todo bien      code = 0 -> hubo un error (el detalle va en msge)
#    GET    /api/notificaciones?lectura=&tipo=   listar las del usuario
#    GET    /api/notificaciones/<id>             detalle de una
# ---------------------------------------------------------------------------
@bp.route("/api/notificaciones", methods=["GET"])
@roles_required()
def api_listar():
    rpta = dict()
    try:
        usuario_id = session["usuario_id"]
        lectura = request.args.get("lectura", "todas")
        tipo = request.args.get("tipo", "")
        if lectura not in ("todas", "leidas", "no_leidas"):
            raise ValueError("El filtro lectura debe ser todas, leidas o no_leidas")
        if tipo and tipo not in TIPOS:
            raise ValueError("El filtro tipo debe ser: " + ", ".join(TIPOS))
        listaNotificaciones = list()
        for n in Notificacion.listar(usuario_id, lectura, tipo):
            listaNotificaciones.append(crearnotificacion(n))
        rpta["code"] = 1
        rpta["data"] = listaNotificaciones
        rpta["no_leidas"] = Notificacion.contar_no_leidas(usuario_id)
        rpta["msge"] = "Lista de notificaciones generada correctamente en json"
    except Exception as e:
        rpta["code"] = 0
        rpta["data"] = None
        rpta["msge"] = repr(e)
    return jsonify(rpta)


@bp.route("/api/notificaciones/<int:notificacion_id>", methods=["GET"])
@roles_required()
def api_detalle(notificacion_id):
    rpta = dict()
    try:
        n = Notificacion.obtener(notificacion_id, session["usuario_id"])
        if not n:
            raise LookupError("La notificación no existe")
        rpta["code"] = 1
        rpta["data"] = crearnotificacion(n)
        rpta["msge"] = "Notificación encontrada"
    except Exception as e:
        rpta["code"] = 0
        rpta["data"] = None
        rpta["msge"] = repr(e)
    return jsonify(rpta)
