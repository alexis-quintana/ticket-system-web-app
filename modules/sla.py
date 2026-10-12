from flask import Blueprint, render_template
from datetime import datetime, timedelta

bp = Blueprint("sla", __name__)

SLA_HORAS = {"Alta": 4, "Media": 24, "Baja": 72}


def calcular_sla(prioridad, creado_en, estado, resuelto_en=None):
    horas_limite = SLA_HORAS.get(prioridad, 24)
    limite = creado_en + timedelta(hours=horas_limite)
    referencia = resuelto_en if estado in ("Resuelto", "Cerrado") and resuelto_en else datetime.now()
    segundos_restantes = (limite - referencia).total_seconds()
    porcentaje_restante = segundos_restantes / (horas_limite * 3600)

    if segundos_restantes <= 0:
        color, texto = "rojo", f"Vencido · Hace {formatear(abs(segundos_restantes))}"
    elif porcentaje_restante <= 0.25:
        color, texto = "amarillo", f"Por vencer · Restan {formatear(segundos_restantes)}"
    else:
        color, texto = "verde", f"En plazo · Restan {formatear(segundos_restantes)}"
    return {"color": color, "texto": texto}


def formatear(segundos):
    segundos = int(segundos)
    horas, minutos = segundos // 3600, (segundos % 3600) // 60
    return f"{horas} h" if horas >= 1 else f"{minutos} min"


@bp.route("/sla/demo")
def demo():
    ejemplos = [
        calcular_sla("Alta", datetime.now() - timedelta(hours=3, minutes=15), "Abierto"),
        calcular_sla("Media", datetime.now() - timedelta(hours=20), "En proceso"),
        calcular_sla("Baja", datetime.now() - timedelta(hours=80), "Abierto"),
    ]
    return render_template("sla/demo.html", ejemplos=ejemplos)