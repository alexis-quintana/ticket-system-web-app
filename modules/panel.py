# INTEGRACIÓN: páginas generales del sistema (Inicio, Dashboard, Perfil, Configuración).
# No pertenecen a ningún módulo; solo leen datos (SELECT parametrizados y filtrados por empresa_id).
import re

from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from db import obtener_conexion
from modules.auth import PASSWORD_RE, _hashear, _password_correcta, roles_required
from modules.sla import calcular_sla, SLA_HORAS
from modules.tickets import ESTADOS, PRIORIDADES

bp = Blueprint("panel", __name__)

ACTIVOS = ("Abierto", "En proceso")
SLA_ETIQUETAS = {"verde": "En plazo", "amarillo": "Por vencer", "rojo": "Vencido"}


def _tickets_visibles(columnas, extra="", limite=None):
    """Tickets que el usuario puede ver: los de su empresa (el Solicitante, solo los suyos)."""
    sql = ("SELECT " + columnas + " FROM tickets t JOIN categorias c ON c.id = t.categoria_id "
           "WHERE t.empresa_id=%s")
    params = [session["empresa_id"]]
    if session["rol"] == "Solicitante":
        sql += " AND t.solicitante_id=%s"; params.append(session["usuario_id"])
    sql += extra
    if limite:
        sql += " LIMIT %s"; params.append(limite)
    con = obtener_conexion()
    try:
        with con.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()
    finally:
        con.close()


def _barras(conteo, total):
    """[(etiqueta, cantidad, porcentaje)] para los gráficos de barras HTML."""
    return [(k, v, round(v * 100 / total) if total else 0) for k, v in conteo.items()]


@bp.route("/inicio")
@roles_required()
def inicio():
    recientes = _tickets_visibles("t.id, t.asunto, t.estado, t.prioridad, t.created_at",
                                  " ORDER BY t.id DESC", limite=5)
    return render_template("panel/inicio.html", recientes=recientes)


@bp.route("/dashboard")
@roles_required()
def dashboard():
    filas = _tickets_visibles("t.estado, t.prioridad, t.created_at, t.resuelto_en, c.nombre AS categoria")
    total = len(filas)
    por_estado = {e: 0 for e in ESTADOS}
    por_prioridad = {p: 0 for p in PRIORIDADES}
    por_sla = {e: 0 for e in SLA_ETIQUETAS.values()}
    por_categoria = {}
    for t in filas:
        por_estado[t["estado"]] += 1
        por_prioridad[t["prioridad"]] += 1
        por_categoria[t["categoria"]] = por_categoria.get(t["categoria"], 0) + 1
        if t["estado"] in ACTIVOS:   # el semáforo solo importa en tickets aún sin resolver
            color = calcular_sla(t["prioridad"], t["created_at"], t["estado"], t["resuelto_en"])["color"]
            por_sla[SLA_ETIQUETAS[color]] += 1
    activos = sum(por_estado[e] for e in ACTIVOS)
    return render_template(
        "panel/dashboard.html", total=total, activos=activos,
        por_vencer=por_sla["Por vencer"], vencidos=por_sla["Vencido"],
        estados=_barras(por_estado, total), prioridades=_barras(por_prioridad, total),
        sla=_barras(por_sla, activos),
        categorias=_barras(dict(sorted(por_categoria.items(), key=lambda x: -x[1])), total))


def _datos_perfil():
    """Datos del usuario conectado y, si no es administrador, a quién escribir para corregirlos."""
    con = obtener_conexion()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT u.email, p.nombres, p.apellidos, p.dni, p.telefono, "
                        "a.nombre AS area, e.nombre AS empresa "
                        "FROM usuarios u JOIN personas p ON p.id = u.persona_id "
                        "JOIN empresas e ON e.id = u.empresa_id "
                        "LEFT JOIN areas a ON a.id = p.area_id "
                        "WHERE u.id=%s",     # solo su propia cuenta; el superadmin puede estar viendo otra empresa
                        (session["usuario_id"],))
            datos = cur.fetchone() or {}
        admins = []
        if session["rol"] != "Administrador":
            with con.cursor() as cur:
                cur.execute("SELECT p.nombres, p.apellidos, u.email "
                            "FROM usuarios u JOIN personas p ON p.id = u.persona_id "
                            "JOIN roles r ON r.id = u.rol_id "
                            "WHERE u.empresa_id=%s AND r.nombre='Administrador' AND u.activo=1 "
                            "AND u.es_superadmin=0 ORDER BY u.id", (session["empresa_id"],))
                admins = cur.fetchall()
    finally:
        con.close()
    return datos, admins


def _mostrar_perfil(estado=200, **extra):
    datos, admins = _datos_perfil()
    return render_template("panel/perfil.html", datos=datos, admins=admins, **extra), estado


@bp.route("/perfil")
@roles_required()
def perfil():
    return _mostrar_perfil()


# ---------- Edición de la propia cuenta: teléfono y contraseña ----------
@bp.route("/perfil/telefono", methods=["POST"])
@roles_required()
def perfil_telefono():
    telefono = request.form.get("telefono", "").strip()
    if telefono and not re.fullmatch(r"\d{6,15}", telefono):
        return _mostrar_perfil(400, error_telefono="El teléfono solo debe tener números (6 a 15 dígitos).",
                               telefono_escrito=telefono)
    con = obtener_conexion()
    try:
        with con.cursor() as cur:
            cur.execute("UPDATE personas SET telefono=%s "
                        "WHERE id=(SELECT persona_id FROM usuarios WHERE id=%s)",
                        (telefono or None, session["usuario_id"]))
        con.commit()
    finally:
        con.close()
    flash("Teléfono actualizado." if telefono else "Teléfono eliminado de tu ficha.", "success")
    return redirect(url_for("panel.perfil"))


@bp.route("/perfil/password", methods=["POST"])
@roles_required()
def perfil_password():
    actual = request.form.get("actual", "")
    nueva = request.form.get("nueva", "")
    confirmar = request.form.get("confirmar", "")

    con = obtener_conexion()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT password FROM usuarios WHERE id=%s", (session["usuario_id"],))
            fila = cur.fetchone() or {}
        error = ""
        if not actual or not nueva or not confirmar:
            error = "Completa los tres campos."
        elif not _password_correcta(actual, fila.get("password", "")):
            error = "La contraseña actual no es correcta."
        elif not PASSWORD_RE.match(nueva):
            error = "La nueva contraseña debe tener 8+ caracteres con minúscula, mayúscula, número y símbolo (!@#$%^&*)."
        elif len(nueva.encode("utf-8")) > 72:
            error = "La nueva contraseña no puede superar 72 caracteres."
        elif nueva == actual:
            error = "La nueva contraseña debe ser distinta de la actual."
        elif nueva != confirmar:
            error = "La confirmación no coincide con la nueva contraseña."
        if error:
            return _mostrar_perfil(400, error_password=error)
        with con.cursor() as cur:
            cur.execute("UPDATE usuarios SET password=%s WHERE id=%s",
                        (_hashear(nueva), session["usuario_id"]))
        con.commit()
    finally:
        con.close()
    flash("Contraseña actualizada. Úsala la próxima vez que inicies sesión.", "success")
    return redirect(url_for("panel.perfil"))


@bp.route("/configuracion")
@roles_required()
def configuracion():
    return render_template("panel/configuracion.html", sla_horas=SLA_HORAS)
