from datetime import datetime

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from models.notificacion import Notificacion, TIPOS
from modules.auth import respuesta, roles_required

bp = Blueprint("notificaciones", __name__)


# Ayudas
# Texto relativo corto: 'hace 5 min', 'hace 3 h', 'hace 2 d'.
def _hace(fecha):
    segundos = max(0, int((datetime.now() - fecha).total_seconds()))
    if segundos < 60:
        return "hace un momento"
    if segundos < 3600:
        return "hace %d min" % (segundos // 60)
    if segundos < 86400:
        return "hace %d h" % (segundos // 3600)
    return "hace %d d" % (segundos // 86400)


# fetch() de la página avisa con este encabezado; el formulario normal sigue funcionando sin JS.
def _quiere_json():
    return request.headers.get("X-Requested-With") == "fetch"


# Igual que crearcancion() de la clase: arma un diccionario que luego jsonify convierte en JSON.
def crearnotificacion(p_id, p_ticket_id, p_tipo, p_mensaje, p_leida, p_creada):
    notificacion = dict()
    notificacion['id'] = p_id
    notificacion['ticket_id'] = p_ticket_id
    notificacion['codigo_ticket'] = "TK-" + str(p_ticket_id).zfill(4)
    notificacion['tipo'] = p_tipo
    notificacion['titulo'] = TIPOS[p_tipo]
    notificacion['mensaje'] = p_mensaje
    notificacion['leida'] = bool(p_leida)
    notificacion['creada'] = p_creada.isoformat()
    notificacion['hace'] = _hace(p_creada)
    notificacion['url'] = url_for("tickets.detalle", ticket_id=p_ticket_id)
    return notificacion


# Convierte un objeto Notificacion en el diccionario que devuelve jsonify.
def a_diccionario(n):
    return crearnotificacion(n.id, n.ticket_id, n.tipo, n.mensaje, n.leida, n.created_at)


# 1. Pantalla y acciones web
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
        no_leidas=sum(1 for n in todas if not n.leida),
        tipos=TIPOS,
        lectura=lectura,
        tipo=tipo)


@bp.route("/notificaciones/<int:notificacion_id>/leer", methods=["POST"])
@roles_required()
def marcar_leida(notificacion_id):
    n = Notificacion.obtener(notificacion_id, session["usuario_id"])
    if n:
        n.marcar_leida()
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
    n = Notificacion.obtener(notificacion_id, session["usuario_id"])
    borradas = n.eliminar() if n else 0
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


# 2. Rutas JSON de la campana
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
    items = [a_diccionario(n) for n in Notificacion.recientes(usuario_id)]
    return jsonify(no_leidas=Notificacion.contar_no_leidas(usuario_id), items=items)


# 3. API de notificaciones: se prueba en Postman con la sesión iniciada
# Solo GET: lista y detalle (marcar y eliminar se hacen desde la web con POST)
@bp.route('/api/notificaciones')
@roles_required()
def api_listar():
    rpta = dict()
    listaNotificaciones = list()
    try:
        for n in Notificacion.listar(session['usuario_id']):
            listaNotificaciones.append(a_diccionario(n))
        rpta['code'] = 1
        rpta['data'] = listaNotificaciones
        rpta['msge'] = 'Lista de notificaciones generada correctamente en json'
    except Exception as e:
        rpta['code'] = 0
        rpta['data'] = None
        rpta['msge'] = repr(e)
    return jsonify(rpta)


@bp.route('/api/notificaciones/<strId>')
@roles_required()
def api_detalle(strId):
    try:
        n = Notificacion.obtener(int(strId), session['usuario_id'])
        if n:
            return respuesta(1, a_diccionario(n), 'Notificación encontrada')
        return respuesta(0, None, 'La notificación no existe', 404)
    except ValueError:
        return respuesta(0, None, 'El id de la notificación no es válido', 400)
    except Exception as e:
        return respuesta(0, None, repr(e), 500)
