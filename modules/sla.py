from flask import Blueprint

from models.sla import SLA

bp = Blueprint("sla", __name__)

# tickets.py y historial.py importan estos dos nombres; no los renombres
SLA_HORAS = SLA.PLAZOS_POR_DEFECTO


def calcular_sla(prioridad, creado_en, estado, resuelto_en=None):
    return SLA.calcular(prioridad, creado_en, estado, resuelto_en)