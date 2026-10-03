from db import obtener_conexion

# Código guardado en la base -> texto que ve el usuario.
TIPOS = {
    "asignacion": "Asignación de ticket",
    "cambio_estado": "Cambio de estado",
    "comentario": "Nuevo comentario",
}


class Notificacion:
    """Lógica de negocio del módulo 5. Los demás módulos solo llaman a crear()."""

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
            conexion.commit()
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