from flask import Blueprint, flash, g, has_request_context, redirect, render_template, request, session, url_for

from models.sla import SLA, PlazoSLA, PlazoError
from modules.auth import respuesta, roles_required

bp = Blueprint("sla", __name__)

# tickets.py, historial.py y panel.py importan estos nombres; no los renombres
SLA_HORAS = SLA.PLAZOS_POR_DEFECTO


# Plazos de la empresa (los suyos y, si falta alguno, el valor por defecto); se consultan una vez por petición
def plazos_empresa(empresa_id):
    if not has_request_context():
        return dict(SLA_HORAS)
    cache = g.setdefault("plazos_sla", {})
    if empresa_id not in cache:
        try:
            cache[empresa_id] = PlazoSLA.efectivos(empresa_id)
        except Exception:
            # si la tabla sla_plazos aún no existe en esta computadora, se usan los valores por defecto
            cache[empresa_id] = dict(SLA_HORAS)
    return cache[empresa_id]


def calcular_sla(prioridad, creado_en, estado, resuelto_en=None, empresa_id=None):
    plazos = plazos_empresa(empresa_id) if empresa_id else None
    return SLA.calcular(prioridad, creado_en, estado, resuelto_en, plazos)


# 1. Pantalla de plazos (solo el Administrador de la empresa)
@bp.route("/sla")
@roles_required("Administrador")
def lista():
    empresa_id = session["empresa_id"]
    plazos = PlazoSLA.listar(empresa_id)
    definidas = [p["prioridad"] for p in plazos]
    libres = [p for p in PlazoSLA.PRIORIDADES if p not in definidas]
    return render_template("sla/plazos.html", plazos=plazos, libres=libres,
                           efectivos=PlazoSLA.efectivos(empresa_id), defecto=SLA.PLAZOS_POR_DEFECTO,
                           min_horas=PlazoSLA.MIN_HORAS, max_horas=PlazoSLA.MAX_HORAS)


@bp.route("/sla/crear", methods=["POST"])
@roles_required("Administrador")
def crear():
    try:
        PlazoSLA.registrar(session["empresa_id"], request.form.get("prioridad", ""), request.form.get("horas", ""))
        flash("Plazo creado correctamente.", "success")
    except PlazoError as e:
        flash(str(e), "danger")
    return redirect(url_for("sla.lista"))


@bp.route("/sla/<int:plazo_id>/actualizar", methods=["POST"])
@roles_required("Administrador")
def actualizar(plazo_id):
    try:
        PlazoSLA.modificar(plazo_id, session["empresa_id"], request.form.get("horas", ""))
        flash("Plazo actualizado correctamente.", "success")
    except PlazoError as e:
        flash(str(e), "danger")
    return redirect(url_for("sla.lista"))


@bp.route("/sla/<int:plazo_id>/eliminar", methods=["POST"])
@roles_required("Administrador")
def eliminar(plazo_id):
    try:
        PlazoSLA.quitar(plazo_id, session["empresa_id"])
        flash("Plazo eliminado: esa prioridad vuelve a su valor por defecto.", "success")
    except PlazoError as e:
        flash(str(e), "danger")
    return redirect(url_for("sla.lista"))


# 2. API de plazos: se prueba en Postman con la sesión iniciada
# Igual que crearcancion() de la clase: arma un diccionario que luego jsonify convierte en JSON.
def crearplazo(p_id, p_prioridad, p_horas):
    plazo = dict()
    plazo["id"] = p_id
    plazo["prioridad"] = p_prioridad
    plazo["horas_limite"] = p_horas
    return plazo


@bp.route("/api/sla")
@roles_required("Administrador")
def api_listar():
    rpta = dict()
    listaPlazos = list()
    try:
        for p in PlazoSLA.listar(session["empresa_id"]):
            listaPlazos.append(crearplazo(p["id"], p["prioridad"], p["horas_limite"]))
        rpta["code"] = 1
        rpta["data"] = listaPlazos
        rpta["msge"] = "Lista de plazos SLA generada correctamente en json"
    except Exception as e:
        rpta["code"] = 0
        rpta["data"] = None
        rpta["msge"] = repr(e)
    return respuesta(rpta["code"], rpta["data"], rpta["msge"], 200 if rpta["code"] == 1 else 500)


@bp.route("/api/sla/<strId>")
@roles_required("Administrador")
def api_detalle(strId):
    try:
        p = PlazoSLA.obtener(int(strId), session["empresa_id"])
        if p:
            return respuesta(1, crearplazo(p["id"], p["prioridad"], p["horas_limite"]), "Plazo encontrado")
        return respuesta(0, None, "El plazo no existe", 404)
    except ValueError:
        return respuesta(0, None, "El id del plazo no es válido", 400)
    except Exception as e:
        return respuesta(0, None, repr(e), 500)


# Crea un plazo: acepta JSON {"prioridad": "Alta", "horas": 6} o un formulario
@bp.route("/api/sla", methods=["POST"])
@roles_required("Administrador")
def api_crear():
    try:
        datos = request.get_json(silent=True) if request.is_json else request.form
        if not isinstance(datos, dict) and datos is not request.form:
            return respuesta(0, None, "Envía un objeto JSON válido", 400)
        nuevo_id = PlazoSLA.registrar(session["empresa_id"], str(datos.get("prioridad", "")), datos.get("horas", ""))
        p = PlazoSLA.obtener(nuevo_id, session["empresa_id"])
        return respuesta(1, crearplazo(p["id"], p["prioridad"], p["horas_limite"]), "Plazo creado correctamente", 201)
    except PlazoError as e:
        return respuesta(0, None, str(e), e.estado)
    except Exception as e:
        return respuesta(0, None, repr(e), 500)
