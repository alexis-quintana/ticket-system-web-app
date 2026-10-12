from datetime import datetime, timedelta

from db import obtener_conexion


def _consultar(sql, params=(), uno=False):
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(sql, params)
            return cursor.fetchone() if uno else cursor.fetchall()
    finally:
        conexion.close()


def _escribir(sql, params=()):
    conexion = obtener_conexion()
    try:
        with conexion.cursor() as cursor:
            cursor.execute(sql, params)
            nuevo_id = cursor.lastrowid
            filas = cursor.rowcount
        conexion.commit()
        return nuevo_id, filas
    finally:
        conexion.close()


# Lógica de negocio del módulo 4: plazos y semáforo de un ticket.
class SLA:
    PLAZOS_POR_DEFECTO = {"Alta": 4, "Media": 24, "Baja": 72}  # horas
    UMBRAL_AMARILLO = 0.25  # amarillo cuando queda 25 % o menos del plazo
    ESTADOS_FINALES = ("Resuelto", "Cerrado")

    @staticmethod
    def horas_limite(prioridad, plazos=None):
        tabla = plazos or {}
        return tabla.get(prioridad, SLA.PLAZOS_POR_DEFECTO.get(prioridad, 24))

    @staticmethod
    def calcular(prioridad, creado_en, estado, resuelto_en=None, plazos=None):
        horas = SLA.horas_limite(prioridad, plazos)
        limite = creado_en + timedelta(hours=horas)

        # Si el ticket ya terminó, el contador se congela en la fecha de resolución
        if estado in SLA.ESTADOS_FINALES and resuelto_en:
            referencia = resuelto_en
        else:
            referencia = datetime.now()

        restantes = (limite - referencia).total_seconds()
        proporcion = restantes / (horas * 3600)

        if restantes <= 0:
            color, texto = "rojo", "Vencido · Hace " + SLA._formatear(-restantes)
        elif proporcion <= SLA.UMBRAL_AMARILLO:
            color, texto = "amarillo", "Por vencer · Restan " + SLA._formatear(restantes)
        else:
            color, texto = "verde", "En plazo · Restan " + SLA._formatear(restantes)

        return {"color": color, "texto": texto, "vencido": restantes <= 0}

    @staticmethod
    def _formatear(segundos):
        segundos = int(segundos)
        horas, minutos = segundos // 3600, (segundos % 3600) // 60
        return f"{horas} h" if horas >= 1 else f"{minutos} min"


# CRUD de la tabla sla_plazos (plazos editables por empresa).
class PlazoSLA:
    PRIORIDADES = ("Alta", "Media", "Baja")

    @staticmethod
    def listar(empresa_id):
        return _consultar(
            "SELECT id, prioridad, horas_limite FROM sla_plazos "
            "WHERE empresa_id = %s ORDER BY horas_limite", (empresa_id,))

    @staticmethod
    def como_diccionario(empresa_id):
        # {"Alta": 4, "Media": 24, ...}; lo que no esté usa el valor por defecto
        return {f["prioridad"]: f["horas_limite"] for f in PlazoSLA.listar(empresa_id)}

    @staticmethod
    def obtener(plazo_id, empresa_id):
        return _consultar(
            "SELECT id, prioridad, horas_limite FROM sla_plazos "
            "WHERE id = %s AND empresa_id = %s", (plazo_id, empresa_id), uno=True)

    @staticmethod
    def crear(empresa_id, prioridad, horas):
        nuevo_id, _ = _escribir(
            "INSERT INTO sla_plazos (empresa_id, prioridad, horas_limite) VALUES (%s, %s, %s)",
            (empresa_id, prioridad, horas))
        return nuevo_id

    @staticmethod
    def actualizar(plazo_id, empresa_id, horas):
        _, filas = _escribir(
            "UPDATE sla_plazos SET horas_limite = %s WHERE id = %s AND empresa_id = %s",
            (horas, plazo_id, empresa_id))
        return filas > 0

    @staticmethod
    def eliminar(plazo_id, empresa_id):
        # Al borrar un plazo, esa prioridad vuelve a su valor por defecto (4/24/72)
        _, filas = _escribir(
            "DELETE FROM sla_plazos WHERE id = %s AND empresa_id = %s",
            (plazo_id, empresa_id))
        return filas > 0