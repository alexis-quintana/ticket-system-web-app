from flask import Blueprint, render_template, session
from db import obtener_conexion
from modules.auth import roles_required

bp = Blueprint("tickets", __name__, url_prefix="/tickets")

PRIORIDADES = ("Alta", "Media", "Baja")
ESTADOS = ("Abierto", "En proceso", "Resuelto", "Cerrado")

@bp.route("/")
@roles_required()
def listar():
    emp = session["empresa_id"]
    sql = ("SELECT t.id, t.asunto, t.prioridad, t.estado, t.created_at, c.nombre AS categoria "
           "FROM tickets t JOIN categorias c ON c.id = t.categoria_id "
           "WHERE t.empresa_id=%s")
    params = [emp]
    if session["rol"] == "Solicitante":     
        sql += " AND t.solicitante_id=%s"
        params.append(session["usuario_id"])
    sql += " ORDER BY t.id DESC"
    con = obtener_conexion()
    try:
        with con.cursor() as cur:
            cur.execute(sql, params)
            lista = cur.fetchall()
    finally:
        con.close()
    return render_template("tickets/listado.html", tickets=lista)