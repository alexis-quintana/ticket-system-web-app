from db import obtener_conexion

# Código guardado en la base -> texto que ve el usuario.
TIPOS = {
    "asignacion": "Asignación de ticket",
    "cambio_estado": "Cambio de estado",
    "comentario": "Nuevo comentario",
}

COLUMNAS = "id, usuario_id, ticket_id, tipo, mensaje, leida, created_at"


# Una notificación de un usuario; los avisos los crean los triggers de la base.
class Notificacion:

    # Constructor: cada objeto representa una fila de la tabla notificaciones.
    def __init__(self, id, usuario_id, ticket_id, tipo, mensaje, leida, created_at):
        self.id = id
        self.usuario_id = usuario_id
        self.ticket_id = ticket_id
        self.tipo = tipo
        self.mensaje = mensaje
        self.leida = bool(leida)
        self.created_at = created_at

    # Convierte una fila de la base (diccionario) en un objeto Notificacion.
    @staticmethod
    def desde_fila(fila):
        return Notificacion(fila["id"], fila["usuario_id"], fila["ticket_id"], fila["tipo"],
                            fila["mensaje"], fila["leida"], fila["created_at"])

    # Marca esta notificación como leída. Devuelve cuántas filas cambió (0 o 1).
    def marcar_leida(self):
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "UPDATE notificaciones SET leida = 1 WHERE id = %s AND usuario_id = %s",
                    (self.id, self.usuario_id))
                filas = cursor.rowcount
            conexion.commit()
            self.leida = True
            return filas
        finally:
            conexion.close()

    # Elimina esta notificación. Devuelve cuántas filas se borraron (0 o 1).
    def eliminar(self):
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM notificaciones WHERE id = %s AND usuario_id = %s",
                    (self.id, self.usuario_id))
                filas = cursor.rowcount
            conexion.commit()
            return filas
        finally:
            conexion.close()

    # Crea una notificación a mano y devuelve el objeto; hoy los avisos los crean los triggers.
    @staticmethod
    def crear(usuario_id, ticket_id, tipo, mensaje):
        if tipo not in TIPOS:
            raise ValueError("Tipo de notificación no válido: " + repr(tipo))
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO notificaciones (usuario_id, ticket_id, tipo, mensaje) "
                    "VALUES (%s, %s, %s, %s)",
                    (usuario_id, ticket_id, tipo, mensaje))
                nuevo_id = cursor.lastrowid
            conexion.commit()
        finally:
            conexion.close()
        return Notificacion.obtener(nuevo_id, usuario_id)

    # Una notificación del usuario, o None si no existe o es de otra persona.
    @staticmethod
    def obtener(notificacion_id, usuario_id):
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "SELECT " + COLUMNAS + " FROM notificaciones WHERE id = %s AND usuario_id = %s",
                    (notificacion_id, usuario_id))
                fila = cursor.fetchone()
        finally:
            conexion.close()
        return Notificacion.desde_fila(fila) if fila else None

    @staticmethod
    def contar_no_leidas(usuario_id):
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "SELECT COUNT(*) AS total FROM notificaciones "
                    "WHERE usuario_id = %s AND leida = 0",
                    (usuario_id,))
                return cursor.fetchone()["total"]
        finally:
            conexion.close()

    # Lista de objetos Notificacion del usuario, con filtros opcionales.
    @staticmethod
    def listar(usuario_id, lectura="todas", tipo=""):
        consulta = "SELECT " + COLUMNAS + " FROM notificaciones WHERE usuario_id = %s"
        parametros = [usuario_id]
        if lectura == "no_leidas":
            consulta += " AND leida = 0"
        elif lectura == "leidas":
            consulta += " AND leida = 1"
        if tipo in TIPOS:
            consulta += " AND tipo = %s"
            parametros.append(tipo)
        consulta += " ORDER BY created_at DESC, id DESC"
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(consulta, parametros)
                filas = cursor.fetchall()
        finally:
            conexion.close()
        return [Notificacion.desde_fila(f) for f in filas]

    # Últimas notificaciones para el desplegable de la campana (no leídas primero).
    @staticmethod
    def recientes(usuario_id, limite=6):
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "SELECT " + COLUMNAS + " FROM notificaciones WHERE usuario_id = %s "
                    "ORDER BY leida ASC, created_at DESC, id DESC LIMIT %s",
                    (usuario_id, limite))
                filas = cursor.fetchall()
        finally:
            conexion.close()
        return [Notificacion.desde_fila(f) for f in filas]

    @staticmethod
    def marcar_todas(usuario_id):
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "UPDATE notificaciones SET leida = 1 "
                    "WHERE usuario_id = %s AND leida = 0",
                    (usuario_id,))
                filas = cursor.rowcount
            conexion.commit()
            return filas
        finally:
            conexion.close()

    # Borra todas las notificaciones ya leídas del usuario. Devuelve cuántas fueron.
    @staticmethod
    def eliminar_leidas(usuario_id):
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM notificaciones WHERE usuario_id = %s AND leida = 1",
                    (usuario_id,))
                filas = cursor.rowcount
            conexion.commit()
            return filas
        finally:
            conexion.close()
