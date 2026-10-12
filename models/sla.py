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


# Error de validación que se muestra al usuario; estado es el código HTTP (400, 404, 409).
class PlazoError(Exception):
    def __init__(self, mensaje, estado=400):
        super().__init__(mensaje)
        self.estado = estado


# CRUD de la tabla sla_plazos (plazos editables por empresa).
class PlazoSLA:
    PRIORIDADES = ("Alta", "Media", "Baja")
    MIN_HORAS = 1
    MAX_HORAS = 720  # 30 días

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

    # Plazos que realmente se aplican: los de la empresa y, si falta alguno, el valor por defecto
    @staticmethod
    def efectivos(empresa_id):
        plazos = dict(SLA.PLAZOS_POR_DEFECTO)
        plazos.update(PlazoSLA.como_diccionario(empresa_id))
        return plazos

    @staticmethod
    def validar_prioridad(valor):
        if valor not in PlazoSLA.PRIORIDADES:
            raise PlazoError("Selecciona una prioridad válida.")
        return valor

    @staticmethod
    def validar_horas(valor):
        texto = str(valor).strip()
        if not texto.isdigit() or not PlazoSLA.MIN_HORAS <= int(texto) <= PlazoSLA.MAX_HORAS:
            raise PlazoError("Las horas deben ser un número entero entre 1 y 720.")
        return int(texto)

    @staticmethod
    def existe_prioridad(empresa_id, prioridad):
        fila = _consultar("SELECT id FROM sla_plazos WHERE empresa_id = %s AND prioridad = %s",
                          (empresa_id, prioridad), uno=True)
        return fila is not None

    # Crea el plazo de una prioridad (una sola por empresa) y devuelve su id
    @staticmethod
    def registrar(empresa_id, prioridad, horas):
        prioridad = PlazoSLA.validar_prioridad(prioridad)
        horas = PlazoSLA.validar_horas(horas)
        if PlazoSLA.existe_prioridad(empresa_id, prioridad):
            raise PlazoError("La prioridad " + prioridad + " ya tiene un plazo. Edítalo en la lista.", 409)
        return PlazoSLA.crear(empresa_id, prioridad, horas)

    # Cambia las horas de un plazo existente
    @staticmethod
    def modificar(plazo_id, empresa_id, horas):
        horas = PlazoSLA.validar_horas(horas)
        if not PlazoSLA.obtener(plazo_id, empresa_id):
            raise PlazoError("El plazo no existe.", 404)
        PlazoSLA.actualizar(plazo_id, empresa_id, horas)

    # Borra un plazo; esa prioridad vuelve a su valor por defecto
    @staticmethod
    def quitar(plazo_id, empresa_id):
        if not PlazoSLA.eliminar(plazo_id, empresa_id):
            raise PlazoError("El plazo no existe.", 404)
