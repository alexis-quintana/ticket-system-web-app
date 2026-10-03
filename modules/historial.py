from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, session, abort
from db import obtener_conexion
from modules.auth import roles_required
from modules.sla import calcular_sla   # Módulo 4 (Ordoñez): semáforo en el detalle

bp = Blueprint("historial", __name__)

ESTADOS = ("Abierto", "En proceso", "Resuelto", "Cerrado")
PRIORIDADES = ("Alta", "Media", "Baja")
# Transiciones permitidas (se puede cambiar aquí si el docente pide otra regla)
TRANSICIONES = {
    "Abierto":    ("En proceso",),
    "En proceso": ("Resuelto",),
    "Resuelto":   ("Cerrado", "En proceso"),   # En proceso = reapertura
    "Cerrado":    (),
}
SLA_CSS = {"verde": "green", "amarillo": "yellow", "rojo": "red"}

# SELECT base del ticket con nombres de solicitante y técnico (siempre filtrado por empresa)
SQL_TICKET = (
    "SELECT t.id, t.asunto, t.descripcion, t.prioridad, t.estado, t.created_at, t.resuelto_en, "
    "t.solicitante_id, t.tecnico_id, c.nombre AS categoria, "
    "CONCAT(ps.nombres, ' ', ps.apellidos) AS solicitante, "
    "CONCAT(pt.nombres, ' ', pt.apellidos) AS tecnico "
    "FROM tickets t "
    "LEFT JOIN categorias c ON c.id = t.categoria_id "
    "LEFT JOIN usuarios us ON us.id = t.solicitante_id "
    "LEFT JOIN personas ps ON ps.id = us.persona_id "
    "LEFT JOIN usuarios ut ON ut.id = t.tecnico_id "
    "LEFT JOIN personas pt ON pt.id = ut.persona_id "
)


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


# ---------- Funciones auxiliares ----------
def _tecnicos(cur, emp):
    cur.execute("SELECT u.id, CONCAT(p.nombres, ' ', p.apellidos) AS nombre "
                "FROM usuarios u JOIN roles r ON r.id = u.rol_id "
                "JOIN personas p ON p.id = u.persona_id "
                "WHERE u.empresa_id=%s AND r.nombre='Técnico' AND u.activo=1 "
                "ORDER BY p.apellidos, p.nombres", (emp,))
    return cur.fetchall()


def _historial(cur, ticket_id, emp):
    cur.execute("SELECT h.id, h.tipo, h.estado_anterior, h.estado_nuevo, h.comentario, h.created_at, "
                "CONCAT(pa.nombres, ' ', pa.apellidos) AS autor, "
                "CONCAT(pt.nombres, ' ', pt.apellidos) AS tecnico "
                "FROM ticket_historial h "
                "JOIN usuarios ua ON ua.id = h.usuario_id JOIN personas pa ON pa.id = ua.persona_id "
                "LEFT JOIN usuarios ut ON ut.id = h.tecnico_id LEFT JOIN personas pt ON pt.id = ut.persona_id "
                "WHERE h.ticket_id=%s AND h.empresa_id=%s ORDER BY h.created_at DESC, h.id DESC",
                (ticket_id, emp))
    return cur.fetchall()


def _puede_ver(t):
    """Solicitante solo ve sus tickets; Administrador y Técnico ven los de su empresa."""
    return session["rol"] != "Solicitante" or t["solicitante_id"] == session["usuario_id"]


def _puede_cambiar_estado(t):
    rol = session["rol"]
    return rol == "Administrador" or (rol == "Técnico" and t["tecnico_id"] == session["usuario_id"])


def _notificar(cur, emp, destino, tipo, ticket_id):
    """Gancho al Módulo 5 (Quintana). Si su tabla aún no existe o tiene otras columnas,
    se ignora el error y el historial se guarda igual. AJUSTAR cuando exista 05_notificaciones.sql."""
    if not destino or destino == session["usuario_id"]:
        return
    try:
        cur.execute("INSERT INTO notificaciones (empresa_id, usuario_id, tipo, ticket_id) "
                    "VALUES (%s,%s,%s,%s)", (emp, destino, tipo, ticket_id))
    except Exception as e:
        print("Notificación omitida:", repr(e))


def _sla_de(t):
    """Semáforo con la función del Módulo 4. Usa tickets.resuelto_en para detener el contador."""
    s = calcular_sla(t["prioridad"], t["created_at"], t["estado"], t["resuelto_en"])
    return {"clase": SLA_CSS[s["color"]], "texto": s["texto"]}


# ---------- Bandeja de asignación (Administrador y Técnico) ----------
@bp.route("/asignaciones")
@roles_required("Administrador", "Técnico")
def asignaciones():
    emp, yo, rol = session["empresa_id"], session["usuario_id"], session["rol"]
    q = request.args.get("q", "").strip()
    estado = request.args.get("estado", "")
    prioridad = request.args.get("prioridad", "")
    asignado = request.args.get("asignado", "")   # "sin" = sin técnico

    sql = SQL_TICKET + "WHERE t.empresa_id=%s"
    params = [emp]
    if rol == "Técnico":                       # el técnico solo ve lo que tiene asignado
        sql += " AND t.tecnico_id=%s"; params.append(yo)
    if q:
        sql += " AND (t.asunto LIKE %s OR t.id = %s)"
        params += [f"%{q}%", q.lstrip('#') if q.lstrip('#').isdigit() else 0]
    if estado in ESTADOS:
        sql += " AND t.estado=%s"; params.append(estado)
    if prioridad in PRIORIDADES:
        sql += " AND t.prioridad=%s"; params.append(prioridad)
    if asignado == "sin":
        sql += " AND t.tecnico_id IS NULL"
    sql += " ORDER BY FIELD(t.prioridad,'Alta','Media','Baja'), t.created_at"

    con = obtener_conexion()
    try:
        with con.cursor() as cur:
            cur.execute(sql, params)
            tickets = cur.fetchall()
            tecnicos = _tecnicos(cur, emp) if rol == "Administrador" else []
            for t in tickets:
                t["sla"] = _sla_de(t)
                t["siguientes"] = TRANSICIONES.get(t["estado"], ())
                t["puede_estado"] = _puede_cambiar_estado(t) and bool(t["siguientes"])
    finally:
        con.close()
    return render_template("historial/asignaciones.html", tickets=tickets, tecnicos=tecnicos,
                           estados=ESTADOS, prioridades=PRIORIDADES,
                           f={"q": q, "estado": estado, "prioridad": prioridad, "asignado": asignado})


# ---------- Detalle con historial (línea de tiempo) ----------
@bp.route("/tickets/<int:ticket_id>/historial")
@roles_required()
def ver_historial(ticket_id):
    emp = session["empresa_id"]
    con = obtener_conexion()
    try:
        with con.cursor() as cur:
            cur.execute(SQL_TICKET + "WHERE t.id=%s AND t.empresa_id=%s", (ticket_id, emp))
            t = cur.fetchone()
            if not t or not _puede_ver(t):
                abort(404)
            eventos = _historial(cur, ticket_id, emp)
            tecnicos = _tecnicos(cur, emp) if session["rol"] == "Administrador" else []
            t["sla"] = _sla_de(t)
    finally:
        con.close()
    t["siguientes"] = TRANSICIONES.get(t["estado"], ())
    t["puede_estado"] = _puede_cambiar_estado(t) and bool(t["siguientes"])
    return render_template("historial/historial.html", t=t, eventos=eventos, tecnicos=tecnicos)


# ---------- Asignar ticket a un técnico (solo Administrador) ----------
@bp.route("/tickets/<int:ticket_id>/asignar", methods=["POST"])
@roles_required("Administrador")
def asignar(ticket_id):
    emp, yo = session["empresa_id"], session["usuario_id"]
    tecnico_id = request.form.get("tecnico_id", "").strip()
    comentario = request.form.get("comentario", "").strip()

    if not tecnico_id.isdigit():
        return jsonify(ok=False, mensaje="Selecciona un técnico."), 400
    if len(comentario) > 1000:
        return jsonify(ok=False, mensaje="El comentario no puede superar 1000 caracteres."), 400

    con = obtener_conexion()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT id, estado, tecnico_id FROM tickets WHERE id=%s AND empresa_id=%s FOR UPDATE",
                        (ticket_id, emp))
            t = cur.fetchone()
            if not t:
                return jsonify(ok=False, mensaje="El ticket no existe."), 404
            if t["estado"] == "Cerrado":
                return jsonify(ok=False, mensaje="Un ticket cerrado no se puede reasignar."), 409
            if t["tecnico_id"] == int(tecnico_id):
                return jsonify(ok=False, mensaje="El ticket ya está asignado a ese técnico."), 409
            # el técnico debe ser de la misma empresa, tener rol Técnico y estar activo
            tec = next((x for x in _tecnicos(cur, emp) if x["id"] == int(tecnico_id)), None)
            if not tec:
                return jsonify(ok=False, mensaje="El técnico seleccionado no es válido."), 400

            comentario = comentario or "Ticket asignado a " + tec["nombre"] + "."
            cur.execute("UPDATE tickets SET tecnico_id=%s WHERE id=%s AND empresa_id=%s",
                        (tec["id"], ticket_id, emp))
            cur.execute("INSERT INTO ticket_historial (empresa_id, ticket_id, usuario_id, tipo, "
                        "estado_anterior, estado_nuevo, tecnico_id, comentario) "
                        "VALUES (%s,%s,%s,'Asignación',%s,%s,%s,%s)",
                        (emp, ticket_id, yo, t["estado"], t["estado"], tec["id"], comentario))
            _notificar(cur, emp, tec["id"], "asignacion", ticket_id)
        con.commit()
        return jsonify(ok=True, mensaje="Ticket asignado a " + tec["nombre"] + ".")
    except Exception as e:
        con.rollback()
        print(repr(e))
        return jsonify(ok=False, mensaje="Error en el servidor. Inténtalo de nuevo."), 500
    finally:
        con.close()


# ---------- Cambiar estado con comentario obligatorio ----------
@bp.route("/tickets/<int:ticket_id>/estado", methods=["POST"])
@roles_required("Administrador", "Técnico")
def cambiar_estado(ticket_id):
    emp, yo = session["empresa_id"], session["usuario_id"]
    nuevo = request.form.get("estado", "").strip()
    comentario = request.form.get("comentario", "").strip()

    if nuevo not in ESTADOS:
        return jsonify(ok=False, mensaje="Selecciona el nuevo estado."), 400
    if not comentario:
        return jsonify(ok=False, mensaje="Escribe un comentario para cambiar el estado."), 400
    if len(comentario) < 5 or len(comentario) > 1000:
        return jsonify(ok=False, mensaje="El comentario debe tener entre 5 y 1000 caracteres."), 400

    con = obtener_conexion()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT id, estado, tecnico_id, solicitante_id FROM tickets "
                        "WHERE id=%s AND empresa_id=%s FOR UPDATE", (ticket_id, emp))
            t = cur.fetchone()
            if not t:
                return jsonify(ok=False, mensaje="El ticket no existe."), 404
            if not _puede_cambiar_estado(t):
                return jsonify(ok=False, mensaje="Solo el técnico asignado puede cambiar el estado."), 403
            if not t["tecnico_id"]:
                return jsonify(ok=False, mensaje="Asigna un técnico antes de cambiar el estado."), 409
            if nuevo not in TRANSICIONES[t["estado"]]:
                return jsonify(ok=False, mensaje=f"No se puede pasar de {t['estado']} a {nuevo}."), 409

            # resuelto_en detiene el contador SLA: se fija al resolver y se limpia al reabrir
            # (al reabrir, el vencimiento original se conserva porque created_at no cambia).
            if nuevo == "Resuelto":
                extra = ", resuelto_en=NOW()"
            elif nuevo == "En proceso":
                extra = ", resuelto_en=NULL"
            else:                       # Cerrado: conserva la fecha de resolución
                extra = ""
            cur.execute("UPDATE tickets SET estado=%s" + extra + " WHERE id=%s AND empresa_id=%s",
                        (nuevo, ticket_id, emp))
            cur.execute("INSERT INTO ticket_historial (empresa_id, ticket_id, usuario_id, tipo, "
                        "estado_anterior, estado_nuevo, comentario) "
                        "VALUES (%s,%s,%s,'Cambio de estado',%s,%s,%s)",
                        (emp, ticket_id, yo, t["estado"], nuevo, comentario))
            _notificar(cur, emp, t["solicitante_id"], "cambio_estado", ticket_id)
        con.commit()
        return jsonify(ok=True, mensaje="Estado actualizado a " + nuevo + ".")
    except Exception as e:
        con.rollback()
        print(repr(e))
        return jsonify(ok=False, mensaje="Error en el servidor. Inténtalo de nuevo."), 500
    finally:
        con.close()


# ---------- API REST: historial de un ticket (JSON) ----------
@bp.route("/api/tickets/<int:ticket_id>/historial")
@roles_required()
def api_historial(ticket_id):
    emp = session["empresa_id"]
    con = obtener_conexion()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT id, solicitante_id FROM tickets WHERE id=%s AND empresa_id=%s", (ticket_id, emp))
            t = cur.fetchone()
            if not t or not _puede_ver(t):
                return jsonify(error="Ticket no encontrado"), 404
            eventos = _historial(cur, ticket_id, emp)
    finally:
        con.close()
    for e in eventos:
        e["created_at"] = e["created_at"].isoformat(sep=" ", timespec="seconds")
    return jsonify(eventos)
