# INTEGRACIÓN: páginas generales del sistema (Inicio, Dashboard, Perfil, Configuración).
# No pertenecen a ningún módulo; solo leen datos (SELECT parametrizados y filtrados por empresa_id).
from flask import Blueprint, render_template, session
from db import obtener_conexion
from modules.auth import roles_required
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


@bp.route("/perfil")
@roles_required()
def perfil():
    con = obtener_conexion()
    try:
        with con.cursor() as cur:
            cur.execute("SELECT u.email, p.nombres, p.apellidos, p.dni, p.telefono, "
                        "a.nombre AS area, e.nombre AS empresa "
                        "FROM usuarios u JOIN personas p ON p.id = u.persona_id "
                        "JOIN empresas e ON e.id = u.empresa_id "
                        "LEFT JOIN areas a ON a.id = p.area_id "
                        "WHERE u.id=%s AND u.empresa_id=%s",
                        (session["usuario_id"], session["empresa_id"]))
            datos = cur.fetchone() or {}
    finally:
        con.close()
    return render_template("panel/perfil.html", datos=datos)


@bp.route("/configuracion")
@roles_required()
def configuracion():
    return render_template("panel/configuracion.html", sla_horas=SLA_HORAS)
