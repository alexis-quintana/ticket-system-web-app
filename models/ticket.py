
import os
import uuid
from flask import current_app
from db import obtener_conexion
from modules.sla import calcular_sla

PRIORIDADES = ("Alta", "Media", "Baja")
ESTADOS = ("Abierto", "En proceso", "Resuelto", "Cerrado")
SLA_CSS = {"verde": "green", "amarillo": "yellow", "rojo": "red"}   # clases de tickets.css

MAX_FOTOS = 3
MAX_BYTES = 5 * 1024 * 1024          # 5 MB por foto
# Tipo MIME según los primeros bytes del archivo (no se confía en la extensión)
FIRMAS = {b"\xff\xd8\xff": ("image/jpeg", ".jpg"),
          b"\x89PNG\r\n\x1a\n": ("image/png", ".png")}


class TicketError(Exception):
    """Error que se muestra al usuario. `estado` es el código HTTP (400, 403, 404)."""
    def __init__(self, mensaje, estado=400):
        super().__init__(mensaje)
        self.estado = estado


# ---------------------------------------------------------------------------
# Evidencia: una foto adjunta a un ticket
# ---------------------------------------------------------------------------
class Evidencia:

    def __init__(self, id, ticket_id, archivo, nombre_original, mime, tamano_bytes):
        self.id = id
        self.ticket_id = ticket_id
        self.archivo = archivo                    # nombre aleatorio dentro de /uploads
        self.nombre_original = nombre_original    # nombre que tenía en la PC del usuario
        self.mime = mime
        self.tamano_bytes = tamano_bytes

    @staticmethod
    def desde_fila(fila):
        return Evidencia(fila["id"], fila["ticket_id"], fila["archivo"], fila["nombre_original"],
                         fila["mime"], fila["tamano_bytes"])

    @staticmethod
    def carpeta():
        return os.path.join(current_app.root_path, "uploads")

    def ruta(self):
        return os.path.join(Evidencia.carpeta(), self.archivo)

    def a_diccionario(self):
        return dict(id=self.id, nombre=self.nombre_original, mime=self.mime, tamano_bytes=self.tamano_bytes,
                    url="/tickets/evidencia/" + str(self.id))

    @staticmethod
    def leer(archivo_subido):
        """Valida una foto subida (peso y tipo MIME real). Devuelve (datos, mime, extension)."""
        datos = archivo_subido.read()
        if len(datos) > MAX_BYTES:
            raise TicketError("La foto " + archivo_subido.filename + " pesa más de 5 MB.")
        for firma, (mime, ext) in FIRMAS.items():
            if datos.startswith(firma):
                return datos, mime, ext
        raise TicketError("La foto " + archivo_subido.filename + " no es una imagen JPG o PNG.")

    @staticmethod
    def de_ticket(ticket_id, empresa_id):
        """Fotos de un ticket, de la más antigua a la más nueva."""
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                cur.execute("SELECT * FROM ticket_evidencias WHERE ticket_id=%s AND empresa_id=%s ORDER BY id",
                            (ticket_id, empresa_id))
                return [Evidencia.desde_fila(f) for f in cur.fetchall()]
        finally:
            con.close()

    @staticmethod
    def obtener(evidencia_id, usuario):
        """La foto con el ticket al que pertenece, solo si el usuario puede verla."""
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                cur.execute("SELECT * FROM ticket_evidencias WHERE id=%s AND empresa_id=%s",
                            (evidencia_id, usuario["empresa_id"]))
                fila = cur.fetchone()
        finally:
            con.close()
        if not fila:
            raise TicketError("La foto no existe.", 404)
        ticket = Ticket.obtener(fila["ticket_id"], usuario)     # valida empresa y solicitante
        return Evidencia.desde_fila(fila), ticket

    @staticmethod
    def guardar_archivos(cur, ticket_id, empresa_id, fotos, guardados):
        """Escribe las fotos en /uploads y las registra. `guardados` acumula rutas para borrarlas si algo falla."""
        for nombre_original, (datos, mime, ext) in fotos:
            archivo = uuid.uuid4().hex + ext
            ruta = os.path.join(Evidencia.carpeta(), archivo)
            with open(ruta, "wb") as salida:
                salida.write(datos)
            guardados.append(ruta)
            cur.execute("INSERT INTO ticket_evidencias (ticket_id, empresa_id, archivo, nombre_original, mime, tamano_bytes) "
                        "VALUES (%s,%s,%s,%s,%s,%s)",
                        (ticket_id, empresa_id, archivo, nombre_original[:160], mime, len(datos)))

    def eliminar(self, usuario):
        """Borra la foto (fila y archivo). Solo mientras el ticket se pueda editar."""
        ticket = Ticket.obtener(self.ticket_id, usuario)
        ticket.validar_edicion(usuario)
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                cur.execute("DELETE FROM ticket_evidencias WHERE id=%s AND empresa_id=%s",
                            (self.id, usuario["empresa_id"]))
            con.commit()
        finally:
            con.close()
        if os.path.exists(self.ruta()):
            os.remove(self.ruta())


# ---------------------------------------------------------------------------
# Ticket
# ---------------------------------------------------------------------------
COLUMNAS = ("t.id, t.empresa_id, t.solicitante_id, t.tecnico_id, t.categoria_id, c.nombre AS categoria, "
            "t.asunto, t.descripcion, t.prioridad, t.estado, t.resuelto_en, t.created_at, t.updated_at, "
            "(SELECT MIN(e.id) FROM ticket_evidencias e WHERE e.ticket_id = t.id) AS evidencia_id, "
            "(SELECT COUNT(*) FROM ticket_evidencias e WHERE e.ticket_id = t.id) AS total_evidencias")
DESDE = "FROM tickets t JOIN categorias c ON c.id = t.categoria_id "


class Ticket:

    def __init__(self, fila):
        self.id = fila["id"]
        self.empresa_id = fila["empresa_id"]
        self.solicitante_id = fila["solicitante_id"]
        self.tecnico_id = fila["tecnico_id"]
        self.categoria_id = fila["categoria_id"]
        self.categoria = fila["categoria"]
        self.asunto = fila["asunto"]
        self.descripcion = fila["descripcion"]
        self.prioridad = fila["prioridad"]
        self.estado = fila["estado"]
        self.resuelto_en = fila["resuelto_en"]
        self.created_at = fila["created_at"]
        self.updated_at = fila["updated_at"]
        self.evidencia_id = fila["evidencia_id"]           # primera foto (miniatura del listado)
        self.total_evidencias = fila["total_evidencias"]
        self.sla = self.calcular_sla()

    
    def calcular_sla(self):
        """Semáforo del Módulo 4 en el formato que usa el listado: clase CSS, estado y detalle."""
        s = calcular_sla(self.prioridad, self.created_at, self.estado, self.resuelto_en, self.empresa_id)
        estado, detalle = s["texto"].split(" · ")
        return {"clase": SLA_CSS[s["color"]], "estado": estado, "detalle": detalle}

    def puede_editar(self, usuario):
        """Se edita solo mientras está Abierto, y solo su solicitante o un Administrador."""
        return self.estado == "Abierto" and (usuario["rol"] == "Administrador"
                                             or usuario["usuario_id"] == self.solicitante_id)

    def validar_edicion(self, usuario):
        if self.estado != "Abierto":
            raise TicketError("Solo se puede modificar un ticket en estado Abierto.", 403)
        if not self.puede_editar(usuario):
            raise TicketError("No tienes permiso para modificar este ticket.", 403)

    @staticmethod
    def validar_datos(datos, archivos, fotos_actuales=0):
        """Revisa los campos del formulario o del JSON. Devuelve los valores limpios."""
        asunto = str(datos.get("asunto", "")).strip()
        descripcion = str(datos.get("descripcion", "")).strip()
        categoria_id = str(datos.get("categoria_id", "")).strip()
        prioridad = str(datos.get("prioridad", "")).strip()
        if not 5 <= len(asunto) <= 120:
            raise TicketError("El asunto debe tener entre 5 y 120 caracteres.")
        if not 10 <= len(descripcion) <= 2000:
            raise TicketError("La descripción debe tener entre 10 y 2000 caracteres.")
        if not categoria_id.isdigit():
            raise TicketError("Selecciona una categoría.")
        if prioridad not in PRIORIDADES:
            raise TicketError("Selecciona una prioridad válida.")
        if fotos_actuales + len(archivos) > MAX_FOTOS:
            raise TicketError("Un ticket puede tener como máximo 3 fotos." +
                              (" Ya tiene " + str(fotos_actuales) + "." if fotos_actuales else ""))
        fotos = [(f.filename, Evidencia.leer(f)) for f in archivos]
        return asunto, descripcion, int(categoria_id), prioridad, fotos

    def a_diccionario(self):
        """Datos del ticket listos para jsonify (las fechas como texto)."""
        fecha = lambda d: d.isoformat(sep=" ", timespec="seconds") if d else None
        return dict(id=self.id, codigo="TK-" + str(self.id).zfill(4), asunto=self.asunto,
                    descripcion=self.descripcion, categoria_id=self.categoria_id, categoria=self.categoria,
                    prioridad=self.prioridad, estado=self.estado, solicitante_id=self.solicitante_id,
                    tecnico_id=self.tecnico_id, sla=self.sla, total_evidencias=self.total_evidencias,
                    created_at=fecha(self.created_at), updated_at=fecha(self.updated_at),
                    resuelto_en=fecha(self.resuelto_en))

    # ---------- Consultas ----------
    @staticmethod
    def listar(usuario, q="", estado="", prioridad=""):
        """Tickets de la empresa; el Solicitante solo ve los suyos. Filtros opcionales."""
        sql = "SELECT " + COLUMNAS + " " + DESDE + "WHERE t.empresa_id=%s"
        params = [usuario["empresa_id"]]
        if usuario["rol"] == "Solicitante":
            sql += " AND t.solicitante_id=%s"
            params.append(usuario["usuario_id"])
        if q:
            numero = q.upper().removeprefix("TK-").lstrip("#")
            sql += " AND (t.asunto LIKE %s OR t.id = %s)"
            params += [f"%{q}%", int(numero) if numero.isdigit() else 0]
        if estado in ESTADOS:
            sql += " AND t.estado=%s"
            params.append(estado)
        if prioridad in PRIORIDADES:
            sql += " AND t.prioridad=%s"
            params.append(prioridad)
        sql += " ORDER BY t.id DESC"
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                cur.execute(sql, params)
                return [Ticket(f) for f in cur.fetchall()]
        finally:
            con.close()

    @staticmethod
    def obtener(ticket_id, usuario):
        """Un ticket de la empresa del usuario. Error 404 si no existe o no le corresponde verlo."""
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                cur.execute("SELECT " + COLUMNAS + " " + DESDE + "WHERE t.id=%s AND t.empresa_id=%s",
                            (ticket_id, usuario["empresa_id"]))
                fila = cur.fetchone()
        finally:
            con.close()
        if not fila or (usuario["rol"] == "Solicitante" and fila["solicitante_id"] != usuario["usuario_id"]):
            raise TicketError("El ticket no existe.", 404)
        return Ticket(fila)

    @staticmethod
    def categorias(empresa_id):
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                cur.execute("SELECT id, nombre FROM categorias WHERE empresa_id=%s ORDER BY nombre", (empresa_id,))
                return cur.fetchall()
        finally:
            con.close()

    @staticmethod
    def _validar_categoria(cur, categoria_id, empresa_id):
        cur.execute("SELECT id FROM categorias WHERE id=%s AND empresa_id=%s", (categoria_id, empresa_id))
        if not cur.fetchone():
            raise TicketError("La categoría seleccionada no existe.")

    # ---------- Crear y actualizar ----------
    @staticmethod
    def crear(usuario, datos, archivos):
        """Registra el ticket y sus fotos en una sola transacción. Devuelve el id nuevo."""
        asunto, descripcion, categoria_id, prioridad, fotos = Ticket.validar_datos(datos, archivos)
        emp = usuario["empresa_id"]
        guardados = []
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                Ticket._validar_categoria(cur, categoria_id, emp)
                cur.execute("INSERT INTO tickets (empresa_id, solicitante_id, categoria_id, asunto, descripcion, prioridad) "
                            "VALUES (%s,%s,%s,%s,%s,%s)",
                            (emp, usuario["usuario_id"], categoria_id, asunto, descripcion, prioridad))
                ticket_id = cur.lastrowid
                Evidencia.guardar_archivos(cur, ticket_id, emp, fotos, guardados)
            con.commit()
            return ticket_id
        except Exception:
            con.rollback()
            for ruta in guardados:          # si falla la base, no deja fotos sueltas en /uploads
                os.remove(ruta)
            raise
        finally:
            con.close()

    def actualizar(self, usuario, datos, archivos):
        """Cambia los datos del ticket y agrega fotos nuevas (hasta completar 3)."""
        self.validar_edicion(usuario)
        asunto, descripcion, categoria_id, prioridad, fotos = Ticket.validar_datos(
            datos, archivos, fotos_actuales=self.total_evidencias)
        guardados = []
        con = obtener_conexion()
        try:
            with con.cursor() as cur:
                Ticket._validar_categoria(cur, categoria_id, self.empresa_id)
                cur.execute("UPDATE tickets SET asunto=%s, descripcion=%s, categoria_id=%s, prioridad=%s "
                            "WHERE id=%s AND empresa_id=%s AND estado='Abierto'",
                            (asunto, descripcion, categoria_id, prioridad, self.id, self.empresa_id))
                Evidencia.guardar_archivos(cur, self.id, self.empresa_id, fotos, guardados)
                from models.historial import Historial
                Historial.registrar_cambio_prioridad(cur, usuario, self.id, self.estado,
                    self.prioridad, prioridad)
            con.commit()
        except Exception:
            con.rollback()
            for ruta in guardados:
                os.remove(ruta)
            raise
        finally:
            con.close()