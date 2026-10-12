from db import obtener_conexion

# Código guardado en la base -> texto que ve el usuario.
TIPOS = {
    "asignacion": "Asignación de ticket",
    "cambio_estado": "Cambio de estado",
    "comentario": "Nuevo comentario",
}


# Lógica de negocio del módulo 5; los avisos los crean los triggers de la base.
class Notificacion:

    # Crea una notificación a mano; hoy los avisos los crean los triggers de la base, este método queda disponible por si se necesita.
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
            return nuevo_id
        finally:
            conexion.close()

    # Una notificación del usuario, o None si no existe o es de otra persona.
    @staticmethod
    def obtener(notificacion_id, usuario_id):
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "SELECT id, ticket_id, tipo, mensaje, leida, created_at "
                    "FROM notificaciones WHERE id = %s AND usuario_id = %s",
                    (notificacion_id, usuario_id))
                return cursor.fetchone()
        finally:
            conexion.close()

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

    @staticmethod
    def listar(usuario_id, lectura="todas", tipo=""):
        consulta = ("SELECT id, ticket_id, tipo, mensaje, leida, created_at "
                    "FROM notificaciones WHERE usuario_id = %s")
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
                return cursor.fetchall()
        finally:
            conexion.close()

    # Últimas notificaciones para el desplegable de la campana (no leídas primero).
    @staticmethod
    def recientes(usuario_id, limite=6):
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "SELECT id, ticket_id, tipo, mensaje, leida, created_at "
                    "FROM notificaciones WHERE usuario_id = %s "
                    "ORDER BY leida ASC, created_at DESC, id DESC LIMIT %s",
                    (usuario_id, limite))
                return cursor.fetchall()
        finally:
            conexion.close()

    @staticmethod
    def marcar_leida(notificacion_id, usuario_id):
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "UPDATE notificaciones SET leida = 1 "
                    "WHERE id = %s AND usuario_id = %s",
                    (notificacion_id, usuario_id))
                filas = cursor.rowcount
            conexion.commit()
            return filas
        finally:
            conexion.close()

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

    # Borra una notificación del usuario. Devuelve cuántas filas se borraron (0 o 1).
    @staticmethod
    def eliminar(notificacion_id, usuario_id):
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "DELETE FROM notificaciones WHERE id = %s AND usuario_id = %s",
                    (notificacion_id, usuario_id))
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
