"""Controlador del Módulo 3 (Seminario): asignación, estados e historial.

El SQL y las reglas están en models/historial.py (clase Historial); aquí no hay cursor.execute.
"""
from datetime import datetime

from flask import Blueprint, render_template, request, jsonify, session, abort, current_app
from werkzeug.exceptions import BadRequest, HTTPException

from models.historial import Historial, HistorialError, ESTADOS, PRIORIDADES
from modules.auth import roles_required

bp = Blueprint("historial", __name__)


def usuario_sesion():
    """Los datos del usuario que necesita el modelo (siempre salen de la sesión, nunca del formulario)."""
    return dict(empresa_id=session["empresa_id"], usuario_id=session["usuario_id"], rol=session["rol"])


# ---------- Filtro Jinja: fecha relativa para la línea de tiempo ----------
@bp.app_template_filter("relativo")
def relativo(fecha):
    if not fecha:
        return ""
    seg = (datetime.now() - fecha).total_seconds()
    if seg < 60:
        return "hace un momento"
    if seg < 3600:
        return f"hace {int(seg // 60)} min"
    if seg < 86400:
        return f"hace {int(seg // 3600)} h"
    dias = int(seg // 86400)
    return "ayer" if dias == 1 else f"hace {dias} días"


# =====================================================================
# Páginas (HTML)
# =====================================================================

# ---------- Bandeja de asignación (Administrador y Técnico) ----------
@bp.route("/asignaciones")
@roles_required("Administrador", "Técnico")
def asignaciones():
    usuario = usuario_sesion()
    # La primera vez (sin ?estado=) la bandeja muestra solo lo pendiente; "todos" quita el filtro
    estado = request.args.get("estado", "pendientes")
    f = {"q": request.args.get("q", "").strip(),
         "estado": estado,
         "prioridad": request.args.get("prioridad", ""),
         "asignado": request.args.get("asignado", "")}      # "sin" = sin técnico, "inactivo"
    if f["estado"] == "todos":
        estado = ""
    tickets = Historial.bandeja(usuario, f["q"], estado, f["prioridad"], f["asignado"])
    tecnicos = Historial.tecnicos(usuario["empresa_id"]) if usuario["rol"] == "Administrador" else []
    return render_template("historial/asignaciones.html", tickets=tickets, tecnicos=tecnicos,
                           estados=ESTADOS, prioridades=PRIORIDADES, f=f)


# ---------- Detalle con historial (línea de tiempo) ----------
@bp.route("/tickets/<int:ticket_id>/historial")
@roles_required()
def ver_historial(ticket_id):
    usuario = usuario_sesion()
    try:
        t = Historial.ticket(ticket_id, usuario)
        eventos = Historial.listar(ticket_id, usuario)
    except HistorialError:
        abort(404)
    tecnicos = Historial.tecnicos(usuario["empresa_id"]) if usuario["rol"] == "Administrador" else []
    return render_template("historial/historial.html", t=t, eventos=eventos, tecnicos=tecnicos)


# ---------- Acciones de los modales (responden JSON para historial.js) ----------
def _accion(funcion, *args):
    """Ejecuta una acción del modelo y responde {ok, mensaje} como espera historial.js."""
    try:
        mensaje = funcion(*args)
    except HistorialError as e:
        return jsonify(ok=False, mensaje=str(e)), e.estado
    except Exception as e:
        current_app.logger.exception("Error en el Módulo 3")
        return jsonify(ok=False, mensaje="Error en el servidor. Inténtalo de nuevo."), 500
    return jsonify(ok=True, mensaje=mensaje)


@bp.route("/tickets/<int:ticket_id>/asignar", methods=["POST"])
@roles_required("Administrador")
def asignar(ticket_id):
    return _accion(Historial.asignar, ticket_id, usuario_sesion(),
                   request.form.get("tecnico_id", ""), request.form.get("comentario", ""))


@bp.route("/tickets/<int:ticket_id>/quitar_asignacion", methods=["POST"])
@roles_required("Administrador")
def quitar_asignacion(ticket_id):
    return _accion(Historial.quitar_asignacion, ticket_id, usuario_sesion(),
                   request.form.get("comentario", ""))


# Todos los roles: el Solicitante dueño puede confirmar o reabrir su ticket Resuelto.
# El modelo decide qué estados permite a cada usuario (Historial.siguientes).
@bp.route("/tickets/<int:ticket_id>/estado", methods=["POST"])
@roles_required()
def cambiar_estado(ticket_id):
    return _accion(Historial.cambiar_estado, ticket_id, usuario_sesion(),
                   request.form.get("estado", ""), request.form.get("comentario", ""))


# =====================================================================
# API REST del Módulo 3 (JSON). Mismo formato que /api/usuarios y /api/tickets: code, data, msge.
# Se prueba en Postman con la sesión iniciada (POST /api/login).
#
#   GET    /api/asignaciones                      bandeja (filtros ?q=&estado=&prioridad=&asignado=sin|inactivo)
#                                                 estado: un estado, "pendientes" o vacío (todos)
#   GET    /api/asignaciones/tecnicos             técnicos activos para asignar
#   GET    /api/tickets/<id>/historial            línea de tiempo del ticket
#   GET    /api/historial/<id>                    detalle de un evento
#   POST   /api/tickets/<id>/asignacion           asignar (ticket SIN técnico)   {"tecnico_id": 3, "comentario": "..."}
#   POST   /api/tickets/<id>/reasignacion         reasignar (ticket CON técnico) {"tecnico_id": 4, "comentario": "..."}
#   POST   /api/tickets/<id>/quitar_asignacion    quitar la asignación (comentario opcional)
#   POST   /api/tickets/<id>/estado               cambiar estado {"estado": "En proceso", "comentario": "..."}
#                                                 (el Solicitante dueño: solo desde Resuelto a Cerrado o En proceso)
# =====================================================================
def respuesta(code, data, msge, estado=200):
    rpta = dict()
    rpta["code"] = code
    rpta["data"] = data
    rpta["msge"] = msge
    return jsonify(rpta), estado


def datos_api():
    """Acepta JSON o formulario."""
    if request.is_json:
        try:
            datos = request.get_json()
        except BadRequest:
            raise HistorialError("El cuerpo JSON no es válido.")
        if not isinstance(datos, dict):
            raise HistorialError("Envía un objeto JSON.")
        return datos
    return request.form


@bp.errorhandler(HistorialError)
def _error_historial(e):
    # Solo llega aquí lo que no se atrapó antes: las rutas de la API
    return respuesta(-1, None, str(e), e.estado)


@bp.errorhandler(Exception)
def _error_inesperado(e):
    """Un error no previsto (por ejemplo, la base rechaza algo) en la API responde JSON, no una página HTML."""
    if isinstance(e, HTTPException):          # 404, 405, etc. siguen su camino normal
        return e
    current_app.logger.exception("Error en el Módulo 3")
    if request.path.startswith("/api/"):
        return respuesta(-1, None, "Error en el servidor. Inténtalo de nuevo.", 500)
    raise e


@bp.route("/api/asignaciones")
@roles_required("Administrador", "Técnico")
def api_asignaciones():
    usuario = usuario_sesion()
    lista = list()
    estado = request.args.get("estado", "")
    for t in Historial.bandeja(usuario, request.args.get("q", "").strip(), "" if estado == "todos" else estado,
                               request.args.get("prioridad", ""), request.args.get("asignado", "")):
        lista.append(Historial.ticket_a_diccionario(t))
    return respuesta(1, lista, "Lista de asignaciones generada correctamente en JSON.")


@bp.route("/api/asignaciones/tecnicos")
@roles_required("Administrador")
def api_tecnicos():
    return respuesta(1, Historial.tecnicos(session["empresa_id"]), "Lista de técnicos activos.")


@bp.route("/api/tickets/<int:ticket_id>/historial")
@roles_required()
def api_historial(ticket_id):
    lista = list()
    for e in Historial.listar(ticket_id, usuario_sesion()):
        lista.append(e.a_diccionario())
    return respuesta(1, lista, "Historial del ticket TK-" + str(ticket_id).zfill(4) + " generado correctamente.")


@bp.route("/api/historial/<int:evento_id>")
@roles_required()
def api_evento(evento_id):
    return respuesta(1, Historial.obtener(evento_id, usuario_sesion()).a_diccionario(), "Evento encontrado.")


# Asigna o reasigna un técnico: primera=True exige que el ticket no tenga técnico; primera=False, que ya tenga
def _asignar_api(ticket_id, primera):
    usuario = usuario_sesion()
    datos = datos_api()
    actual = Historial.ticket(ticket_id, usuario)
    if primera and actual["tecnico_id"]:
        raise HistorialError("El ticket ya tiene técnico. Usa /reasignacion para cambiarlo.", 409)
    if not primera and not actual["tecnico_id"]:
        raise HistorialError("El ticket no tiene técnico. Usa /asignacion para asignarlo.", 409)
    mensaje = Historial.asignar(ticket_id, usuario, datos.get("tecnico_id", ""), datos.get("comentario", ""))
    t = Historial.ticket_a_diccionario(Historial.ticket(ticket_id, usuario))
    return respuesta(1, t, mensaje, 201 if primera else 200)


@bp.route("/api/tickets/<int:ticket_id>/asignacion", methods=["POST"])
@roles_required("Administrador")
def api_asignacion(ticket_id):
    return _asignar_api(ticket_id, True)


@bp.route("/api/tickets/<int:ticket_id>/reasignacion", methods=["POST"])
@roles_required("Administrador")
def api_reasignacion(ticket_id):
    return _asignar_api(ticket_id, False)


@bp.route("/api/tickets/<int:ticket_id>/quitar_asignacion", methods=["POST"])
@roles_required("Administrador")
def api_quitar_asignacion(ticket_id):
    usuario = usuario_sesion()
    datos = datos_api()          # el comentario es opcional; sin cuerpo llega vacío
    mensaje = Historial.quitar_asignacion(ticket_id, usuario, datos.get("comentario", ""))
    t = Historial.ticket_a_diccionario(Historial.ticket(ticket_id, usuario))
    return respuesta(1, t, mensaje)


@bp.route("/api/tickets/<int:ticket_id>/estado", methods=["POST"])
@roles_required()
def api_estado(ticket_id):
    usuario = usuario_sesion()
    datos = datos_api()
    mensaje = Historial.cambiar_estado(ticket_id, usuario, datos.get("estado", ""), datos.get("comentario", ""))
    t = Historial.ticket_a_diccionario(Historial.ticket(ticket_id, usuario))
    return respuesta(1, t, mensaje)
