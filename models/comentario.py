from db import obtener_conexion

MAX_COMENTARIO = 1000


# Un comentario de un ticket; el trigger trg_comentarios_ai crea el aviso para la otra parte.
class Comentario:

    # Constructor: cada objeto representa una fila de la tabla ticket_comentarios.
    def __init__(self, id, ticket_id, usuario_id, autor, rol, comentario, created_at):
        self.id = id
        self.ticket_id = ticket_id
        self.usuario_id = usuario_id
        self.autor = autor
        self.rol = rol
        self.comentario = comentario
        self.created_at = created_at

    # Convierte una fila de la base (diccionario) en un objeto Comentario.
    @staticmethod
    def desde_fila(fila):
        return Comentario(fila["id"], fila["ticket_id"], fila["usuario_id"], fila["autor"],
                          fila["rol"], fila["comentario"], fila["created_at"])

    # Igual que crearcancion() de la clase: arma el diccionario que luego jsonify convierte en JSON.
    def a_diccionario(self):
        comentario = dict()
        comentario['id'] = self.id
        comentario['ticket_id'] = self.ticket_id
        comentario['usuario_id'] = self.usuario_id
        comentario['autor'] = self.autor
        comentario['rol'] = self.rol
        comentario['comentario'] = self.comentario
        comentario['creado'] = self.created_at.isoformat()
        return comentario

    # Ticket de la empresa que el usuario puede ver, o None (el Solicitante solo ve los suyos).
    @staticmethod
    def ticket_visible(ticket_id, empresa_id, usuario_id, rol):
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "SELECT id, estado, solicitante_id, tecnico_id FROM tickets "
                    "WHERE id = %s AND empresa_id = %s", (ticket_id, empresa_id))
                ticket = cursor.fetchone()
        finally:
            conexion.close()
        if ticket and rol == "Solicitante" and ticket["solicitante_id"] != usuario_id:
            return None
        return ticket

    # Comentarios del ticket, del más antiguo al más nuevo.
    @staticmethod
    def listar(ticket_id, empresa_id):
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "SELECT c.id, c.ticket_id, c.comentario, c.created_at, c.usuario_id, "
                    "CONCAT(p.nombres, ' ', p.apellidos) AS autor, r.nombre AS rol "
                    "FROM ticket_comentarios c "
                    "JOIN usuarios u ON u.id = c.usuario_id "
                    "JOIN personas p ON p.id = u.persona_id "
                    "JOIN roles r ON r.id = u.rol_id "
                    "WHERE c.ticket_id = %s AND c.empresa_id = %s ORDER BY c.created_at, c.id",
                    (ticket_id, empresa_id))
                filas = cursor.fetchall()
        finally:
            conexion.close()
        return [Comentario.desde_fila(f) for f in filas]

    # Guarda un comentario nuevo y devuelve el objeto creado.
    @staticmethod
    def crear(empresa_id, ticket_id, usuario_id, texto):
        conexion = obtener_conexion()
        try:
            with conexion.cursor() as cursor:
                cursor.execute(
                    "INSERT INTO ticket_comentarios (empresa_id, ticket_id, usuario_id, comentario) "
                    "VALUES (%s, %s, %s, %s)", (empresa_id, ticket_id, usuario_id, texto))
                nuevo_id = cursor.lastrowid
            conexion.commit()
        finally:
            conexion.close()
        return next(c for c in Comentario.listar(ticket_id, empresa_id) if c.id == nuevo_id)
