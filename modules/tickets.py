
from flask import (Blueprint, render_template, request, jsonify, session, send_from_directory,
                   abort, redirect, url_for, flash)
from werkzeug.exceptions import BadRequest
from modules.auth import roles_required
from modules.sla import SLA_HORAS
from models.ticket import Ticket, Evidencia, TicketError, PRIORIDADES, ESTADOS

# Sin url_prefix: cada ruta escribe /tickets/... completo, igual que historial.py,
# así la API puede vivir en /api/tickets como /api/usuarios y /api/notificaciones.
bp = Blueprint("tickets", __name__)


@bp.record_once
def _configurar(state):
    # Flask rechaza peticiones de más de 16 MB (3 fotos de 5 MB + el texto)
    state.app.config.setdefault("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)


def usuario_sesion():
    """Los datos del usuario que necesita el modelo (siempre salen de la sesión, nunca del formulario)."""
    return dict(empresa_id=session["empresa_id"], usuario_id=session["usuario_id"], rol=session["rol"])


def fotos_subidas():
    return [f for f in request.files.getlist("evidencias") if f.filename]


@bp.app_template_global()
def evidencias_de(ticket_id):
    """Fotos de un ticket para cualquier plantilla. La usa tickets/_evidencias.html,
    que el detalle (historial.html, Módulo 3) incluye con una sola línea."""
    return Evidencia.de_ticket(ticket_id, session["empresa_id"])



@bp.app_template_global()
def ticket_editable(ticket_id):
    usuario = usuario_sesion()
    try:
        return Ticket.obtener(ticket_id, usuario).puede_editar(usuario)
    except TicketError:
        return False


# =====================================================================
# Páginas (HTML)
# =====================================================================
@bp.route("/tickets/")
@roles_required()
def listar():
    usuario = usuario_sesion()
    # búsqueda (?q=, también desde la barra superior) y filtros de estado/prioridad
    q = request.args.get("q", "").strip()
    estado = request.args.get("estado", "")
    estado = estado if estado in ESTADOS else ""
    prioridad = request.args.get("prioridad", "")
    prioridad = prioridad if prioridad in PRIORIDADES else ""
    lista = Ticket.listar(usuario, q, estado, prioridad)
    for t in lista:
        t.editable = t.puede_editar(usuario)
    # Alerta del Módulo 4: tickets activos vencidos o por vencer
    activos = [t for t in lista if t.estado in ("Abierto", "En proceso")]
    vencidos = sum(1 for t in activos if t.sla["clase"] == "red")
    por_vencer = sum(1 for t in activos if t.sla["clase"] == "yellow")
    return render_template("tickets/listado.html", tickets=lista, estados=ESTADOS, prioridades=PRIORIDADES,
                           f={"q": q, "estado": estado, "prioridad": prioridad}, sla_horas=SLA_HORAS,
                           vencidos=vencidos, por_vencer=por_vencer)


# Enlace corto al detalle (lo usan el listado y las notificaciones).
# El detalle vive en el Módulo 3, que ya valida empresa y permisos.
@bp.route("/tickets/<int:ticket_id>")
@roles_required()
def detalle(ticket_id):
    return redirect(url_for("historial.ver_historial", ticket_id=ticket_id))


@bp.route("/tickets/nuevo")
@roles_required()
def nuevo():
    """Formulario vacío para registrar un ticket."""
    return render_template("tickets/formulario.html", ticket=None, fotos=[],
                           categorias=Ticket.categorias(session["empresa_id"]), prioridades=PRIORIDADES)


@bp.route("/tickets/<int:ticket_id>/editar")
@roles_required()
def editar(ticket_id):
    """El mismo formulario, con los datos y las fotos actuales del ticket."""
    usuario = usuario_sesion()
    try:
        t = Ticket.obtener(ticket_id, usuario)
        t.validar_edicion(usuario)
    except TicketError as e:
        if e.estado == 404:
            abort(404)
        flash(str(e), "warning")
        return redirect(url_for("tickets.listar"))
    return render_template("tickets/formulario.html", ticket=t, fotos=Evidencia.de_ticket(t.id, t.empresa_id),
                           categorias=Ticket.categorias(t.empresa_id), prioridades=PRIORIDADES)


# ---------- Acciones del formulario (responden JSON para tickets.js) ----------
@bp.route("/tickets/procesar_ticket", methods=["POST"])
@roles_required()
def procesar_ticket():
    try:
        ticket_id = Ticket.crear(usuario_sesion(), request.form, fotos_subidas())
    except TicketError as e:
        return jsonify(ok=False, mensaje=str(e)), e.estado
    except Exception as e:
        print(repr(e))
        return jsonify(ok=False, mensaje="Error en el servidor. Inténtalo de nuevo."), 500
    return jsonify(ok=True, id=ticket_id,
                   mensaje="Ticket TK-" + str(ticket_id).zfill(4) + " registrado correctamente.")


@bp.route("/tickets/<int:ticket_id>/actualizar", methods=["POST"])
@roles_required()
def actualizar(ticket_id):
    usuario = usuario_sesion()
    try:
        Ticket.obtener(ticket_id, usuario).actualizar(usuario, request.form, fotos_subidas())
    except TicketError as e:
        return jsonify(ok=False, mensaje=str(e)), e.estado
    except Exception as e:
        print(repr(e))
        return jsonify(ok=False, mensaje="Error en el servidor. Inténtalo de nuevo."), 500
    return jsonify(ok=True, id=ticket_id,
                   mensaje="Ticket TK-" + str(ticket_id).zfill(4) + " actualizado correctamente.")


@bp.route("/tickets/evidencia/<int:evidencia_id>/eliminar", methods=["POST"])
@roles_required()
def eliminar_evidencia(evidencia_id):
    usuario = usuario_sesion()
    try:
        foto, _ = Evidencia.obtener(evidencia_id, usuario)
        foto.eliminar(usuario)
    except TicketError as e:
        return jsonify(ok=False, mensaje=str(e)), e.estado
    return jsonify(ok=True, mensaje="Foto " + foto.nombre_original + " eliminada.")


@bp.route("/tickets/evidencia/<int:evidencia_id>")
@roles_required()
def evidencia(evidencia_id):
    """Entrega la foto solo si es de la empresa del usuario (y si es Solicitante, solo de sus tickets)."""
    try:
        foto, _ = Evidencia.obtener(evidencia_id, usuario_sesion())
    except TicketError:
        abort(404)
    return send_from_directory(Evidencia.carpeta(), foto.archivo, mimetype=foto.mime)


# =====================================================================
# API REST de tickets (JSON). Mismo formato que /api/usuarios: code, data, msge.
# Se prueba en Postman con la sesión iniciada (POST /api/login).
# =====================================================================
def respuesta(code, data, msge, estado=200):
    rpta = dict()
    rpta["code"] = code
    rpta["data"] = data
    rpta["msge"] = msge
    return jsonify(rpta), estado


def datos_api():
    """Acepta JSON o formulario (formulario si se envían fotos)."""
    if request.is_json:
        try:
            datos = request.get_json()
        except BadRequest:
            raise TicketError("El cuerpo JSON no es válido.")
        if not isinstance(datos, dict):
            raise TicketError("Envía un objeto JSON.")
        return datos
    return request.form


@bp.errorhandler(TicketError)
def _error_ticket(e):
    # Solo llega aquí lo que no se atrapó antes: las rutas de la API
    return respuesta(-1, None, str(e), e.estado)


@bp.route("/api/tickets", methods=["GET", "POST"])
@roles_required()
def api_tickets():
    usuario = usuario_sesion()
    if request.method == "GET":
        lista = list()
        for t in Ticket.listar(usuario, request.args.get("q", "").strip(),
                               request.args.get("estado", ""), request.args.get("prioridad", "")):
            lista.append(t.a_diccionario())
        return respuesta(1, lista, "Lista de tickets generada correctamente en JSON.")
    ticket_id = Ticket.crear(usuario, datos_api(), fotos_subidas())
    return respuesta(1, Ticket.obtener(ticket_id, usuario).a_diccionario(),
                     "Ticket TK-" + str(ticket_id).zfill(4) + " registrado correctamente.", 201)


@bp.route("/api/tickets/<int:ticket_id>", methods=["GET", "PUT"])
@roles_required()
def api_ticket(ticket_id):
    usuario = usuario_sesion()
    t = Ticket.obtener(ticket_id, usuario)
    if request.method == "PUT":
        t.actualizar(usuario, datos_api(), fotos_subidas())
        t = Ticket.obtener(ticket_id, usuario)
        mensaje = "Ticket actualizado correctamente."
    else:
        mensaje = "Ticket encontrado."
    data = t.a_diccionario()
    data["evidencias"] = [e.a_diccionario() for e in Evidencia.de_ticket(t.id, t.empresa_id)]
    return respuesta(1, data, mensaje)


@bp.route("/api/tickets/<int:ticket_id>/evidencias/<int:evidencia_id>", methods=["DELETE"])
@roles_required()
def api_eliminar_evidencia(ticket_id, evidencia_id):
    usuario = usuario_sesion()
    foto, t = Evidencia.obtener(evidencia_id, usuario)
    if t.id != ticket_id:
        raise TicketError("La foto no pertenece a ese ticket.", 404)
    foto.eliminar(usuario)
    return respuesta(1, dict(id=evidencia_id, ticket_id=ticket_id), "Foto eliminada correctamente.")