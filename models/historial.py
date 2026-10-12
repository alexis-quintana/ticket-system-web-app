"""Modelo del Módulo 3 (Seminario): asignación, estados e historial del ticket.

Aquí está todo el SQL del módulo; la ruta (modules/historial.py) solo recibe la petición
y decide qué responder. El historial es la auditoría del ticket: se agrega, nunca se borra.
"""
from db import obtener_conexion
from modules.sla import calcular_sla        # Módulo 4 (Ordoñez): semáforo del ticket
from models.ticket import ESTADOS, PRIORIDADES   # Módulo 2 (Timaná): una sola lista en Python

# Transiciones del Administrador y del técnico asignado (se cambia aquí si el docente pide otra regla)
TRANSICIONES = {
    "Abierto":    ("En proceso",),
    "En proceso": ("Resuelto",),
    "Resuelto":   ("Cerrado", "En proceso"),   # En proceso = reapertura
    "Cerrado":    (),
}
# El Solicitante dueño del ticket confirma la solución (Cerrado) o la rechaza (vuelve a En proceso)
TRANSICIONES_SOLICITANTE = {
    "Resuelto": ("Cerrado", "En proceso"),
}
# Solo se asigna o reasigna mientras el ticket está pendiente
ASIGNABLES = ("Abierto", "En proceso")
# Tipos de evento que se guardan en ticket_historial.tipo (mismos valores que el ENUM de la tabla)
TIPOS = ("Asignación", "Desasignación", "Cambio de estado", "Cambio de prioridad")
SLA_CSS = {"verde": "green", "amarillo": "yellow", "rojo": "red"}
MAX_COMENTARIO = 1000

# SELECT base del ticket con nombres de solicitante y técnico (siempre filtrado por empresa).
# tecnico_activo = 0 avisa que el responsable fue desactivado y hay que reasignar.
SQL_TICKET = (
    "SELECT t.id, t.asunto, t.descripcion, t.prioridad, t.estado, t.created_at, t.resuelto_en, "
    "t.solicitante_id, t.tecnico_id, c.nombre AS categoria, "
    "CONCAT(ps.nombres, ' ', ps.apellidos) AS solicitante, "
    "CONCAT(pt.nombres, ' ', pt.apellidos) AS tecnico, ut.activo AS tecnico_activo "
    "FROM tickets t "
    "LEFT JOIN categorias c ON c.id = t.categoria_id "
    "LEFT JOIN usuarios us ON us.id = t.solicitante_id "
    "LEFT JOIN personas ps ON ps.id = us.persona_id "
    "LEFT JOIN usuarios ut ON ut.id = t.tecnico_id "
    "LEFT JOIN personas pt ON pt.id = ut.persona_id "
)

# SELECT base de un evento del historial con el nombre de quien lo hizo y de los técnicos.
# tecnico = quién queda a cargo DESPUÉS del evento; tecnico_anterior = quién estaba ANTES.
SQL_EVENTO = (
    "SELECT h.id, h.ticket_id, h.tipo, h.estado_anterior, h.estado_nuevo, h.tecnico_id, "
    "h.tecnico_anterior_id, h.comentario, h.created_at, "
    "CONCAT(pa.nombres, ' ', pa.apellidos) AS autor, "
    "CONCAT(pt.nombres, ' ', pt.apellidos) AS tecnico, "
    "CONCAT(pn.nombres, ' ', pn.apellidos) AS tecnico_anterior "
    "FROM ticket_historial h "
    "JOIN usuarios ua ON ua.id = h.usuario_id JOIN personas pa ON pa.id = ua.persona_id "
    "LEFT JOIN usuarios ut ON ut.id = h.tecnico_id LEFT JOIN personas pt ON pt.id = ut.persona_id "
    "LEFT JOIN usuarios un ON un.id = h.tecnico_anterior_id LEFT JOIN personas pn ON pn.id = un.persona_id "
)


def _fecha(d):
    """Fecha como texto para jsonify (igual que Ticket.a_diccionario)."""
    return d.isoformat(sep=" ", timespec="seconds") if d else None


class HistorialError(Exception):
    """Error que se muestra al usuario. `estado` es el código HTTP (400, 403, 404, 409)."""
    def __init__(self, mensaje, estado=400):
        super().__init__(mensaje)
        self.estado = estado


# Un evento de la línea de tiempo: una fila de la tabla ticket_historial.
class Historial:

    # Constructor: cada objeto representa un movimiento del ticket.
    def __init__(self, id, ticket_id, tipo, estado_anterior, estado_nuevo, tecnico_id,
                 comentario, created_at, autor, tecnico, tecnico_anterior_id=None, tecnico_anterior=None):
        self.id = id
        self.ticket_id = ticket_id
        self.tipo = tipo                          # Asignación, Desasignación o Cambio de estado
        self.estado_anterior = estado_anterior
        self.estado_nuevo = estado_nuevo
        self.tecnico_id = tecnico_id
        self.comentario = comentario
        self.created_at = created_at
        self.autor = autor                        # quién hizo el cambio
        self.tecnico = tecnico                    # técnico a cargo después del evento
        self.tecnico_anterior_id = tecnico_anterior_id
        self.tecnico_anterior = tecnico_anterior  # técnico que tenía el ticket antes (reasignar/quitar)

    # Convierte una fila de la base (diccionario) en un objeto Historial.
    @staticmethod
    def desde_fila(fila):
        return Historial(fila["id"], fila["ticket_id"], fila["tipo"], fila["estado_anterior"],
                         fila["estado_nuevo"], fila["tecnico_id"], fila["comentario"],
                         fila["created_at"], fila["autor"], fila["tecnico"],
                         fila["tecnico_anterior_id"], fila["tecnico_anterior"])

    # Datos del evento listos para jsonify.
    def a_diccionario(self):
        evento = dict()
        evento["id"] = self.id
        evento["ticket_id"] = self.ticket_id
        evento["codigo_ticket"] = "TK-" + str(self.ticket_id).zfill(4)
        evento["tipo"] = self.tipo
        evento["estado_anterior"] = self.estado_anterior
        evento["estado_nuevo"] = self.estado_nuevo
        evento["tecnico_id"] = self.tecnico_id
        evento["tecnico"] = self.tecnico
        evento["tecnico_anterior_id"] = self.tecnico_anterior_id
        evento["tecnico_anterior"] = self.tecnico_anterior
        evento["autor"] = self.autor
        evento["comentario"] = self.comentario
        evento["created_at"] = _fecha(self.created_at)
        return evento

    # ---------- Reglas de permisos ----------
    @staticmethod
    def puede_ver(t, usuario):
        """Solicitante solo ve sus tickets; Administrador y Técnico ven los de su empresa."""
        return usuario["rol"] != "Solicitante" or t["solicitante_id"] == usuario["usuario_id"]

    @staticmethod
    def puede_cambiar_estado(t, usuario):
        rol = usuario["rol"]
        return rol == "Administrador" or (rol == "Técnico" and t["tecnico_id"] == usuario["usuario_id"])

    @staticmethod
    def siguientes(t, usuario):
        """Estados a los que ESTE usuario puede mover el ticket (vacío = no puede cambiarlo)."""
        if usuario["rol"] == "Solicitante":
            if t["solicitante_id"] != usuario["usuario_id"]:
                return ()
            return TRANSICIONES_SOLICITANTE.get(t["estado"], ())
        if not Historial.puede_cambiar_estado(t, usuario):
            return ()
        return TRANSICIONES.get(t["estado"], ())

    @staticmethod
    def puede_asignar(t, usuario):
        """Solo el Administrador, y solo mientras el ticket está pendiente (Abierto o En proceso)."""
        return usuario["rol"] == "Administrador" and t["estado"] in ASIGNABLES

    @staticmethod
    def puede_quitar_asignacion(t, usuario):
        """Solo el Administrador, y solo si el técnico aún no empezó (ticket Abierto)."""
        return usuario["rol"] == "Administrador" and bool(t["tecnico_id"]) and t["estado"] == "Abierto"

    @staticmethod
    def _completar(t, usuario):
        """Agrega al ticket el semáforo SLA y lo que el usuario puede hacer con él."""
        s = calcular_sla(t["prioridad"], t["created_at"], t["estado"], t["resuelto_en"], usuario["empresa_id"])
        t["sla"] = {"clase": SLA_CSS[s["color"]], "texto": s["texto"]}
        t["siguientes"] = Historial.siguientes(t, usuario)
        t["puede_estado"] = bool(t["tecnico_id"]) and bool(t["siguientes"])
        t["puede_asignar"] = Historial.puede_asignar(t, usuario)
        t["puede_quitar"] = Historial.puede_quitar_asignacion(t, usuario)
        # el responsable fue desactivado (Módulo 1) y el ticket sigue pendiente: hay que reasignar
        t["tecnico_inactivo"] = (bool(t["tecnico_id"]) and not t["tecnico_activo"]
                                 and t["estado"] in ASIGNABLES)
        return t

    @staticmethod
    def ticket_a_diccionario(t):
        """Ticket de la bandeja listo para jsonify (las fechas como texto)."""
        return dict(id=t["id"], codigo="TK-" + str(t["id"]).zfill(4), asunto=t["asunto"],
                    prioridad=t["prioridad"], estado=t["estado"], categoria=t["categoria"],
                    solicitante_id=t["solicitante_id"], solicitante=t["solicitante"],
                    tecnico_id=t["tecnico_id"], tecnico=t["tecnico"],
                    tecnico_inactivo=t["tecnico_inactivo"], sla=t["sla"],
                    siguientes=list(t["siguientes"]), puede_estado=t["puede_estado"],
                    puede_asignar=t["puede_asignar"], puede_quitar=t["puede_quitar"],
                    created_at=_fecha(t["created_at"]),
                    resuelto_en=_fecha(t["resuelto_en"]))

    # ---------- Consultas ----------
    @staticmethod
    def _tecnicos(cur, empresa_id):
        cur.execute("SELECT u.id, CONCAT(p.nombres, ' ', p.apellidos) AS nombre "
                    "FROM usuarios u JOIN roles r ON r.id = u.rol_id "
                    "JOIN personas p ON p.id = u.persona_id "
                    "WHERE u.empresa_id=%s AND r.nombre='Técnico' AND u.activo=1 "
                    "ORDER BY p.apellidos, p.nombres", (empresa_id,))
        return cur.fetchall()

    @staticmethod
    def tecnicos(empresa_id):
        """Técnicos activos de la empresa (para el selector de asignar)."""
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                return Historial._tecnicos(cur, empresa_id)
        finally:
            con.close()

    @staticmethod
    def bandeja(usuario, q="", estado="", prioridad="", asignado=""):
        """Tickets de la bandeja de asignación. El Técnico solo ve los que tiene asignados.
        estado: un estado, "pendientes" (Abierto + En proceso) o vacío (todos).
        asignado: "sin" = sin técnico, "inactivo" = su técnico fue desactivado."""
        sql = SQL_TICKET + "WHERE t.empresa_id=%s"
        params = [usuario["empresa_id"]]
        if usuario["rol"] == "Técnico":
            sql += " AND t.tecnico_id=%s"
            params.append(usuario["usuario_id"])
        if q:
            numero = q.upper().removeprefix("TK-").lstrip("#")
            sql += " AND (t.asunto LIKE %s OR t.id = %s)"
            params += [f"%{q}%", int(numero) if numero.isdigit() else 0]
        if estado in ESTADOS:
            sql += " AND t.estado=%s"
            params.append(estado)
        elif estado == "pendientes":
            sql += " AND t.estado IN ('Abierto','En proceso')"
        if prioridad in PRIORIDADES:
            sql += " AND t.prioridad=%s"
            params.append(prioridad)
        if asignado == "sin":                     # "sin" = sin técnico
            sql += " AND t.tecnico_id IS NULL"
        elif asignado == "inactivo":              # pendientes cuyo técnico fue desactivado
            sql += (" AND t.tecnico_id IS NOT NULL AND ut.activo = 0 "
                    "AND t.estado IN ('Abierto','En proceso')")
        # Primero lo pendiente, luego Resuelto y al final Cerrado; dentro de cada grupo,
        # lo que vence antes. fn_fecha_limite_sla es del Módulo 4 (no se repite la regla 4/24/72 h).
        sql += (" ORDER BY t.estado IN ('Resuelto','Cerrado'), t.estado = 'Cerrado', "
                "fn_fecha_limite_sla(t.prioridad, t.created_at), t.id")
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                cur.execute(sql, params)
                filas = cur.fetchall()
        finally:
            con.close()
        return [Historial._completar(t, usuario) for t in filas]

    @staticmethod
    def ticket(ticket_id, usuario):
        """Un ticket con su SLA y permisos. Error 404 si no existe o el usuario no puede verlo."""
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                cur.execute(SQL_TICKET + "WHERE t.id=%s AND t.empresa_id=%s", (ticket_id, usuario["empresa_id"]))
                t = cur.fetchone()
        finally:
            con.close()
        if not t or not Historial.puede_ver(t, usuario):
            raise HistorialError("El ticket no existe.", 404)
        return Historial._completar(t, usuario)

    @staticmethod
    def listar(ticket_id, usuario):
        """Línea de tiempo del ticket (lo más reciente primero) como lista de objetos Historial."""
        Historial.ticket(ticket_id, usuario)      # valida empresa y que el usuario pueda verlo
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                cur.execute(SQL_EVENTO + "WHERE h.ticket_id=%s AND h.empresa_id=%s "
                            "ORDER BY h.created_at DESC, h.id DESC", (ticket_id, usuario["empresa_id"]))
                filas = cur.fetchall()
        finally:
            con.close()
        return [Historial.desde_fila(f) for f in filas]

    @staticmethod
    def obtener(evento_id, usuario):
        """Un evento del historial, solo si el usuario puede ver su ticket."""
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                cur.execute(SQL_EVENTO + "WHERE h.id=%s AND h.empresa_id=%s", (evento_id, usuario["empresa_id"]))
                fila = cur.fetchone()
        finally:
            con.close()
        if not fila:
            raise HistorialError("El evento del historial no existe.", 404)
        Historial.ticket(fila["ticket_id"], usuario)
        return Historial.desde_fila(fila)

    # ---------- Acciones (cada una en una sola transacción) ----------
    @staticmethod
    def _bloquear_ticket(cur, ticket_id, empresa_id):
        """Lee el ticket con FOR UPDATE para que dos personas no lo cambien a la vez."""
        cur.execute("SELECT id, estado, tecnico_id, solicitante_id FROM tickets "
                    "WHERE id=%s AND empresa_id=%s FOR UPDATE", (ticket_id, empresa_id))
        t = cur.fetchone()
        if not t:
            raise HistorialError("El ticket no existe.", 404)
        return t

    @staticmethod
    def _registrar(cur, usuario, ticket_id, tipo, anterior, nuevo, tecnico_id, comentario,
                   tecnico_anterior_id=None):
        """Inserta un evento. tecnico_id = quién queda a cargo; tecnico_anterior_id = quién estaba."""
        cur.execute("INSERT INTO ticket_historial (empresa_id, ticket_id, usuario_id, tipo, "
                    "estado_anterior, estado_nuevo, tecnico_id, tecnico_anterior_id, comentario) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (usuario["empresa_id"], ticket_id, usuario["usuario_id"], tipo,
                     anterior, nuevo, tecnico_id, tecnico_anterior_id, comentario))

    @staticmethod
    def registrar_cambio_prioridad(cur, usuario, ticket_id, estado, prioridad_anterior, prioridad_nueva):
        """Para el Módulo 2 (Timaná): se llama DENTRO de su transacción de Ticket.actualizar()
        cuando cambia la prioridad, porque eso cambia el plazo del SLA. No hace commit."""
        if prioridad_anterior == prioridad_nueva:
            return
        cur.execute("SELECT tecnico_id FROM tickets WHERE id=%s AND empresa_id=%s",
                    (ticket_id, usuario["empresa_id"]))
        fila = cur.fetchone()
        Historial._registrar(cur, usuario, ticket_id, "Cambio de prioridad", estado, estado,
                             fila["tecnico_id"] if fila else None,
                             "Prioridad cambiada de " + prioridad_anterior + " a " + prioridad_nueva + ".")

    @staticmethod
    def asignar(ticket_id, usuario, tecnico_id, comentario=""):
        """Asigna (o reasigna) un técnico. Crea un evento 'Asignación'. Devuelve el mensaje."""
        tecnico_id = str(tecnico_id or "").strip()
        comentario = str(comentario or "").strip()
        if not tecnico_id.isdigit():
            raise HistorialError("Selecciona un técnico.")
        if len(comentario) > MAX_COMENTARIO:
            raise HistorialError("El comentario no puede superar 1000 caracteres.")
        emp = usuario["empresa_id"]
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                t = Historial._bloquear_ticket(cur, ticket_id, emp)
                if t["estado"] not in ASIGNABLES:
                    raise HistorialError("Solo se puede asignar un ticket Abierto o En proceso. "
                                         "Si un ticket Resuelto necesita más trabajo, primero reábrelo.", 409)
                if t["tecnico_id"] == int(tecnico_id):
                    raise HistorialError("El ticket ya está asignado a ese técnico.", 409)
                # el técnico debe ser de la misma empresa, tener rol Técnico y estar activo
                tec = next((x for x in Historial._tecnicos(cur, emp) if x["id"] == int(tecnico_id)), None)
                if not tec:
                    raise HistorialError("El técnico seleccionado no es válido.")
                reasignacion = bool(t["tecnico_id"])
                texto = ("Ticket reasignado a " if reasignacion else "Ticket asignado a ") + tec["nombre"] + "."
                comentario = comentario or texto
                cur.execute("UPDATE tickets SET tecnico_id=%s WHERE id=%s AND empresa_id=%s",
                            (tec["id"], ticket_id, emp))
                # se guarda también quién lo tenía antes (NULL si es la primera asignación)
                Historial._registrar(cur, usuario, ticket_id, "Asignación",
                                     t["estado"], t["estado"], tec["id"], comentario,
                                     tecnico_anterior_id=t["tecnico_id"])
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
        return texto

    @staticmethod
    def quitar_asignacion(ticket_id, usuario, comentario=""):
        """Quita el técnico del ticket (el 'eliminar' del CRUD del módulo).
        El historial no se borra: queda un evento 'Desasignación' como auditoría."""
        comentario = str(comentario or "").strip()
        if len(comentario) > MAX_COMENTARIO:
            raise HistorialError("El comentario no puede superar 1000 caracteres.")
        emp = usuario["empresa_id"]
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                t = Historial._bloquear_ticket(cur, ticket_id, emp)
                if not t["tecnico_id"]:
                    raise HistorialError("El ticket no tiene un técnico asignado.", 409)
                if t["estado"] != "Abierto":
                    raise HistorialError("Solo se puede quitar la asignación de un ticket Abierto. "
                                         "Si ya está en atención, usa Reasignar.", 409)
                # el nombre se busca directo: el técnico pudo haber sido desactivado después
                cur.execute("SELECT CONCAT(p.nombres, ' ', p.apellidos) AS nombre FROM usuarios u "
                            "JOIN personas p ON p.id = u.persona_id WHERE u.id=%s", (t["tecnico_id"],))
                anterior = cur.fetchone()
                nombre = anterior["nombre"] if anterior else "el técnico"
                comentario = comentario or "Se quitó la asignación a " + nombre + "."
                cur.execute("UPDATE tickets SET tecnico_id=NULL WHERE id=%s AND empresa_id=%s",
                            (ticket_id, emp))
                # nadie queda a cargo (tecnico_id NULL); tecnico_anterior_id = a quién se le quitó
                Historial._registrar(cur, usuario, ticket_id, "Desasignación",
                                     t["estado"], t["estado"], None, comentario,
                                     tecnico_anterior_id=t["tecnico_id"])
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
        return "Se quitó la asignación del ticket TK-" + str(ticket_id).zfill(4) + "."

    @staticmethod
    def cambiar_estado(ticket_id, usuario, nuevo, comentario):
        """Cambia el estado con comentario obligatorio. Crea un evento 'Cambio de estado'."""
        nuevo = str(nuevo or "").strip()
        comentario = str(comentario or "").strip()
        if nuevo not in ESTADOS:
            raise HistorialError("Selecciona el nuevo estado.")
        if not comentario:
            raise HistorialError("Escribe un comentario para cambiar el estado.")
        if len(comentario) < 5 or len(comentario) > MAX_COMENTARIO:
            raise HistorialError("El comentario debe tener entre 5 y 1000 caracteres.")
        emp = usuario["empresa_id"]
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                t = Historial._bloquear_ticket(cur, ticket_id, emp)
                if usuario["rol"] == "Solicitante" and t["solicitante_id"] != usuario["usuario_id"]:
                    raise HistorialError("El ticket no existe.", 404)   # no revela tickets ajenos
                if not t["tecnico_id"]:
                    raise HistorialError("Asigna un técnico antes de cambiar el estado.", 409)
                permitidos = Historial.siguientes(t, usuario)
                if not permitidos:
                    if usuario["rol"] == "Solicitante":
                        raise HistorialError("Solo puedes confirmar o reabrir tu ticket cuando está Resuelto.", 403)
                    raise HistorialError("Solo el técnico asignado o un administrador puede cambiar el estado.", 403)
                if nuevo not in permitidos:
                    raise HistorialError(f"No se puede pasar de {t['estado']} a {nuevo}.", 409)
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
                Historial._registrar(cur, usuario, ticket_id, "Cambio de estado",
                                     t["estado"], nuevo, None, comentario)
            con.commit()
        except Exception:
            con.rollback()
            raise
        finally:
            con.close()
        return "Estado actualizado a " + nuevo + "."
