import os, uuid
from flask import (Blueprint, render_template, request, jsonify, session,
                   current_app, send_from_directory, abort, redirect, url_for)
from db import obtener_conexion
from modules.auth import roles_required
from modules.sla import calcular_sla, SLA_HORAS   # INTEGRACIÓN: semáforo SLA en el listado (Módulo 4)

bp = Blueprint("tickets", __name__, url_prefix="/tickets")

PRIORIDADES = ("Alta", "Media", "Baja")
ESTADOS = ("Abierto", "En proceso", "Resuelto", "Cerrado")
SLA_CSS = {"verde": "green", "amarillo": "yellow", "rojo": "red"}   # INTEGRACIÓN: clases de tickets.css

# ---------- Evidencias (fotos) ----------
MAX_FOTOS = 3
MAX_BYTES = 5 * 1024 * 1024          # 5 MB por foto
# Tipo MIME según los primeros bytes del archivo (no se confía en la extensión)
FIRMAS = {b"\xff\xd8\xff": ("image/jpeg", ".jpg"),
          b"\x89PNG\r\n\x1a\n": ("image/png", ".png")}


@bp.record_once
def _configurar(state):
    # Flask rechaza peticiones de más de 16 MB (3 fotos de 5 MB + el texto)
    state.app.config.setdefault("MAX_CONTENT_LENGTH", 16 * 1024 * 1024)


def _carpeta_uploads():
    return os.path.join(current_app.root_path, "uploads")


def _leer_foto(f):
    """Devuelve (datos, mime, extension) o un mensaje de error."""
    datos = f.read()
    if len(datos) > MAX_BYTES:
        return "La foto " + f.filename + " pesa más de 5 MB."
    for firma, (mime, ext) in FIRMAS.items():
        if datos.startswith(firma):
            return datos, mime, ext
    return "La foto " + f.filename + " no es una imagen JPG o PNG."

@bp.route("/")
@roles_required()
def listar():
    emp = session["empresa_id"]
    # INTEGRACIÓN: búsqueda (?q=, también desde la barra superior) y filtros de estado/prioridad
    q = request.args.get("q", "").strip()
    estado = request.args.get("estado", "")
    estado = estado if estado in ESTADOS else ""
    prioridad = request.args.get("prioridad", "")
    prioridad = prioridad if prioridad in PRIORIDADES else ""
    sql = ("SELECT t.id, t.asunto, t.prioridad, t.estado, t.created_at, t.resuelto_en, c.nombre AS categoria, "
           "(SELECT MIN(e.id) FROM ticket_evidencias e WHERE e.ticket_id = t.id) AS evidencia_id, "
           "(SELECT COUNT(*) FROM ticket_evidencias e WHERE e.ticket_id = t.id) AS total_evidencias "
           "FROM tickets t JOIN categorias c ON c.id = t.categoria_id "
           "WHERE t.empresa_id=%s")
    params = [emp]
    if session["rol"] == "Solicitante":
        sql += " AND t.solicitante_id=%s"
        params.append(session["usuario_id"])
    if q:
        numero = q.upper().removeprefix("TK-").lstrip("#")
        sql += " AND (t.asunto LIKE %s OR t.id = %s)"
        params += [f"%{q}%", int(numero) if numero.isdigit() else 0]
    if estado:
        sql += " AND t.estado=%s"; params.append(estado)
    if prioridad:
        sql += " AND t.prioridad=%s"; params.append(prioridad)
    sql += " ORDER BY t.id DESC"
    con = obtener_conexion()
    try:
        with con.cursor() as cur:
            cur.execute(sql, params)
            lista = cur.fetchall()
    finally:
        con.close()
    for t in lista:   # INTEGRACIÓN: semáforo con la misma función que usa el historial
        s = calcular_sla(t["prioridad"], t["created_at"], t["estado"], t["resuelto_en"])
        t["sla"] = {"clase": SLA_CSS[s["color"]], "estado": s["texto"].split(" · ")[0],
                    "detalle": s["texto"].split(" · ")[1]}
    return render_template("tickets/listado.html", tickets=lista, estados=ESTADOS, prioridades=PRIORIDADES,
                           f={"q": q, "estado": estado, "prioridad": prioridad}, sla_horas=SLA_HORAS)


# INTEGRACIÓN: enlace corto al detalle (lo usan el listado y las notificaciones).
# El detalle vive en el Módulo 3, que ya valida empresa y permisos.
@bp.route("/<int:ticket_id>")
@roles_required()
def detalle(ticket_id):
    return redirect(url_for("historial.ver_historial", ticket_id=ticket_id))

@bp.route("/nuevo")
@roles_required()
def nuevo():
    """Muestra el formulario con las categorías de la empresa del usuario."""
    con = obtener_conexion()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT id, nombre FROM categorias WHERE empresa_id=%s ORDER BY nombre",
                        (session["empresa_id"],))
            categorias = cur.fetchall()
    finally:
        con.close()
    return render_template("tickets/crear.html", categorias=categorias, prioridades=PRIORIDADES)


@bp.route("/procesar_ticket", methods=["POST"])
@roles_required()
def procesar_ticket():
    emp, yo = session["empresa_id"], session["usuario_id"]
    asunto = request.form.get("asunto", "").strip()
    descripcion = request.form.get("descripcion", "").strip()
    categoria_id = request.form.get("categoria_id", "").strip()
    prioridad = request.form.get("prioridad", "")
    archivos = [f for f in request.files.getlist("evidencias") if f.filename]

    error = ""
    if len(asunto) < 5 or len(asunto) > 120:
        error = "El asunto debe tener entre 5 y 120 caracteres."
    elif len(descripcion) < 10 or len(descripcion) > 2000:
        error = "La descripción debe tener entre 10 y 2000 caracteres."
    elif not categoria_id.isdigit():
        error = "Selecciona una categoría."
    elif prioridad not in PRIORIDADES:
        error = "Selecciona una prioridad válida."
    elif len(archivos) > MAX_FOTOS:
        error = "Puedes adjuntar como máximo 3 fotos."
    if error:
        return jsonify(ok=False, mensaje=error), 400

    fotos = []
    for f in archivos:
        r = _leer_foto(f)
        if isinstance(r, str):          
            return jsonify(ok=False, mensaje=r), 400
        fotos.append((f.filename, r))

    guardados = []                      
    con = obtener_conexion()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT id FROM categorias WHERE id=%s AND empresa_id=%s", (categoria_id, emp))
            if not cur.fetchone():
                return jsonify(ok=False, mensaje="La categoría seleccionada no existe."), 400
            cur.execute("INSERT INTO tickets (empresa_id, solicitante_id, categoria_id, asunto, descripcion, prioridad) "
                        "VALUES (%s,%s,%s,%s,%s,%s)", (emp, yo, categoria_id, asunto, descripcion, prioridad))
            ticket_id = cur.lastrowid
            for nombre_original, (datos, mime, ext) in fotos:
                archivo = uuid.uuid4().hex + ext
                ruta = os.path.join(_carpeta_uploads(), archivo)
                with open(ruta, "wb") as salida:
                    salida.write(datos)
                guardados.append(ruta)
                cur.execute("INSERT INTO ticket_evidencias (ticket_id, empresa_id, archivo, nombre_original, mime, tamano_bytes) "
                            "VALUES (%s,%s,%s,%s,%s,%s)",
                            (ticket_id, emp, archivo, nombre_original[:160], mime, len(datos)))
        con.commit()
        return jsonify(ok=True, id=ticket_id,
                       mensaje="Ticket TK-" + str(ticket_id).zfill(4) + " registrado correctamente.")
    except Exception as e:
        con.rollback()
        for ruta in guardados:           
            os.remove(ruta)
        print(repr(e))
        return jsonify(ok=False, mensaje="Error en el servidor. Inténtalo de nuevo."), 500
    finally:
        con.close()


@bp.route("/evidencia/<int:evidencia_id>")
@roles_required()
def evidencia(evidencia_id):
    """Entrega la foto solo si es de la empresa del usuario (y si es Solicitante, solo de sus tickets)."""
    con = obtener_conexion()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT e.archivo, e.mime, t.solicitante_id FROM ticket_evidencias e "
                        "JOIN tickets t ON t.id = e.ticket_id "
                        "WHERE e.id=%s AND e.empresa_id=%s", (evidencia_id, session["empresa_id"]))
            e = cur.fetchone()
    finally:
        con.close()
    if not e or (session["rol"] == "Solicitante" and e["solicitante_id"] != session["usuario_id"]):
        abort(404)
    return send_from_directory(_carpeta_uploads(), e["archivo"], mimetype=e["mime"])